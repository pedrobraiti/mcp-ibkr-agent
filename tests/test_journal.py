from decimal import Decimal

from ibkr_agent.domain.models import (
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    TradingMode,
)
from ibkr_agent.journal import TradeJournal

PLACED = OrderResult(order_id="1", status=OrderStatus.SUBMITTED, symbol="AAPL", side=OrderSide.BUY)


def test_record_and_read(tmp_path):
    journal = TradeJournal(tmp_path / "trades.jsonl")
    request = OrderRequest(symbol="aapl", side=OrderSide.BUY, cash_qty=Decimal("50"))

    journal.record(
        request=request, mode=TradingMode.PAPER, dry_run=False,
        notional=Decimal("50"), result=PLACED,
    )

    rows = journal.read()
    assert len(rows) == 1
    assert rows[0]["symbol"] == "AAPL"
    assert rows[0]["side"] == "BUY"
    assert rows[0]["order_id"] == "1"
    assert rows[0]["notional"] == "50"


def test_spent_today_counts_only_placed_buys(tmp_path):
    journal = TradeJournal(tmp_path / "trades.jsonl")
    buy = OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("30"))

    journal.record(request=buy, mode=TradingMode.LIVE, dry_run=False,
                   notional=Decimal("30"), result=PLACED)
    journal.record(request=buy, mode=TradingMode.LIVE, dry_run=False,
                   notional=Decimal("20"), result=PLACED)
    # A dry-run has no order_id and must NOT count toward the daily spend.
    dry = OrderResult(status=OrderStatus.PENDING, symbol="AAPL", side=OrderSide.BUY, dry_run=True)
    journal.record(request=buy, mode=TradingMode.LIVE, dry_run=True,
                   notional=Decimal("999"), result=dry)

    assert journal.spent_today() == Decimal("50")


def test_read_skips_corrupt_lines_instead_of_crashing(tmp_path):
    # A single malformed line must not brick reads — otherwise the daily-spend cap and
    # duplicate guard (which read the whole journal) would block ALL trading.
    path = tmp_path / "trades.jsonl"
    journal = TradeJournal(path)
    journal.record(request=OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("30")),
                   mode=TradingMode.LIVE, dry_run=False, notional=Decimal("30"), result=PLACED)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{ this is not valid json\n")

    rows = journal.read(limit=0)
    assert len(rows) == 1
    assert journal.spent_today() == Decimal("30")


def test_sent_but_unconfirmed_order_counts_as_duplicate(tmp_path):
    # An order dispatched to the broker but whose call errored (timeout/503) has no
    # order_id, yet may have filled — a retry must still be caught as a duplicate.
    journal = TradeJournal(tmp_path / "trades.jsonl")
    request = OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("10"))

    journal.record(request=request, mode=TradingMode.LIVE, dry_run=False,
                   notional=Decimal("10"), error=RuntimeError("timeout"), sent=True)

    assert journal.has_recent_duplicate(request, 5) is True


def test_guard_blocked_attempt_is_not_a_duplicate(tmp_path):
    # An attempt blocked BEFORE being sent (sent=False, no order_id) must not block a
    # later legitimate order.
    journal = TradeJournal(tmp_path / "trades.jsonl")
    request = OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("10"))

    journal.record(request=request, mode=TradingMode.LIVE, dry_run=False,
                   notional=Decimal("10"), error=RuntimeError("market closed"), sent=False)

    assert journal.has_recent_duplicate(request, 5) is False


def test_spent_today_counts_sent_unconfirmed_and_excludes_failed(tmp_path):
    journal = TradeJournal(tmp_path / "trades.jsonl")
    buy = OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("30"))
    # Sent but unconfirmed (no order_id) — may have spent money → must count.
    journal.record(request=buy, mode=TradingMode.LIVE, dry_run=False,
                   notional=Decimal("30"), error=RuntimeError("503"), sent=True)
    # Acked then rejected — moved no money → must NOT count.
    rejected = OrderResult(order_id="9", status=OrderStatus.REJECTED, symbol="AAPL",
                           side=OrderSide.BUY)
    journal.record(request=buy, mode=TradingMode.LIVE, dry_run=False,
                   notional=Decimal("70"), result=rejected, sent=True)

    assert journal.spent_today() == Decimal("30")


def test_different_order_type_is_not_a_duplicate(tmp_path):
    # A resting STOP and a panic MARKET sell of the same size are different orders — the
    # second must not be trapped as a duplicate.
    journal = TradeJournal(tmp_path / "trades.jsonl")
    stop = OrderRequest(symbol="AAPL", side=OrderSide.SELL, quantity=Decimal("5"),
                        order_type=OrderType.STOP, stop_price=Decimal("40"))
    journal.record(request=stop, mode=TradingMode.LIVE, dry_run=False,
                   notional=None, result=PLACED, sent=True)

    market_sell = OrderRequest(symbol="AAPL", side=OrderSide.SELL, quantity=Decimal("5"))
    assert journal.has_recent_duplicate(market_sell, 30) is False


def test_rejected_order_does_not_block_retry(tmp_path):
    journal = TradeJournal(tmp_path / "trades.jsonl")
    buy = OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("10"))
    rejected = OrderResult(order_id="9", status=OrderStatus.REJECTED, symbol="AAPL",
                           side=OrderSide.BUY)
    journal.record(request=buy, mode=TradingMode.LIVE, dry_run=False,
                   notional=Decimal("10"), result=rejected, sent=True)

    assert journal.has_recent_duplicate(buy, 30) is False


def test_has_recent_duplicate(tmp_path):
    journal = TradeJournal(tmp_path / "trades.jsonl")
    request = OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("10"))

    assert journal.has_recent_duplicate(request, 5) is False
    journal.record(request=request, mode=TradingMode.LIVE, dry_run=False,
                   notional=Decimal("10"), result=PLACED)

    assert journal.has_recent_duplicate(request, 5) is True
    # A different size is not a duplicate.
    other = OrderRequest(symbol="AAPL", side=OrderSide.BUY, cash_qty=Decimal("11"))
    assert journal.has_recent_duplicate(other, 5) is False
    # Window 0 disables the check.
    assert journal.has_recent_duplicate(request, 0) is False
