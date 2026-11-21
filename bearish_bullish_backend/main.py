"""F&O 5-Day Breakout Screener – FastAPI entrypoint.

Observation/analysis only: no order execution, paper trading or portfolio logic.

Run:  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from engine.groww_client import (
    AccessForbiddenError,
    DataNotFoundError,
    GrowwClient,
    MarketDataClient,
    MarketDataError,
    NotAuthenticatedError,
    RateLimitedError,
)
from engine.market_time import heuristic_session_date, now_ist
from engine.mock_client import MockClient
from engine.screener import Screener
from engine.strategy import classify
from models import CandleResponse, DailyCandle, HealthResponse, ScreenerSnapshot
from ws import ConnectionManager

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("screener")

SYMBOL_RE = re.compile(r"^[A-Z0-9&\-]{1,20}$")
CHART_SESSIONS = 90  # daily candles returned to the chart

ws_manager = ConnectionManager()


def _build_client() -> MarketDataClient:
    if settings.data_source == "mock":
        logger.warning("DATA_SOURCE=mock – serving SYNTHETIC demo data, not real prices")
        return MockClient()
    return GrowwClient(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = _build_client()
    screener = Screener(client, ws_manager, settings)
    app.state.client = client
    app.state.screener = screener

    try:
        await client.authenticate()
    except MarketDataError as exc:
        # Keep the server up; the screener loop retries with backoff.
        logger.error("Initial Groww login failed: %s", exc.message)
        screener.last_error = exc.message
    await screener.ensure_universe()

    task = asyncio.create_task(screener.loop(), name="screener-loop")
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="F&O 5-Day Breakout Screener", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _screener() -> Screener:
    return app.state.screener


def _http_error(exc: MarketDataError) -> HTTPException:
    if isinstance(exc, RateLimitedError):
        return HTTPException(status_code=429, detail=exc.message, headers={"Retry-After": "2"})
    if isinstance(exc, NotAuthenticatedError):
        return HTTPException(status_code=503, detail=exc.message)
    if isinstance(exc, DataNotFoundError):
        return HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, AccessForbiddenError):
        return HTTPException(status_code=502, detail=exc.message)
    return HTTPException(status_code=502, detail=exc.message)


# ------------------------------------------------------------------------- routes
@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    sc = _screener()
    return HealthResponse(
        status="ok" if sc.last_error is None else "degraded",
        authenticated=app.state.client.authenticated,
        data_source=settings.data_source,
        universe_size=len(sc.universe),
        last_scan_at=sc.latest.scanned_at if sc.latest else None,
        last_error=sc.last_error,
        ws_clients=ws_manager.count,
    )


@app.get("/api/screener", response_model=ScreenerSnapshot)
async def get_screener() -> ScreenerSnapshot:
    sc = _screener()
    if sc.latest is None:
        detail = sc.last_error or "First scan has not completed yet"
        raise HTTPException(status_code=503, detail=detail)
    return sc.latest


@app.get("/api/symbols", response_model=list[str])
async def get_symbols() -> list[str]:
    return _screener().universe


@app.get("/api/candles/{symbol}", response_model=CandleResponse)
async def get_candles(symbol: str) -> CandleResponse:
    sym = symbol.strip().upper()
    sc = _screener()
    if not SYMBOL_RE.fullmatch(sym) or (sc.universe and sym not in sc.universe):
        raise HTTPException(status_code=404, detail=f"Unknown F&O symbol '{symbol}'")

    try:
        df = await sc.chart_frame(sym)
    except MarketDataError as exc:
        raise _http_error(exc) from exc

    session_date = sc.session_date or heuristic_session_date(now_ist())
    latest = sc.results.get(sym)
    signal = classify(sym, df, latest.ltp if latest else None, session_date, settings.lookback_days)

    tail = df.tail(CHART_SESSIONS)
    candles = [
        DailyCandle(
            time=row.date.isoformat(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=None if row.volume != row.volume else float(row.volume),  # NaN-safe
        )
        for row in tail.itertuples(index=False)
    ]
    return CandleResponse(
        symbol=sym,
        candles=candles,
        lookback_days=settings.lookback_days,
        session_date=session_date,
        signal=signal,
    )


@app.websocket("/ws/screener")
async def screener_ws(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket, initial_message=_screener().update_message())
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WS receive error: %s", exc)
    finally:
        ws_manager.disconnect(websocket)
