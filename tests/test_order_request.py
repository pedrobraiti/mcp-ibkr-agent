from decimal import Decimal

import pytest
from pydantic import ValidationError

from ibkr_agent.domain.models import BracketRequest, OrderRequest, OrderSide, OrderType


def test_quantity_order_is_valid_and_not_fractional():
    order = OrderRequest(symbol="AAPL", side=OrderSide.BUY, quantity=2)
    assert order.is_fractional is False


def test_fractional_quantity_is_accepted():
    order = OrderRequest(symbol="AAPL", side=OrderSide.SELL, quantity=Decimal("0.0066"))
    assert order.quantity == Decimal("0.0066")
    assert order.is_fractional is False  # is_fractional reflects cashQty, not the quantity


def test_cash_qty_order_is_fractional():
    order = OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("50"))
    assert order.is_fractional is True


def test_rejects_both_quantity_and_cash_qty():
    with pytest.raises(ValidationError):
        OrderRequest(symbol="AAPL", side=OrderSide.BUY, quantity=2, cash_qty=Decimal("50"))


def test_rejects_neither_sizing():
    with pytest.raises(ValidationError):
        OrderRequest(symbol="AAPL", side=OrderSide.BUY)


def test_limit_order_requires_limit_price():
    with pytest.raises(ValidationError):
        OrderRequest(symbol="AAPL", side=OrderSide.BUY, quantity=1, order_type=OrderType.LIMIT)


def test_symbol_whitespace_is_stripped():
    # A padded symbol must be normalized so it can't slip past the deny/allow-list.
    order = OrderRequest(symbol="  AAPL ", side=OrderSide.BUY, quantity=1)
    assert order.symbol == "AAPL"


def test_cash_qty_rejected_on_sell():
    # cashQty is buy-only; a cash SELL has no quantity and would bypass the short guard.
    with pytest.raises(ValidationError):
        OrderRequest(symbol="AAPL", side=OrderSide.SELL, cash_qty=Decimal("50"))


def test_cash_qty_rejected_on_limit():
    with pytest.raises(ValidationError):
        OrderRequest(
            symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("50"),
            order_type=OrderType.LIMIT, limit_price=Decimal("10"),
        )


def _entry(side: OrderSide, **kw) -> OrderRequest:
    return OrderRequest(symbol="AAPL", side=side, quantity=1, **kw)


def test_bracket_rejects_reversed_buy_exits():
    # BUY bracket with take_profit BELOW stop_loss would liquidate on fill.
    with pytest.raises(ValidationError):
        BracketRequest(
            entry=_entry(OrderSide.BUY),
            take_profit_price=Decimal("100"),
            stop_loss_price=Decimal("200"),
        )


def test_bracket_accepts_sane_buy_exits():
    bracket = BracketRequest(
        entry=_entry(OrderSide.BUY),
        take_profit_price=Decimal("200"),
        stop_loss_price=Decimal("100"),
    )
    assert bracket.take_profit_price > bracket.stop_loss_price


def test_bracket_rejects_tp_below_entry_limit():
    # take_profit must clear the entry limit on a BUY bracket.
    with pytest.raises(ValidationError):
        BracketRequest(
            entry=_entry(OrderSide.BUY, order_type=OrderType.LIMIT, limit_price=Decimal("150")),
            take_profit_price=Decimal("140"),
            stop_loss_price=Decimal("100"),
        )
