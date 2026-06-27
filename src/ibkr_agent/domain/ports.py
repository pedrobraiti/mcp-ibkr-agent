"""Backwards-compatible shim — the domain ports now live in ``trading_core``.

New code should import from ``trading_core.domain.ports``.
"""

from trading_core.domain.ports import AuthPort, BrokerPort, MarketDataPort

__all__ = ["AuthPort", "BrokerPort", "MarketDataPort"]
