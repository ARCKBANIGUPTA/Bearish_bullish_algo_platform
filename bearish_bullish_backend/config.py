"""Application settings and automated Groww authentication (TOTP flow).

The Groww access token expires every day at 06:00 IST and token generation is
hard-limited to 150 requests / 24h, so the token is cached on disk and reused
until the next 06:00 IST boundary.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, time as dtime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import pyotp
from growwapi import GrowwAPI
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
BASE_DIR = Path(__file__).resolve().parent
TOKEN_EXPIRY_TIME = dtime(6, 0)  # Groww tokens expire daily at 06:00 IST


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Credentials (.env keys: TOTP_TOKEN = TOTP API key, TOTP_QR = base32 TOTP secret)
    groww_api_key: str = Field(default="", alias="TOTP_TOKEN")
    groww_totp_secret: str = Field(default="", alias="TOTP_QR")

    # "groww" = live Groww market data, "mock" = synthetic demo data for local development
    data_source: Literal["groww", "mock"] = "groww"

    # Screener behaviour
    scan_interval_sec: int = 300          # LTP scan cadence (5 minutes)
    batch_size: int = 10                   # symbols per batch for daily-candle fetch
    batch_window_sec: float = 1.0          # one batch per second
    ltp_batch_size: int = 50               # get_ltp allows up to 50 symbols per call
    lookback_days: int = 5                 # breakout window (previous N trading days)
    history_calendar_days: int = 120       # daily candles fetched (chart + lookback)
    only_market_hours: bool = True         # after the startup scan, only scan 09:15–15:30 IST
    request_timeout_sec: int = 10          # SDK default is "infinite" – always pass one

    # Server
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    token_cache_path: Path = BASE_DIR / ".token_cache.json"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


class AuthError(RuntimeError):
    """Raised when a Groww access token cannot be obtained."""


def _last_expiry_boundary(now: datetime) -> datetime:
    """Most recent 06:00 IST at or before `now`."""
    boundary = now.replace(hour=TOKEN_EXPIRY_TIME.hour, minute=0, second=0, microsecond=0)
    return boundary if now >= boundary else boundary - timedelta(days=1)


def _read_cached_token(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text())
        created_at = datetime.fromisoformat(data["created_at"])
        token = data["token"]
    except FileNotFoundError:
        return None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        logger.warning("Ignoring malformed token cache at %s", path)
        return None
    if created_at >= _last_expiry_boundary(datetime.now(IST)) and token:
        return token
    return None


def _write_cached_token(path: Path, token: str) -> None:
    payload = json.dumps({"token": token, "created_at": datetime.now(IST).isoformat()})
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(payload)


def login(settings: Settings, *, force: bool = False) -> str:
    """Return a valid Groww access token, using the on-disk cache unless `force`.

    Blocking (network I/O) – call via `asyncio.to_thread` from async code.
    """
    if not settings.groww_api_key or not settings.groww_totp_secret:
        raise AuthError("TOTP_TOKEN and TOTP_QR must be set in bearish_bullish_backend/.env")

    if not force:
        cached = _read_cached_token(settings.token_cache_path)
        if cached:
            logger.info("Using cached Groww access token")
            return cached

    totp = pyotp.TOTP(settings.groww_totp_secret)
    last_error: Exception | None = None
    for attempt in range(2):
        # If we are within 2s of the 30s TOTP rollover, wait for the next code.
        if totp.interval - (time.time() % totp.interval) < 2:
            time.sleep(2.5)
        try:
            token = GrowwAPI.get_access_token(api_key=settings.groww_api_key, totp=totp.now())
        except Exception as exc:  # SDK raises GrowwAPIException / requests errors
            last_error = exc
            logger.warning("Groww login attempt %d failed: %s", attempt + 1, type(exc).__name__)
            time.sleep(3)
            continue
        if not token:
            last_error = AuthError("Empty token returned by Groww")
            continue
        _write_cached_token(settings.token_cache_path, token)
        logger.info("Generated new Groww access token")
        return token

    raise AuthError(f"Groww login failed: {last_error}") from last_error
