"""Startup-warning behavior in the config loaders (offline — no .env required)."""

import logging
from decimal import Decimal

from crypto_agent.config import CryptoMode, CryptoSettings
from crypto_agent.config import _warn_if_daily_cap_off as crypto_warn
from ibkr_agent.config import Settings
from ibkr_agent.config import _warn_if_daily_cap_off as ibkr_warn

_NEEDLE = "MAX_DAILY_VALUE unset"


def _warned(caplog) -> bool:
    return any(_NEEDLE in record.getMessage() for record in caplog.records)


def test_ibkr_warns_when_daily_cap_off_and_live_allowed(caplog):
    settings = Settings(max_daily_value=None, trading_allow_live=True)
    with caplog.at_level(logging.WARNING, logger="ibkr_agent.config"):
        ibkr_warn(settings)
    assert _warned(caplog)


def test_ibkr_silent_when_daily_cap_set(caplog):
    settings = Settings(max_daily_value=Decimal("500"), trading_allow_live=True)
    with caplog.at_level(logging.WARNING, logger="ibkr_agent.config"):
        ibkr_warn(settings)
    assert not _warned(caplog)


def test_ibkr_silent_when_live_not_allowed(caplog):
    settings = Settings(max_daily_value=None, trading_allow_live=False)
    with caplog.at_level(logging.WARNING, logger="ibkr_agent.config"):
        ibkr_warn(settings)
    assert not _warned(caplog)


def test_crypto_warns_when_daily_cap_off_and_live_allowed(caplog):
    settings = CryptoSettings(
        max_daily_value=None, crypto_allow_live=True, crypto_trading_mode=CryptoMode.LIVE
    )
    with caplog.at_level(logging.WARNING, logger="crypto_agent.config"):
        crypto_warn(settings)
    assert _warned(caplog)


def test_crypto_silent_when_daily_cap_set(caplog):
    settings = CryptoSettings(max_daily_value=Decimal("500"), crypto_allow_live=True)
    with caplog.at_level(logging.WARNING, logger="crypto_agent.config"):
        crypto_warn(settings)
    assert not _warned(caplog)


def test_crypto_silent_when_live_not_allowed(caplog):
    settings = CryptoSettings(max_daily_value=None, crypto_allow_live=False)
    with caplog.at_level(logging.WARNING, logger="crypto_agent.config"):
        crypto_warn(settings)
    assert not _warned(caplog)


# An empty value in the .env file already loads as None; an empty OS env var (MAX_DAILY_VALUE=)
# arrives as "" and used to crash pydantic's Decimal parsing, preventing the server from
# starting. The before-validators make the two paths behave the same.
def test_ibkr_empty_daily_cap_env_loads_as_none(monkeypatch):
    monkeypatch.setenv("MAX_DAILY_VALUE", "")
    assert Settings().max_daily_value is None


def test_ibkr_empty_order_cap_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("MAX_ORDER_VALUE", "")
    assert Settings().max_order_value == Decimal("100")


def test_crypto_empty_daily_cap_env_loads_as_none(monkeypatch):
    monkeypatch.setenv("MAX_DAILY_VALUE", "")
    assert CryptoSettings().max_daily_value is None


def test_crypto_empty_order_cap_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("MAX_ORDER_VALUE", "")
    assert CryptoSettings().max_order_value == Decimal("100")
