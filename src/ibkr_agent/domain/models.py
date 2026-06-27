"""Backwards-compatible shim — the domain models now live in ``trading_core``.

Kept so existing imports (``ibkr_agent.domain.models``) and the test-suite keep working
after the core was extracted. New code should import from ``trading_core.domain.models``.
"""

from trading_core.domain.models import (
    AccountSummary,
    BracketRequest,
    OrderPreview,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Quote,
    TradingMode,
    TrailingType,
)

__all__ = [
    "AccountSummary",
    "BracketRequest",
    "OrderPreview",
    "OrderRequest",
    "OrderResult",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "Position",
    "Quote",
    "TradingMode",
    "TrailingType",
]
