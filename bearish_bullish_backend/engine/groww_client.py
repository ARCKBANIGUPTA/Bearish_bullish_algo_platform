"""Async, rate-limited, read-only wrapper around the synchronous `growwapi` SDK.

Only market-data endpoints are used (instruments, quote, LTP, historical candles).
No order / portfolio / margin endpoints are ever called.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
from collections import deque
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol

import pandas as pd
import requests
from growwapi import GrowwAPI
from growwapi.groww.exceptions import (
    GrowwAPIAuthenticationException,
    GrowwAPIAuthorisationException,
    GrowwAPIBadRequestException,
    GrowwAPIException,
    GrowwAPINotFoundException,
    GrowwAPIRateLimitException,
    GrowwAPITimeoutException,
)

from config import AuthError, Settings, login
from engine.market_time import IST, heuristic_session_date, now_ist
from engine.strategy import candles_to_frame
from engine.symbols import FALLBACK_FNO_SYMBOLS, INDEX_SYMBOLS

logger = logging.getLogger(__name__)

INSTRUMENT_CSV_URL = "https://growwapi-assets.groww.in/instruments/instrument.csv"
REFERENCE_SYMBOL = "RELIANCE"  # liquid stock used to detect the current session date


# --------------------------------------------------------------------------- errors
class MarketDataError(Exception):
    """Base class for all market-data failures surfaced to the API layer."""

    def __init__(self, message: str, symbol: str | None = None) -> None:
        super().__init__(message)
        self.symbol = symbol
        self.message = message


class NotAuthenticatedError(MarketDataError):
    pass


class AccessForbiddenError(MarketDataError):
    """Groww returned 403 – usually the Trading API subscription is not active."""


class RateLimitedError(MarketDataError):
    pass


class UpstreamError(MarketDataError):
    pass


class DataNotFoundError(MarketDataError):
    pass


# ---------------------------------------------------------------------- rate limit
class RateLimiter:
    """Sliding-window limiter enforcing several (max_calls, period_sec) windows at once."""

    def __init__(self, limits: list[tuple[int, float]]) -> None:
        self._limits = limits
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._max_period = max(p for _, p in limits)

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                while self._calls and now - self._calls[0] > self._max_period:
                    self._calls.popleft()
                wait = 0.0
                for max_calls, period in self._limits:
                    in_window = [t for t in self._calls if now - t < period]
                    if len(in_window) >= max_calls:
                        wait = max(wait, period - (now - in_window[-max_calls]))
                if wait <= 0:
                    self._calls.append(now)
                    return
                await asyncio.sleep(wait)


# ------------------------------------------------------------------------ protocol
class MarketDataClient(Protocol):
    data_source: str
    authenticated: bool

    async def authenticate(self, force: bool = False) -> None: ...
    async def load_universe(self) -> list[str]: ...
    async def get_session_date(self) -> date: ...
    async def fetch_daily_candles(self, symbol: str, calendar_days: int) -> pd.DataFrame: ...
    async def fetch_ltp(self, symbols: list[str]) -> dict[str, float]: ...


# -------------------------------------------------------------------------- client
class GrowwClient:
    data_source = "groww"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api: GrowwAPI | None = None
        self._auth_lock = asyncio.Lock()
        # Live-data category: 10 req/s, 300 req/min – keep headroom on the minute window.
        self._limiter = RateLimiter([(10, 1.0), (280, 60.0)])
        self.authenticated = False

    # ---- auth
    async def authenticate(self, force: bool = False) -> None:
        async with self._auth_lock:
            if self._api is not None and not force:
                return
            try:
                token = await asyncio.to_thread(login, self._settings, force=force)
            except AuthError as exc:
                self.authenticated = False
                raise NotAuthenticatedError(str(exc)) from exc
            self._api = GrowwAPI(token)
            self.authenticated = True

    async def _ensure_api(self) -> GrowwAPI:
        if self._api is None:
            await self.authenticate()
        assert self._api is not None
        return self._api

    # ---- core call with retries
    async def _call(self, method: str, *, symbol: str | None = None, **kwargs: Any) -> dict:
        reauthed = False
        backoff = 1.0
        attempts = 4
        for attempt in range(1, attempts + 1):
            api = await self._ensure_api()
            await self._limiter.acquire()
            try:
                return await asyncio.to_thread(
                    getattr(api, method), timeout=self._settings.request_timeout_sec, **kwargs
                )
            except GrowwAPIRateLimitException as exc:
                if attempt == attempts:
                    raise RateLimitedError("Groww rate limit exceeded", symbol) from exc
                logger.warning("Rate limited on %s(%s); backing off %.1fs", method, symbol, backoff)
            except (GrowwAPITimeoutException, requests.Timeout, requests.ConnectionError) as exc:
                if attempt >= 3:
                    raise UpstreamError(f"Groww request timed out ({method})", symbol) from exc
                logger.warning("Timeout on %s(%s); retrying", method, symbol)
            except GrowwAPIAuthenticationException as exc:
                if reauthed:
                    raise NotAuthenticatedError("Groww authentication failed", symbol) from exc
                logger.info("Access token rejected; re-authenticating")
                await self.authenticate(force=True)
                reauthed = True
                continue
            except GrowwAPIAuthorisationException as exc:
                raise AccessForbiddenError(_forbidden_message(), symbol) from exc
            except (GrowwAPINotFoundException, GrowwAPIBadRequestException) as exc:
                raise DataNotFoundError(f"No data for {symbol or method}", symbol) from exc
            except GrowwAPIException as exc:
                code = str(getattr(exc, "code", ""))
                if code == "403":
                    raise AccessForbiddenError(_forbidden_message(), symbol) from exc
                if code == "401" and not reauthed:
                    await self.authenticate(force=True)
                    reauthed = True
                    continue
                if code == "429" and attempt < attempts:
                    logger.warning("Rate limited (429) on %s(%s)", method, symbol)
                else:
                    raise UpstreamError(f"Groww API error {code}: {getattr(exc, 'msg', exc)}", symbol) from exc
            except (ValueError, KeyError) as exc:  # malformed JSON / payload
                raise UpstreamError(f"Malformed Groww response for {method}", symbol) from exc
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 8.0)
        raise UpstreamError(f"Groww call {method} failed after retries", symbol)

    # ---- universe
    async def load_universe(self) -> list[str]:
        try:
            symbols = await asyncio.to_thread(_download_fno_universe)
            if len(symbols) < 50:
                raise ValueError(f"suspiciously small universe ({len(symbols)})")
            logger.info("Loaded %d F&O underlyings from instrument master", len(symbols))
            return symbols
        except Exception as exc:  # network, CSV schema changes, ...
            logger.warning("Instrument master unavailable (%s); using static fallback list", exc)
            return sorted(FALLBACK_FNO_SYMBOLS)

    # ---- session date
    async def get_session_date(self) -> date:
        """Date of the most recent trade on a liquid reference stock (handles holidays)."""
        try:
            quote = await self._call(
                "get_quote", symbol=REFERENCE_SYMBOL,
                trading_symbol=REFERENCE_SYMBOL, exchange=GrowwAPI.EXCHANGE_NSE,
                segment=GrowwAPI.SEGMENT_CASH,
            )
            ts = quote.get("last_trade_time")
            if isinstance(ts, (int, float)) and ts > 0:
                seconds = ts / 1000 if ts > 10**11 else ts
                return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone(IST).date()
        except AccessForbiddenError:
            raise
        except MarketDataError as exc:
            logger.warning("Session date lookup failed (%s); using weekday heuristic", exc.message)
        return heuristic_session_date(now_ist())

    # ---- candles
    async def fetch_daily_candles(self, symbol: str, calendar_days: int) -> pd.DataFrame:
        end = now_ist()
        start = end - timedelta(days=min(calendar_days, 180))  # API max for 1-day candles
        payload = await self._call(
            "get_historical_candles", symbol=symbol,
            exchange=GrowwAPI.EXCHANGE_NSE, segment=GrowwAPI.SEGMENT_CASH,
            groww_symbol=f"NSE-{symbol}",
            start_time=start.strftime("%Y-%m-%d 00:00:00"),
            end_time=end.strftime("%Y-%m-%d %H:%M:%S"),
            candle_interval=GrowwAPI.CANDLE_INTERVAL_DAY,
        )
        df = candles_to_frame(payload.get("candles") or [])
        if df.empty:
            raise DataNotFoundError(f"No daily candles returned for {symbol}", symbol)
        return df

    # ---- LTP
    async def fetch_ltp(self, symbols: list[str]) -> dict[str, float]:
        if not symbols:
            return {}
        if len(symbols) > 50:
            raise ValueError("get_ltp accepts at most 50 symbols per call")
        keys = tuple(f"NSE_{s}" for s in symbols)
        payload = await self._call(
            "get_ltp", exchange_trading_symbols=keys, segment=GrowwAPI.SEGMENT_CASH
        )
        out: dict[str, float] = {}
        for key, value in payload.items():
            price = value.get("ltp") if isinstance(value, dict) else value
            if isinstance(price, (int, float)) and price > 0:
                out[key.split("_", 1)[1] if "_" in key else key] = float(price)
        return out


def _forbidden_message() -> str:
    return (
        "Groww denied access to market data (HTTP 403). Check that the Trading API "
        "subscription is active at https://groww.in/user/profile/trading-apis"
    )


def _download_fno_universe() -> list[str]:
    """NSE F&O stock underlyings that also trade as NSE cash equities (drops indices/test rows)."""
    resp = requests.get(INSTRUMENT_CSV_URL, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.BytesIO(resp.content), dtype=str, low_memory=False)
    required = {"exchange", "segment", "instrument_type", "underlying_symbol", "trading_symbol"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"instrument CSV missing columns: {sorted(missing)}")

    nse = df[df["exchange"] == "NSE"]
    futures = nse[(nse["segment"] == "FNO") & (nse["instrument_type"] == "FUT")]
    equities = set(nse[(nse["segment"] == "CASH") & (nse["instrument_type"] == "EQ")]["trading_symbol"])
    underlyings = set(futures["underlying_symbol"].dropna().str.strip())
    return sorted(s for s in underlyings if s in equities and s not in INDEX_SYMBOLS)
