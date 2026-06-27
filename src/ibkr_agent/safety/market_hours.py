"""Backwards-compatible shim — market hours now live in ``trading_core.safety``.

New code should import from ``trading_core.safety.market_hours``.
"""

from trading_core.safety.market_hours import is_market_open_at, is_market_open_now

__all__ = ["is_market_open_at", "is_market_open_now"]
