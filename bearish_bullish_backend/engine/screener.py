"""Background screener: daily-candle cache + 5-minute LTP scans + WebSocket broadcast."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime

import pandas as pd

from config import Settings
from engine.groww_client import (
    AccessForbiddenError,
    MarketDataClient,
    MarketDataError,
    NotAuthenticatedError,
)
from engine.market_time import IST, is_market_open, next_scan_time, now_ist
from engine.strategy import classify
from models import ScanErrorMessage, ScreenerSnapshot, ScreenerUpdateMessage, Signal, SignalResult
from ws import ConnectionManager

logger = logging.getLogger(__name__)

CHART_CACHE_TTL_SEC = 300
MAX_SLEEP_CHUNK_SEC = 30  # re-check the clock regularly (laptop sleep, clock changes)


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class Screener:
    def __init__(self, client: MarketDataClient, ws: ConnectionManager, settings: Settings) -> None:
        self.client = client
        self.ws = ws
        self.settings = settings
        self.universe: list[str] = []
        self.latest: ScreenerSnapshot | None = None
        self.results: dict[str, SignalResult] = {}
        self.session_date: date | None = None
        self.last_error: str | None = None
        self._daily: dict[str, tuple[float, pd.DataFrame]] = {}  # symbol -> (fetched_at, df)
        self._daily_session: date | None = None
        self._scan_lock = asyncio.Lock()
        self._universe_loaded_on: date | None = None

    # ------------------------------------------------------------------ universe
    async def ensure_universe(self) -> None:
        today = now_ist().date()
        if self.universe and self._universe_loaded_on == today:
            return
        self.universe = await self.client.load_universe()
        self._universe_loaded_on = today

    # -------------------------------------------------------------- daily candles
    async def _fetch_one(self, symbol: str) -> pd.DataFrame:
        df = await self.client.fetch_daily_candles(symbol, self.settings.history_calendar_days)
        self._daily[symbol] = (time.monotonic(), df)
        return df

    async def refresh_daily_candles(self, symbols: list[str]) -> list[str]:
        """Fetch daily candles in batches of `batch_size` per `batch_window_sec` (10/sec).

        Returns the symbols that failed. Aborts early on HTTP 403 (no data entitlement)
        instead of burning ~200 doomed requests.
        """
        failed: list[str] = []
        batches = _chunks(symbols, self.settings.batch_size)
        started = time.monotonic()
        for i, batch in enumerate(batches, start=1):
            batch_start = time.monotonic()
            results = await asyncio.gather(*(self._fetch_one(s) for s in batch), return_exceptions=True)
            for symbol, res in zip(batch, results):
                if isinstance(res, AccessForbiddenError):
                    raise res
                if isinstance(res, NotAuthenticatedError):
                    raise res
                if isinstance(res, BaseException):
                    failed.append(symbol)
                    msg = res.message if isinstance(res, MarketDataError) else repr(res)
                    logger.warning("Daily candles failed for %s: %s", symbol, msg)
            elapsed = time.monotonic() - batch_start
            # Explicit throttle: one batch of 10 symbols per second.
            if i < len(batches):
                await asyncio.sleep(max(0.0, self.settings.batch_window_sec - elapsed))
        logger.info(
            "Daily candles refreshed: %d symbols, %d failed, %.1fs",
            len(symbols), len(failed), time.monotonic() - started,
        )
        return failed

    def daily_frame(self, symbol: str) -> pd.DataFrame | None:
        entry = self._daily.get(symbol)
        return entry[1] if entry else None

    async def chart_frame(self, symbol: str) -> pd.DataFrame:
        """Daily candles for charting; re-fetched if older than 5 minutes (today's candle moves)."""
        entry = self._daily.get(symbol)
        if entry and time.monotonic() - entry[0] < CHART_CACHE_TTL_SEC:
            return entry[1]
        return await self._fetch_one(symbol)

    # ---------------------------------------------------------------------- scan
    async def run_scan(self) -> ScreenerSnapshot:
        async with self._scan_lock:
            started = time.monotonic()
            await self.client.authenticate()
            await self.ensure_universe()

            session_date = await self.client.get_session_date()
            failed: set[str] = set()

            if self._daily_session != session_date or not self._daily:
                logger.info("New session %s – refreshing daily candles", session_date)
                failed.update(await self.refresh_daily_candles(self.universe))
                self._daily_session = session_date
            else:
                missing = [s for s in self.universe if s not in self._daily]
                if missing:
                    failed.update(await self.refresh_daily_candles(missing))

            ltps: dict[str, float] = {}
            for batch in _chunks(self.universe, self.settings.ltp_batch_size):
                try:
                    ltps.update(await self.client.fetch_ltp(batch))
                except (AccessForbiddenError, NotAuthenticatedError):
                    raise
                except MarketDataError as exc:
                    logger.warning("LTP batch failed (%d symbols): %s", len(batch), exc.message)

            results: dict[str, SignalResult] = {}
            for symbol in self.universe:
                df = self.daily_frame(symbol)
                res = classify(symbol, df, ltps.get(symbol), session_date, self.settings.lookback_days) if df is not None else None
                if res is None:
                    failed.add(symbol)
                else:
                    results[symbol] = res

            bullish = sorted(
                (r for r in results.values() if r.signal == Signal.BULLISH),
                key=lambda r: r.breakout_pct, reverse=True,
            )
            bearish = sorted(
                (r for r in results.values() if r.signal == Signal.BEARISH),
                key=lambda r: r.breakout_pct, reverse=True,
            )
            now = now_ist()
            snapshot = ScreenerSnapshot(
                bullish=bullish,
                bearish=bearish,
                neutral_count=sum(1 for r in results.values() if r.signal == Signal.NEUTRAL),
                failed=sorted(failed),
                universe_size=len(self.universe),
                lookback_days=self.settings.lookback_days,
                session_date=session_date,
                scanned_at=now,
                next_scan_at=next_scan_time(now, self.settings.scan_interval_sec, self.settings.only_market_hours),
                duration_ms=int((time.monotonic() - started) * 1000),
                data_source=self.client.data_source,  # type: ignore[arg-type]
            )
            self.results = results
            self.session_date = session_date
            self.latest = snapshot
            self.last_error = None
            logger.info(
                "Scan done: %d bullish, %d bearish, %d neutral, %d failed in %dms",
                len(bullish), len(bearish), snapshot.neutral_count, len(failed), snapshot.duration_ms,
            )
            await self.ws.broadcast(self.update_message())
            return snapshot

    def update_message(self) -> dict | None:
        if self.latest is None:
            return None
        return ScreenerUpdateMessage(data=self.latest).model_dump(mode="json")

    async def _report_error(self, message: str) -> None:
        self.last_error = message
        await self.ws.broadcast(ScanErrorMessage(message=message, at=now_ist()).model_dump(mode="json"))

    # ---------------------------------------------------------------------- loop
    async def loop(self) -> None:
        """Scan at startup (retrying until one succeeds, even off-hours), then on every
        5-minute boundary – during market hours only, unless only_market_hours=False."""
        error_backoff = 30
        while True:
            try:
                needs_initial = self.latest is None
                if needs_initial or not self.settings.only_market_hours or is_market_open(now_ist()):
                    await self.run_scan()
                error_backoff = 30
                target = next_scan_time(now_ist(), self.settings.scan_interval_sec, self.settings.only_market_hours)
            except asyncio.CancelledError:
                raise
            except MarketDataError as exc:
                logger.error("Scan failed: %s", exc.message)
                await self._report_error(exc.message)
                target = datetime.fromtimestamp(time.time() + error_backoff, tz=IST)
                error_backoff = min(error_backoff * 2, self.settings.scan_interval_sec)
            except Exception as exc:
                logger.exception("Unexpected scan failure")
                await self._report_error(f"Unexpected scan failure: {type(exc).__name__}")
                target = datetime.fromtimestamp(time.time() + error_backoff, tz=IST)
                error_backoff = min(error_backoff * 2, self.settings.scan_interval_sec)
            if self.latest is not None and self.last_error is None:
                self.latest.next_scan_at = target
            logger.info("Next scan at %s", target.strftime("%Y-%m-%d %H:%M:%S %Z"))
            while (remaining := (target - now_ist()).total_seconds()) > 0:
                await asyncio.sleep(min(remaining, MAX_SLEEP_CHUNK_SEC))
