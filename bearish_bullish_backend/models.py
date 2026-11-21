"""Pydantic schemas shared by REST responses and WebSocket payloads.

Mirrored 1:1 by `bearish_bullish_frontend/src/types.ts`.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Signal(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class SignalResult(BaseModel):
    symbol: str
    signal: Signal
    ltp: float
    high_5d: float = Field(description="Highest high of the previous N completed sessions")
    low_5d: float = Field(description="Lowest low of the previous N completed sessions")
    prev_close: float
    change_pct: float = Field(description="LTP vs previous session close, in %")
    breakout_pct: float = Field(description="Distance beyond the broken level in % (0 if NEUTRAL)")
    session_date: date


class ScreenerSnapshot(BaseModel):
    bullish: list[SignalResult]
    bearish: list[SignalResult]
    neutral_count: int
    failed: list[str]
    universe_size: int
    lookback_days: int
    session_date: date
    scanned_at: datetime
    next_scan_at: datetime | None
    duration_ms: int
    data_source: Literal["groww", "mock"]


class DailyCandle(BaseModel):
    time: str = Field(description="Session date as YYYY-MM-DD (lightweight-charts business day)")
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class CandleResponse(BaseModel):
    symbol: str
    interval: Literal["1d"] = "1d"
    candles: list[DailyCandle]
    lookback_days: int
    session_date: date
    signal: SignalResult | None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    authenticated: bool
    data_source: Literal["groww", "mock"]
    universe_size: int
    last_scan_at: datetime | None
    last_error: str | None
    ws_clients: int


class ScreenerUpdateMessage(BaseModel):
    type: Literal["screener_update"] = "screener_update"
    data: ScreenerSnapshot


class ScanErrorMessage(BaseModel):
    type: Literal["scan_error"] = "scan_error"
    message: str
    at: datetime
