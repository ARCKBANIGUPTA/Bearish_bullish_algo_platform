"""Synthetic market-data client for local development (DATA_SOURCE=mock).

Generates deterministic random-walk daily candles per symbol and a jittered LTP,
so the full pipeline (screener → WebSocket → chart) can be exercised without
Groww market-data access. Every snapshot is tagged data_source="mock" and the UI
shows a DEMO DATA banner – never mistake this for real prices.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import date, timedelta

import pandas as pd

from engine.market_time import heuristic_session_date, is_trading_weekday, now_ist
from engine.symbols import FALLBACK_FNO_SYMBOLS


def _seed(*parts: object) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


class MockClient:
    data_source = "mock"

    def __init__(self) -> None:
        self.authenticated = True
        self._daily: dict[str, pd.DataFrame] = {}

    async def authenticate(self, force: bool = False) -> None:
        return None

    async def load_universe(self) -> list[str]:
        return sorted(FALLBACK_FNO_SYMBOLS)

    async def get_session_date(self) -> date:
        return heuristic_session_date(now_ist())

    async def fetch_daily_candles(self, symbol: str, calendar_days: int) -> pd.DataFrame:
        await asyncio.sleep(0.01)  # simulate network latency
        session = heuristic_session_date(now_ist())
        rng = random.Random(_seed(symbol, session))
        price = rng.uniform(150, 5000)
        drift = rng.uniform(-0.004, 0.004)
        rows = []
        d = session - timedelta(days=calendar_days)
        while d <= session:
            if is_trading_weekday(d):
                o = price
                c = max(1.0, o * (1 + drift + rng.gauss(0, 0.015)))
                h = max(o, c) * (1 + abs(rng.gauss(0, 0.006)))
                lo = min(o, c) * (1 - abs(rng.gauss(0, 0.006)))
                rows.append((d, round(o, 2), round(h, 2), round(lo, 2), round(c, 2), rng.randint(10**5, 10**7)))
                price = c
            d += timedelta(days=1)
        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
        self._daily[symbol] = df
        return df

    async def fetch_ltp(self, symbols: list[str]) -> dict[str, float]:
        await asyncio.sleep(0.01)
        bucket = int(now_ist().timestamp() // 300)  # changes every 5 minutes
        out: dict[str, float] = {}
        for s in symbols:
            df = self._daily.get(s)
            if df is None or df.empty:
                continue
            window = df.iloc[-6:-1]
            rng = random.Random(_seed(s, bucket))
            # Push ~25% of names outside their 5-day range so both lists populate.
            roll = rng.random()
            if roll < 0.13:
                ltp = window["high"].max() * (1 + rng.uniform(0.001, 0.03))
            elif roll < 0.25:
                ltp = window["low"].min() * (1 - rng.uniform(0.001, 0.03))
            else:
                ltp = rng.uniform(window["low"].min(), window["high"].max())
            out[s] = round(float(ltp), 2)
        return out
