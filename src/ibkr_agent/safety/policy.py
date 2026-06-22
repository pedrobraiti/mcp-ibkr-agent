"""Safety locks over order execution.

``GuardedBroker`` is a decorator over ``BrokerPort``: it applies the hard rules BEFORE
delegating to the real broker. Rules:
  1. Live only with ``allow_live=True`` (otherwise blocked).
  2. The order's notional must not exceed ``max_order_value``.
  3. The market must be open (RTH), if required.
  4. ``dry_run`` (default): validates everything but does NOT send the order — returns an
     ``OrderResult`` marked with ``dry_run=True``.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from ..domain.models import OrderRequest, OrderResult, OrderStatus, TradingMode
from ..domain.ports import BrokerPort, MarketDataPort


class SafetyError(Exception):
    """The order violates a safety rule — it must not be sent."""


class GuardedBroker:
    """Implements ``BrokerPort`` by wrapping another ``BrokerPort`` with safety locks."""

    def __init__(
        self,
        inner: BrokerPort,
        market_data: MarketDataPort,
        *,
        mode: TradingMode,
        allow_live: bool,
        dry_run: bool,
        max_order_value: Decimal,
        require_market_open: bool = True,
        is_market_open: Callable[[], bool] = lambda: True,
    ):
        self._inner = inner
        self._market_data = market_data
        self._mode = mode
        self._allow_live = allow_live
        self._dry_run = dry_run
        self._max_order_value = max_order_value
        self._require_market_open = require_market_open
        self._is_market_open = is_market_open

    async def place_order(self, request: OrderRequest) -> OrderResult:
        if self._mode is TradingMode.LIVE and not self._allow_live:
            raise SafetyError(
                "LIVE mode blocked: set TRADING_ALLOW_LIVE=true to trade with real money."
            )

        if self._require_market_open and not self._is_market_open():
            raise SafetyError(
                "Market closed: orders are only accepted during regular trading hours (RTH)."
            )

        notional = await self._notional(request)
        if notional is not None and notional > self._max_order_value:
            raise SafetyError(
                f"Order of ~US${notional} exceeds the MAX_ORDER_VALUE limit "
                f"(US${self._max_order_value})."
            )

        if self._dry_run:
            return OrderResult(
                status=OrderStatus.PENDING,
                symbol=request.symbol.upper(),
                side=request.side,
                dry_run=True,
                message=f"dry-run: order validated, NOT sent (notional ~US${notional}).",
            )

        return await self._inner.place_order(request)

    async def cancel_order(self, order_id: str) -> OrderResult:
        return await self._inner.cancel_order(order_id)

    async def get_live_orders(self) -> list[OrderResult]:
        return await self._inner.get_live_orders()

    async def _notional(self, request: OrderRequest) -> Decimal | None:
        """Estimated order value in US$. For cashQty it's direct; for quantity it uses the quote."""
        if request.cash_qty is not None:
            return request.cash_qty

        quote = await self._market_data.get_quote(request.symbol)
        price = quote.last_price if quote else None
        if price is None:
            raise SafetyError(
                f"No price for {request.symbol}: cannot validate the order's value limit."
            )
        return price * (request.quantity or Decimal(0))
