"""Backwards-compatible shim — the safety layer now lives in ``trading_core.safety``.

New code should import from ``trading_core.safety``.
"""

from trading_core.safety import (
    GuardedBroker,
    SafetyError,
    is_market_open_at,
    is_market_open_now,
)

__all__ = ["GuardedBroker", "SafetyError", "is_market_open_at", "is_market_open_now"]
