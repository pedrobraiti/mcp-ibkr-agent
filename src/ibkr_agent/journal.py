"""Backwards-compatible shim — the trade journal now lives in ``trading_core``.

New code should import from ``trading_core.journal``.
"""

from trading_core.journal import TradeJournal

__all__ = ["TradeJournal"]
