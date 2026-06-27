"""Configuration for the crypto server, loaded from environment variables / `.env`.

Adds the ``CRYPTO_*`` keys. The live and dry-run gates are venue-specific
(``CRYPTO_ALLOW_LIVE`` / ``CRYPTO_DRY_RUN``) so arming the IBKR server does NOT arm the
crypto server; only the policy limits (``MAX_ORDER_VALUE``, ``MAX_DAILY_VALUE``,
``DUPLICATE_WINDOW_SECONDS``) are shared across both venues.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from trading_core.domain.models import TradingMode

logger = logging.getLogger(__name__)

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# We only police the CRYPTO_* keys this server owns: the shared .env also holds the IBKR
# server's keys (IBKR_*, and IBKR-only TRADING_* like TRADING_ALLOW_LIVE), and warning on
# those here would be a false positive. A misspelled shared key is caught by the IBKR config.
_SAFETY_PREFIXES = ("CRYPTO_",)


class CryptoMode(StrEnum):
    SANDBOX = "sandbox"
    LIVE = "live"


class CryptoSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE), env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # --- crypto (CCXT) ---
    crypto_exchange: str = "binance"
    crypto_api_key: str = ""
    crypto_api_secret: str = ""
    crypto_api_password: str = ""  # only some exchanges (okx, kucoin) require a passphrase
    crypto_trading_mode: CryptoMode = CryptoMode.SANDBOX
    crypto_quote_ccy: str = "USDT"
    # Hard spot-only lock. When false, selling more than held (a short) is blocked.
    crypto_allow_margin: bool = False
    # Venue-specific real-money arm — separate from the IBKR gate on purpose.
    crypto_allow_live: bool = False
    # Venue-specific dry-run (validate but don't send). Independent of the IBKR
    # TRADING_DRY_RUN on purpose: arming/disarming one venue must not affect the other, and
    # crypto stays safe-by-default even when the shared IBKR dry-run is turned off.
    crypto_dry_run: bool = True

    # --- shared safety gates (policy limits, shared across both venues) ---
    max_order_value: Decimal = Decimal("100")
    max_daily_value: Decimal | None = None
    duplicate_window_seconds: float = 5.0
    symbol_allowlist: str = ""
    symbol_denylist: str = ""

    # Separate audit log so crypto and IBKR caps/duplicate-guards don't mix venues.
    crypto_trade_journal_path: str = "logs/crypto_trades.jsonl"

    log_level: str = "INFO"

    @property
    def trading_mode(self) -> TradingMode:
        """Map the crypto sandbox/live mode onto the guard's paper/live concept."""
        return (
            TradingMode.LIVE
            if self.crypto_trading_mode is CryptoMode.LIVE
            else TradingMode.PAPER
        )

    @property
    def is_sandbox(self) -> bool:
        return self.crypto_trading_mode is CryptoMode.SANDBOX


def _warn_unknown_safety_keys() -> None:
    if not _ENV_FILE.exists():
        return
    known = {name.upper() for name in CryptoSettings.model_fields}
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
def get_settings() -> CryptoSettings:
    settings = CryptoSettings()
    _warn_unknown_safety_keys()
    return settings
