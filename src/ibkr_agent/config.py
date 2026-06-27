"""Central configuration, loaded from environment variables / `.env`."""

from __future__ import annotations

import logging
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from trading_core.domain.models import TradingMode

logger = logging.getLogger(__name__)

# Absolute path to the .env at the project root, so the server can find it regardless of
# the directory it is started from (e.g. when Claude Code launches the MCP).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Prefixes of settings that affect safety/behavior. A key with one of these prefixes that
# isn't a known field is almost certainly a typo — and because unknown keys are ignored,
# a typo silently reverts the setting to its default (which for caps/lists means OFF).
_SAFETY_PREFIXES = ("TRADING_", "MAX_", "SYMBOL_", "IBKR_", "DUPLICATE_", "MARKET_", "REAUTH_")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE), env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # CPAPI connection
    ibkr_api_base_url: str = "https://localhost:5000/v1/api"
    ibkr_account_id: str = ""
    ibkr_trading_mode: TradingMode = TradingMode.PAPER

    # Safety
    trading_allow_live: bool = False
    trading_dry_run: bool = True
    # Allow a SELL larger than the held position (i.e. opening a short). Off by default.
    trading_allow_short: bool = False
    max_order_value: Decimal = Decimal("100")
    # Cumulative spend across all buys in a day (market tz). None = no daily cap.
    max_daily_value: Decimal | None = None
    # Reject an identical order (symbol/side/size) placed within this window. 0 = off.
    duplicate_window_seconds: float = 5.0
    # Comma-separated tickers. If allowlist is set, only those can be traded; anything
    # in the denylist is always blocked. Empty = no restriction.
    symbol_allowlist: str = ""
    symbol_denylist: str = ""

    # Audit
    trade_journal_path: str = "logs/trades.jsonl"

    # Optional webhook (ntfy/Discord/generic) POSTed when the session needs reauth.
    reauth_webhook_url: str = ""

    # Session / network
    tickle_interval_seconds: int = 60
    request_timeout_seconds: float = 15.0

    # Market
    market_timezone: str = "America/New_York"
    market_open_time: str = "09:30"
    market_close_time: str = "16:00"

    log_level: str = "INFO"


def _warn_unknown_safety_keys() -> None:
    """Warn if the .env has a safety-prefixed key that maps to no setting (likely a typo).

    A misspelled ``MAX_DAILY_VALUE`` / ``SYMBOL_ALLOWLIST`` / ``TRADING_*`` is silently
    ignored and the protection reverts to its default — often OFF. Surfacing it loudly is
    cheap and turns a silent fail-open into a visible warning.
    """
    if not _ENV_FILE.exists():
        return
    known = {name.upper() for name in Settings.model_fields}
    try:
        lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip().upper()
        if key in known:
            continue
        if key.startswith(_SAFETY_PREFIXES):
            logger.warning(
                "Unrecognized env key %r in .env — it is IGNORED. Check for a typo; a "
                "misspelled safety setting silently reverts to its default.",
                key,
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _warn_unknown_safety_keys()
    return settings
