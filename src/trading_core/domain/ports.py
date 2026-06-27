"""Domain ports (interfaces) — contracts that the concrete adapters implement.

These are async ``Protocol``s: the CPAPI implementation (and future adapters such as
ib_async for data, or OAuth for auth) must satisfy them without explicit inheritance.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol, runtime_checkable

from .models import (
    AccountSummary,
    BracketRequest,
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

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Quotes for several symbols in one call."""
        ...

    async def get_account_summary(self) -> AccountSummary:
        ...

    async def get_positions(self) -> list[Position]:
        ...

    async def held_quantity(self, symbol: str) -> Decimal | None:
        """Signed net quantity currently held for ``symbol`` (>0 long, <0 short, 0 flat).

        Returns ``None`` when holdings can't be confirmed (e.g. the instrument can't be
        resolved). The safety guard uses this to size exits and detect short-covers
        without knowing how each venue identifies an instrument (conid, base asset, ...).
        Implementations should refresh the eventually-consistent positions cache first.
        """
        ...

    async def invalidate_positions(self) -> None:
        """Best-effort hint to refresh the eventually-consistent positions cache."""
        ...


@runtime_checkable
class BrokerPort(Protocol):
    """Execution: place, query and cancel orders."""

    async def place_order(self, request: OrderRequest) -> OrderResult:
        ...

    async def place_bracket(self, bracket: BracketRequest) -> list[OrderResult]:
        """Place an entry order with attached take-profit and stop-loss exits (OCO)."""
        ...

    async def preview_order(self, request: OrderRequest) -> OrderPreview:
        """Estimate margin/commission/warnings for an order without sending it."""
        ...

    async def get_order_status(self, order_id: str) -> OrderResult:
        """Current status of a previously placed order (fill, avg price, state)."""
        ...

    async def cancel_order(self, order_id: str) -> OrderResult:
        ...

    async def get_live_orders(self) -> list[OrderResult]:
        ...
