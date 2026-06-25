"""Append-only trade journal (audit log) — every order attempt and its outcome.

Persisted as JSONL so it is greppable and dependency-free. The path is local and
gitignored; trade data never goes into the repo. This is what answers the question
"what did my agent actually do?", and it backs the daily-spend limit and the
duplicate-order guard.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from .domain.models import OrderRequest, OrderResult, OrderSide, TradingMode

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else _PROJECT_ROOT / path


class TradeJournal:
    """Appends one JSONL record per order attempt and reads them back."""

    def __init__(self, path: str | Path, *, market_timezone: str = "America/New_York"):
        self._path = _resolve(path)
        self._tz = ZoneInfo(market_timezone)

    def record(
        self,
        *,
        request: OrderRequest,
        mode: TradingMode,
        dry_run: bool,
        notional: Decimal | None,
        result: OrderResult | None = None,
        error: Exception | None = None,
        sent: bool = False,
    ) -> dict:
        entry = {
            "timestamp": datetime.now(self._tz).isoformat(),
            "mode": str(mode),
            "symbol": request.symbol.upper(),
            "side": request.side.value,
            "order_type": request.order_type.value,
            "cash_qty": str(request.cash_qty) if request.cash_qty is not None else None,
            "quantity": str(request.quantity) if request.quantity is not None else None,
            "notional": str(notional) if notional is not None else None,
            "dry_run": result.dry_run if result is not None else dry_run,
            # `sent` = dispatched to the broker (it may have filled even if no order_id
            # came back, e.g. a timeout/503). The duplicate guard keys off this so a
            # retry of a sent-but-unconfirmed order is still caught.
            "sent": bool(sent) or (result is not None and result.order_id is not None),
            "order_id": result.order_id if result is not None else None,
            "status": result.status.value if result is not None else "error",
            "message": (result.message if result is not None else None)
            or (str(error) if error is not None else None),
        }
        self._append(entry)
        return entry

    def read(self, limit: int = 50) -> list[dict]:
        if not self._path.exists():
            return []
        entries: list[dict] = []
        corrupt = 0
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # One bad line must not brick reads — the daily-spend cap and the
                # duplicate guard depend on this, so skip it and surface the damage.
                corrupt += 1
        if corrupt:
            logger.warning(
                "Skipped %d corrupt line(s) in the trade journal %s", corrupt, self._path
            )
        return entries[-limit:] if limit else entries

    def spent_today(self) -> Decimal:
        """Sum of today's BUY notionals that may have spent money (market-tz).

        Counts a buy that was acked (``order_id``) OR merely dispatched (``sent``) — the
        latter may have filled even without an ack (timeout/503), so for a spend cap we
        must assume it did. Excludes buys the gateway resolved as rejected/cancelled, which
        moved no money.
        """
        today = datetime.now(self._tz).date().isoformat()
        total = Decimal(0)
        for entry in self.read(limit=0):
            if entry.get("side") != OrderSide.BUY.value or not entry.get("notional"):
                continue
            if not str(entry.get("timestamp", "")).startswith(today):
                continue
            if not (entry.get("order_id") or entry.get("sent")):
                continue
            if entry.get("status") in ("rejected", "cancelled"):
                continue
            try:
                total += Decimal(entry["notional"])
            except (InvalidOperation, ValueError):
                pass
        return total

    def has_recent_duplicate(self, request: OrderRequest, window_seconds: float) -> bool:
        """True if an identical order (symbol/side/size) was placed within the window."""
        if window_seconds <= 0:
            return False
        cutoff = datetime.now(self._tz) - timedelta(seconds=window_seconds)
        size = str(request.cash_qty if request.cash_qty is not None else request.quantity)
        for entry in reversed(self.read(limit=200)):
            # An order counts as a possible duplicate if it was dispatched to the broker
            # (`sent`) — even if no order_id came back (timeout/503), because it may have
            # filled. Pure guard-blocked attempts (never sent) don't count, and neither do
            # ones the gateway resolved as rejected/cancelled (nothing happened, so a
            # corrected retry must be allowed).
            if not (entry.get("sent") or entry.get("order_id")):
                continue
            if entry.get("status") in ("rejected", "cancelled"):
                continue
            entry_size = entry.get("cash_qty") or entry.get("quantity")
            # Match on order_type too: a resting STOP and a panic MARKET sell of the same
            # size are DIFFERENT orders — collapsing them would trap a genuine exit.
            if (
                entry.get("symbol") == request.symbol.upper()
                and entry.get("side") == request.side.value
                and entry.get("order_type") == request.order_type.value
                and entry_size == size
            ):
                try:
                    when = datetime.fromisoformat(entry["timestamp"])
                except (ValueError, KeyError):
                    continue
                if when >= cutoff:
                    return True
        return False

    def _append(self, entry: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
