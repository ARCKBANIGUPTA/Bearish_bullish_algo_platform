"""NSE market-hours helpers (IST). Exchange holidays are not modelled; on a
holiday the scan simply re-reads the last session's prices."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
SCAN_BUFFER_SEC = 10  # run a few seconds after each 5-minute boundary


def now_ist() -> datetime:
    return datetime.now(IST)


def is_trading_weekday(d: date) -> bool:
    return d.weekday() < 5


def is_market_open(now: datetime) -> bool:
    now = now.astimezone(IST)
    return is_trading_weekday(now.date()) and MARKET_OPEN <= now.time() <= MARKET_CLOSE


def previous_weekday(d: date) -> date:
    d -= timedelta(days=1)
    while not is_trading_weekday(d):
        d -= timedelta(days=1)
    return d


def heuristic_session_date(now: datetime) -> date:
    """Best guess of the current/most recent session when no quote timestamp is available."""
    now = now.astimezone(IST)
    today = now.date()
    if is_trading_weekday(today) and now.time() >= MARKET_OPEN:
        return today
    return previous_weekday(today)


def next_market_open(now: datetime) -> datetime:
    now = now.astimezone(IST)
    candidate = datetime.combine(now.date(), MARKET_OPEN, tzinfo=IST)
    if now >= candidate or not is_trading_weekday(candidate.date()):
        d = candidate.date() + timedelta(days=1)
        while not is_trading_weekday(d):
            d += timedelta(days=1)
        candidate = datetime.combine(d, MARKET_OPEN, tzinfo=IST)
    return candidate


def next_scan_time(now: datetime, interval_sec: int, only_market_hours: bool) -> datetime:
    """Next interval boundary (+buffer); outside market hours, the next market open."""
    now = now.astimezone(IST)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = (now - midnight).total_seconds()
    slot = midnight + timedelta(seconds=(int(elapsed // interval_sec) + 1) * interval_sec)
    candidate = slot + timedelta(seconds=SCAN_BUFFER_SEC)
    if not only_market_hours:
        return candidate
    # Allow the scan just after the close (e.g. 15:30:10) to capture closing prices.
    close_limit = datetime.combine(candidate.date(), MARKET_CLOSE, tzinfo=IST) + timedelta(
        seconds=SCAN_BUFFER_SEC
    )
    open_limit = datetime.combine(candidate.date(), MARKET_OPEN, tzinfo=IST)
    if is_trading_weekday(candidate.date()) and open_limit <= candidate <= close_limit:
        return candidate
    return next_market_open(now) + timedelta(seconds=SCAN_BUFFER_SEC)
