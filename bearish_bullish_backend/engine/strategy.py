"""5-day breakout strategy (pure functions – no I/O).

BULLISH : LTP > highest high of the previous N completed trading sessions
BEARISH : LTP < lowest low  of the previous N completed trading sessions
NEUTRAL : otherwise

"Previous N sessions" are the N daily candles dated strictly before the current
session date, so today's still-forming candle never contaminates the window.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from models import Signal, SignalResult

IST = ZoneInfo("Asia/Kolkata")
CANDLE_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def _parse_candle_date(ts: Any) -> date | None:
    """Groww returns ISO strings ('2025-09-24T00:00:00') or epoch seconds/ms."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        seconds = ts / 1000 if ts > 10**11 else ts
        return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone(IST).date()
    if isinstance(ts, str):
        text = ts.strip()
        if text.isdigit():
            return _parse_candle_date(int(text))
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(IST)
        return parsed.date()
    return None


def candles_to_frame(rows: Iterable[Any]) -> pd.DataFrame:
    """Normalise raw Groww candle rows ([ts, o, h, l, c, vol, oi?]) into a clean DataFrame.

    Output columns: date (datetime.date), open, high, low, close, volume.
    Rows with missing/invalid prices are dropped; duplicates keep the last row.
    """
    records = []
    for row in rows or []:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            continue
        d = _parse_candle_date(row[0])
        if d is None:
            continue
        records.append((d, row[1], row[2], row[3], row[4], row[5] if len(row) > 5 else None))

    df = pd.DataFrame.from_records(records, columns=CANDLE_COLUMNS)
    if df.empty:
        return df
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df[(df["high"] > 0) & (df["low"] > 0)]
    df = df.drop_duplicates(subset="date", keep="last").sort_values("date").reset_index(drop=True)
    return df


def prior_window(daily: pd.DataFrame, session_date: date, lookback: int) -> pd.DataFrame:
    """The `lookback` most recent completed sessions strictly before `session_date`."""
    if daily.empty:
        return daily
    return daily[daily["date"] < session_date].tail(lookback)


def _valid_price(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def classify(
    symbol: str,
    daily: pd.DataFrame,
    ltp: float | None,
    session_date: date,
    lookback: int = 5,
) -> SignalResult | None:
    """Classify one symbol. Returns None when there is not enough data to decide."""
    if daily is None or daily.empty:
        return None

    window = prior_window(daily, session_date, lookback)
    if len(window) < lookback:
        return None

    price = ltp
    if not _valid_price(price):
        # Fall back to the current session's daily close if the LTP call failed.
        today = daily[daily["date"] == session_date]
        if today.empty:
            return None
        price = float(today["close"].iloc[-1])
        if not _valid_price(price):
            return None
    price = float(price)

    high_n = float(window["high"].max())
    low_n = float(window["low"].min())
    prev_close = float(window["close"].iloc[-1])

    if price > high_n:
        signal, breakout = Signal.BULLISH, (price - high_n) / high_n * 100
    elif price < low_n:
        signal, breakout = Signal.BEARISH, (low_n - price) / low_n * 100
    else:
        signal, breakout = Signal.NEUTRAL, 0.0

    change = (price - prev_close) / prev_close * 100 if prev_close else 0.0

    return SignalResult(
        symbol=symbol,
        signal=signal,
        ltp=round(price, 2),
        high_5d=round(high_n, 2),
        low_5d=round(low_n, 2),
        prev_close=round(prev_close, 2),
        change_pct=round(change, 2),
        breakout_pct=round(breakout, 2),
        session_date=session_date,
    )
