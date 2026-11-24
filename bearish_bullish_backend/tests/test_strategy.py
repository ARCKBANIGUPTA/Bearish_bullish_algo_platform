from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from engine.market_time import IST, heuristic_session_date, next_scan_time
from engine.strategy import candles_to_frame, classify, prior_window
from models import Signal

SESSION = date(2026, 11, 16)  # Monday


def make_daily(highs, lows, closes=None, end=SESSION - timedelta(days=1)):
    """Build consecutive daily candles ending at `end` (older first)."""
    n = len(highs)
    dates = [end - timedelta(days=n - 1 - i) for i in range(n)]
    closes = closes or [(h + l) / 2 for h, l in zip(highs, lows)]
    return pd.DataFrame(
        {"date": dates, "open": closes, "high": highs, "low": lows, "close": closes, "volume": 1000}
    )


@pytest.fixture
def five_days():
    return make_daily(highs=[105, 110, 108, 107, 106], lows=[95, 97, 92, 96, 98])


def test_bullish_when_ltp_above_5d_high(five_days):
    res = classify("ABC", five_days, 112.0, SESSION)
    assert res.signal is Signal.BULLISH
    assert res.high_5d == 110 and res.low_5d == 92
    assert res.breakout_pct == pytest.approx((112 - 110) / 110 * 100, abs=0.01)


def test_bearish_when_ltp_below_5d_low(five_days):
    res = classify("ABC", five_days, 90.0, SESSION)
    assert res.signal is Signal.BEARISH
    assert res.breakout_pct == pytest.approx((92 - 90) / 92 * 100, abs=0.01)


@pytest.mark.parametrize("ltp", [92.0, 100.0, 110.0])
def test_neutral_inside_or_at_range(five_days, ltp):
    res = classify("ABC", five_days, ltp, SESSION)
    assert res.signal is Signal.NEUTRAL
    assert res.breakout_pct == 0


def test_only_last_five_prior_sessions_used():
    # An old, very high candle 6 sessions back must be ignored.
    df = make_daily(highs=[200, 105, 110, 108, 107, 106], lows=[50, 95, 97, 92, 96, 98])
    res = classify("ABC", df, 150.0, SESSION)
    assert res.high_5d == 110 and res.low_5d == 92
    assert res.signal is Signal.BULLISH


def test_todays_candle_excluded_from_window(five_days):
    today = pd.DataFrame(
        [{"date": SESSION, "open": 100, "high": 130, "low": 80, "close": 125, "volume": 1}]
    )
    df = pd.concat([five_days, today], ignore_index=True)
    window = prior_window(df, SESSION, 5)
    assert SESSION not in set(window["date"])
    res = classify("ABC", df, 125.0, SESSION)
    assert res.signal is Signal.BULLISH  # 125 > 110 even though today's own high is 130


def test_falls_back_to_session_close_when_ltp_missing(five_days):
    today = pd.DataFrame(
        [{"date": SESSION, "open": 100, "high": 116, "low": 99, "close": 115, "volume": 1}]
    )
    df = pd.concat([five_days, today], ignore_index=True)
    res = classify("ABC", df, None, SESSION)
    assert res.ltp == 115 and res.signal is Signal.BULLISH


def test_insufficient_history_returns_none():
    df = make_daily(highs=[105, 110, 108, 107], lows=[95, 97, 92, 96])
    assert classify("ABC", df, 120.0, SESSION) is None


def test_no_price_returns_none(five_days):
    assert classify("ABC", five_days, None, SESSION) is None
    assert classify("ABC", five_days, float("nan"), SESSION) is None


def test_change_pct_vs_previous_close(five_days):
    res = classify("ABC", five_days, 106.0, SESSION)
    prev_close = five_days["close"].iloc[-1]
    assert res.prev_close == prev_close
    assert res.change_pct == pytest.approx((106 - prev_close) / prev_close * 100, abs=0.01)


def test_candles_to_frame_parses_iso_and_epoch_and_drops_bad_rows():
    rows = [
        ["2026-11-13T00:00:00", 10, 12, 9, 11, 100, None],
        [1763251200, 11, 13, 10, 12, 200],            # epoch seconds -> 2025-11-16 IST
        ["2026-11-12T00:00:00", 9, 12, None, 11, 100],  # missing low -> dropped
        ["garbage", 1, 2, 3, 4, 5],                    # bad timestamp -> dropped
        ["2026-11-13T00:00:00", 10, 14, 9, 13, 150],   # duplicate date -> keep last
    ]
    df = candles_to_frame(rows)
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["date"].is_monotonic_increasing
    assert df[df["date"] == date(2026, 11, 13)]["high"].iloc[0] == 14


def test_candles_to_frame_fills_missing_open_like_groww_daily():
    # Real Groww 1-day shape (Nov 2026): [iso_ts, None, high, low, close, volume, None]
    rows = [
        ["2026-11-10T00:00:00", None, 105.0, 95.0, 100.0, 1000, None],
        ["2026-11-11T00:00:00", None, 104.0, 99.0, 103.0, 1000, None],  # prev close 100 in range
        ["2026-11-12T00:00:00", None, 112.0, 108.0, 110.0, 1000, None],  # gap up: 103 -> clamp to low 108
        ["2026-11-13T00:00:00", 111.0, 113.0, 107.0, 108.0, 1000, None],  # real open kept
    ]
    df = candles_to_frame(rows)
    assert len(df) == 4
    assert df["open"].tolist() == [100.0, 100.0, 108.0, 111.0]
    assert df["open"].notna().all()
    assert ((df["open"] >= df["low"]) & (df["open"] <= df["high"])).all()


def test_heuristic_session_date():
    sat = datetime(2026, 11, 14, 12, 0, tzinfo=IST)
    mon_early = datetime(2026, 11, 16, 8, 0, tzinfo=IST)
    mon_open = datetime(2026, 11, 16, 10, 0, tzinfo=IST)
    assert heuristic_session_date(sat) == date(2026, 11, 13)
    assert heuristic_session_date(mon_early) == date(2026, 11, 13)
    assert heuristic_session_date(mon_open) == date(2026, 11, 16)


def test_next_scan_time_alignment_and_off_hours():
    t = datetime(2026, 11, 16, 10, 2, 30, tzinfo=IST)
    assert next_scan_time(t, 300, True) == datetime(2026, 11, 16, 10, 5, 10, tzinfo=IST)
    after_close = datetime(2026, 11, 16, 15, 40, tzinfo=IST)
    assert next_scan_time(after_close, 300, True) == datetime(2026, 11, 17, 9, 15, 10, tzinfo=IST)
    friday_night = datetime(2026, 11, 20, 20, 0, tzinfo=IST)
    assert next_scan_time(friday_night, 300, True) == datetime(2026, 11, 23, 9, 15, 10, tzinfo=IST)
