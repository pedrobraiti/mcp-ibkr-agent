"""Domain ports (interfaces) — contracts that the concrete adapters implement.

These are async ``Protocol``s: the CPAPI implementation (and future adapters such as
ib_async for data, or OAuth for auth) must satisfy them without explicit inheritance.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import (
    AccountSummary,
    OrderPreview,
    OrderRequest,
    OrderResult,
    Position,
    Quote,
)


@runtime_checkable
class AuthPort(Protocol):
    """Manages the session/authentication with the broker (Gateway today, OAuth in the future)."""

    async def ensure_session(self) -> None:
        """Ensures a valid session, (re)authenticating or doing a keep-alive if needed."""
        ...

    async def is_authenticated(self) -> bool:
        ...


@runtime_checkable
class MarketDataPort(Protocol):
    """Market and account reads: symbol resolution, quote, balance and positions."""

    async def resolve_conid(self, symbol: str) -> int | None:
        ...

    async def get_quote(self, symbol: str) -> Quote | None:
        ...

    async def get_account_summary(self) -> AccountSummary:
        ...

    async def get_positions(self) -> list[Position]:
        ...


@runtime_checkable
class BrokerPort(Protocol):
    """Execution: place, query and cancel orders."""

    async def place_order(self, request: OrderRequest) -> OrderResult:
        ...

    async def preview_order(self, request: OrderRequest) -> OrderPreview:
        """Estimate margin/commission/warnings for an order without sending it."""
        ...

    async def cancel_order(self, order_id: str) -> OrderResult:
        ...

    async def get_live_orders(self) -> list[OrderResult]:
        ...
