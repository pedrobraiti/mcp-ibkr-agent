from decimal import Decimal

from ibkr_agent.config import Settings
from ibkr_agent.domain.models import (
    AccountSummary,
    OrderPreview,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    Position,
    Quote,
    TradingMode,
)
from ibkr_agent.journal import TradeJournal
from ibkr_agent.safety import GuardedBroker
from ibkr_agent.server import app
from ibkr_agent.server.app import mcp
from ibkr_agent.server.services import Services, build_services


async def test_tools_are_registered():
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    expected = {
        "session_status",
        "market_status",
        "get_quote",
        "account_summary",
        "positions",
        "portfolio",
        "buy",
        "sell",
        "close_position",
        "stop_order",
        "bracket_order",
        "preview_order",
        "order_status",
        "cancel_order",
        "open_orders",
        "trade_history",
    }
    assert expected <= names


def test_build_services_wires_without_network():
    svc = build_services(Settings(ibkr_account_id="DU1", trading_dry_run=True))
    assert svc.settings.ibkr_account_id == "DU1"
    assert isinstance(svc.market_is_open(), bool)
    assert svc.broker is not None


class _FakeAuth:
    async def ensure_session(self) -> None: ...


class _FakeMarketData:
    async def resolve_conid(self, symbol: str) -> int:
        return 1

    async def get_quote(self, symbol: str) -> Quote:
        return Quote(symbol=symbol, conid=1, last_price=Decimal("10"))

    async def get_account_summary(self) -> AccountSummary:
        return AccountSummary(account_id="DU1", available_funds=Decimal("100"))

    async def get_positions(self) -> list[Position]:
        return [Position(conid=1, symbol="AAPL", quantity=Decimal("1"),
                         unrealized_pnl=Decimal("2"))]

    async def invalidate_positions(self) -> None: ...


class _FakeInner:
    def __init__(self):
        self.placed: list[OrderRequest] = []

    async def place_order(self, request: OrderRequest) -> OrderResult:
        self.placed.append(request)
        return OrderResult(order_id="x", status=OrderStatus.SUBMITTED,
                           symbol=request.symbol, side=request.side)

    async def place_bracket(self, bracket) -> list[OrderResult]:
        self.placed.append(bracket.entry)
        return [
            OrderResult(order_id="p", status=OrderStatus.SUBMITTED,
                        symbol=bracket.entry.symbol, side=bracket.entry.side, message="entry"),
            OrderResult(order_id="tp", status=OrderStatus.SUBMITTED,
                        symbol=bracket.entry.symbol, side=OrderSide.SELL, message="take_profit"),
            OrderResult(order_id="sl", status=OrderStatus.SUBMITTED,
                        symbol=bracket.entry.symbol, side=OrderSide.SELL, message="stop_loss"),
        ]

    async def preview_order(self, request: OrderRequest) -> OrderPreview:
        return OrderPreview(symbol=request.symbol, side=request.side)

    async def get_order_status(self, order_id: str) -> OrderResult:
        return OrderResult(order_id=order_id, status=OrderStatus.FILLED,
                           symbol="AAPL", side=OrderSide.BUY,
                           filled_quantity=Decimal("0.5"), avg_price=Decimal("10"))

    async def cancel_order(self, order_id: str) -> OrderResult:
        raise NotImplementedError

    async def get_live_orders(self) -> list[OrderResult]:
        return []


async def test_smoke_buy_dry_run_and_portfolio_through_tools(tmp_path, monkeypatch):
    journal = TradeJournal(tmp_path / "trades.jsonl")
    market_data = _FakeMarketData()
    broker = GuardedBroker(
        _FakeInner(), market_data, mode=TradingMode.PAPER, allow_live=False,
        dry_run=True, max_order_value=Decimal("1000"), require_market_open=False,
        journal=journal,
    )
    svc = Services(
        settings=Settings(ibkr_account_id="DU1"), client=None, auth=_FakeAuth(),
        market_data=market_data, broker=broker, journal=journal,
    )
    monkeypatch.setattr(app, "_services", svc)

    bought = await app.buy("AAPL", cash_amount=10)
    assert bought["ok"] is True
    assert bought["data"]["dry_run"] is True

    snapshot = await app.portfolio()
    assert snapshot["ok"] is True
    assert snapshot["data"]["unrealized_pnl"] == "2"

    history = await app.trade_history()
    assert history["ok"] is True
    assert len(history["data"]) == 1  # the dry-run buy was journaled


async def test_order_status_tool(monkeypatch):
    svc = Services(
        settings=Settings(ibkr_account_id="DU1"), client=None, auth=_FakeAuth(),
        market_data=_FakeMarketData(),
        broker=GuardedBroker(
            _FakeInner(), _FakeMarketData(), mode=TradingMode.PAPER, allow_live=False,
            dry_run=True, max_order_value=Decimal("1000"), require_market_open=False,
        ),
        journal=TradeJournal("logs/unused.jsonl"),
    )
    monkeypatch.setattr(app, "_services", svc)

    status = await app.order_status("x")
    assert status["ok"] is True
    assert status["data"]["status"] == "filled"
    assert status["data"]["filled_quantity"] == "0.5"


async def test_limit_buy_builds_limit_order(tmp_path, monkeypatch):
    inner = _FakeInner()
    market_data = _FakeMarketData()
    broker = GuardedBroker(
        inner, market_data, mode=TradingMode.PAPER, allow_live=False,
        dry_run=False, max_order_value=Decimal("1000"), require_market_open=False,
        journal=TradeJournal(tmp_path / "trades.jsonl"),
    )
    svc = Services(
        settings=Settings(ibkr_account_id="DU1"), client=None, auth=_FakeAuth(),
        market_data=market_data, broker=broker, journal=broker._journal,
    )
    monkeypatch.setattr(app, "_services", svc)

    ok = await app.buy("AAPL", quantity=1, limit_price=9.5)
    assert ok["ok"] is True
    assert inner.placed[-1].order_type.value == "LMT"
    assert inner.placed[-1].limit_price == Decimal("9.5")

    rejected = await app.buy("AAPL", cash_amount=10, limit_price=9.5)
    assert rejected["ok"] is False
    assert "quantity" in rejected["error"]


async def test_stop_order_builds_stop(tmp_path, monkeypatch):
    inner = _FakeInner()
    md = _FakeMarketData()
    broker = GuardedBroker(
        inner, md, mode=TradingMode.PAPER, allow_live=False, dry_run=False,
        max_order_value=Decimal("1000"), require_market_open=False,
        journal=TradeJournal(tmp_path / "t.jsonl"),
    )
    svc = Services(settings=Settings(ibkr_account_id="DU1"), client=None, auth=_FakeAuth(),
                   market_data=md, broker=broker, journal=broker._journal)
    monkeypatch.setattr(app, "_services", svc)

    ok = await app.stop_order("AAPL", side="SELL", quantity=1, stop_price=8.0)
    assert ok["ok"] is True
    assert inner.placed[-1].order_type.value == "STP"
    assert inner.placed[-1].stop_price == Decimal("8.0")


async def test_bracket_order_through_tool(tmp_path, monkeypatch):
    inner = _FakeInner()
    md = _FakeMarketData()
    broker = GuardedBroker(
        inner, md, mode=TradingMode.PAPER, allow_live=False, dry_run=False,
        max_order_value=Decimal("1000"), require_market_open=False,
        journal=TradeJournal(tmp_path / "t.jsonl"),
    )
    svc = Services(settings=Settings(ibkr_account_id="DU1"), client=None, auth=_FakeAuth(),
                   market_data=md, broker=broker, journal=broker._journal)
    monkeypatch.setattr(app, "_services", svc)

    out = await app.bracket_order("AAPL", quantity=1, take_profit=12.0, stop_loss=8.0)
    assert out["ok"] is True
    legs = {leg["message"] for leg in out["data"]}
    assert legs == {"entry", "take_profit", "stop_loss"}
