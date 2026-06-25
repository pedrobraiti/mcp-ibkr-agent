"""Market and account reads via CPAPI: conid, quote, balance and positions."""

from __future__ import annotations

import asyncio
from decimal import Decimal, InvalidOperation

from ...domain.models import AccountSummary, Position, Quote
from .client import CpapiClient, CpapiError

FIELD_LAST = "31"
FIELD_BID = "84"
FIELD_ASK = "86"
_SNAPSHOT_FIELDS = f"{FIELD_LAST},{FIELD_BID},{FIELD_ASK}"
_SNAPSHOT_MAX_ATTEMPTS = 3


class CpapiMarketData:
    """Implements ``MarketDataPort`` on top of the CPAPI."""

    def __init__(
        self,
        client: CpapiClient,
        account_id: str,
        *,
        warmup_delay_seconds: float = 1.0,
    ):
        self._client = client
        self._account_id = account_id
        self._warmup_delay = warmup_delay_seconds
        self._conid_cache: dict[str, int] = {}

    async def resolve_conid(self, symbol: str) -> int | None:
        symbol = symbol.upper()
        if symbol in self._conid_cache:
            return self._conid_cache[symbol]

        data = await self._client.get("/trsrv/stocks", params={"symbols": symbol})
        conid = _pick_us_conid(data, symbol) if isinstance(data, dict) else None
        if conid is not None:
            self._conid_cache[symbol] = conid
        return conid

    async def get_quote(self, symbol: str) -> Quote | None:
        conid = await self.resolve_conid(symbol)
        if conid is None:
            return None

        params = {"conids": str(conid), "fields": _SNAPSHOT_FIELDS}
        snapshot: dict = {}
        # Warmup: the 1st call starts the stream and returns no price; retry until a real
        # last price arrives. Keep the latest row each attempt so bid/ask aren't lost if the
        # last price never fills (presence of the key isn't enough — it can be empty/"").
        for attempt in range(_SNAPSHOT_MAX_ATTEMPTS):
            data = await self._client.get("/iserver/marketdata/snapshot", params=params)
            if isinstance(data, list) and data:
                snapshot = data[0]
                if _last_price(snapshot.get(FIELD_LAST)) is not None:
                    break
            if attempt < _SNAPSHOT_MAX_ATTEMPTS - 1:
                await asyncio.sleep(self._warmup_delay)

        return Quote(
            symbol=symbol.upper(),
            conid=conid,
            last_price=_last_price(snapshot.get(FIELD_LAST)),
            bid=_to_decimal(snapshot.get(FIELD_BID)),
            ask=_to_decimal(snapshot.get(FIELD_ASK)),
        )

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Quotes for several symbols in one snapshot call (cheaper than N get_quote)."""
        conid_by_symbol: dict[str, int] = {}
        for symbol in symbols:
            conid = await self.resolve_conid(symbol)
            if conid is not None:
                conid_by_symbol[symbol.upper()] = conid
        if not conid_by_symbol:
            return []

        params = {
            "conids": ",".join(str(c) for c in conid_by_symbol.values()),
            "fields": _SNAPSHOT_FIELDS,
        }
        snapshots: dict[int, dict] = {}
        # Warmup: the 1st call starts the streams and returns no prices; retry until every
        # requested conid has a real (parseable) last price. Keep the latest row per conid
        # so bid/ask survive even if a last price never arrives for some symbol.
        for attempt in range(_SNAPSHOT_MAX_ATTEMPTS):
            data = await self._client.get("/iserver/marketdata/snapshot", params=params)
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict) and row.get("conid"):
                        snapshots[int(row["conid"])] = row
            priced = sum(
                1 for row in snapshots.values() if _last_price(row.get(FIELD_LAST)) is not None
            )
            if priced >= len(conid_by_symbol):
                break
            if attempt < _SNAPSHOT_MAX_ATTEMPTS - 1:
                await asyncio.sleep(self._warmup_delay)

        quotes: list[Quote] = []
        for symbol, conid in conid_by_symbol.items():
            snapshot = snapshots.get(conid, {})
            quotes.append(
                Quote(
                    symbol=symbol,
                    conid=conid,
                    last_price=_last_price(snapshot.get(FIELD_LAST)),
                    bid=_to_decimal(snapshot.get(FIELD_BID)),
                    ask=_to_decimal(snapshot.get(FIELD_ASK)),
                )
            )
        return quotes

    async def get_account_summary(self) -> AccountSummary:
        data = await self._client.get(f"/portfolio/{self._account_id}/summary")
        data = data if isinstance(data, dict) else {}
        return AccountSummary(
            account_id=self._account_id,
            available_funds=_amount(data, "availablefunds"),
            net_liquidation=_amount(data, "netliquidation"),
            buying_power=_amount(data, "buyingpower"),
        )

    async def get_positions(self) -> list[Position]:
        positions: list[Position] = []
        page = 0
        while True:
            data = await self._client.get(f"/portfolio/{self._account_id}/positions/{page}")
            if not isinstance(data, list) or not data:
                break
            for raw in data:
                position = _to_position(raw)
                if position.quantity != 0:  # IBKR keeps zeroed-out rows in the cache
                    positions.append(position)
            page += 1
        return positions

    async def invalidate_positions(self) -> None:
        """Ask the gateway to invalidate the positions cache (best-effort).

        The positions endpoint is eventually-consistent: after a recent order it
        may take tens of seconds to reflect. Invalidating helps, but does not
        guarantee an immediate update — so we don't fail the flow if it errors out.
        """
        try:
            await self._client.post(f"/portfolio/{self._account_id}/positions/invalidate")
        except CpapiError:
            pass


def _pick_us_conid(data: dict, symbol: str) -> int | None:
    entries = data.get(symbol) or data.get(symbol.upper())
    if not isinstance(entries, list):
        return None
    for entry in entries:
        contracts = entry.get("contracts", []) if isinstance(entry, dict) else []
        for contract in contracts:
            if contract.get("isUS") and contract.get("conid"):
                return int(contract["conid"])
    # No explicit isUS flag: accept a USD-denominated listing (a US contract that simply
    # omits isUS) — but never an arbitrary FOREIGN one, which would trade the wrong
    # instrument in a foreign currency and mis-size the value cap.
    for entry in entries:
        contracts = entry.get("contracts", []) if isinstance(entry, dict) else []
        for contract in contracts:
            if str(contract.get("currency", "")).upper() == "USD" and contract.get("conid"):
                return int(contract["conid"])
    return None


def _to_position(raw: dict) -> Position:
    # Quantity stays exact (fractional shares); money fields come as noisy floats
    # from IBKR, so round them to cents like the balances.
    return Position(
        conid=int(raw.get("conid", 0)),
        symbol=str(raw.get("contractDesc") or raw.get("ticker") or raw.get("symbol") or ""),
        quantity=_to_decimal(raw.get("position")) or Decimal(0),
        avg_cost=_cents(raw.get("avgCost")),
        market_price=_cents(raw.get("mktPrice")),
        market_value=_cents(raw.get("mktValue")),
        unrealized_pnl=_cents(raw.get("unrealizedPnl")),
    )


def _cents(value: object) -> Decimal | None:
    amount = _to_decimal(value)
    return amount.quantize(Decimal("0.01")) if amount is not None else None


def _amount(data: dict, key: str) -> Decimal | None:
    field = data.get(key)
    raw = _to_decimal(field.get("amount")) if isinstance(field, dict) else _to_decimal(field)
    # Balance values come as floats with noise (e.g. 8.869999...) — round to cents.
    return raw.quantize(Decimal("0.01")) if raw is not None else None


def _last_price(value: object) -> Decimal | None:
    """Parse IBKR field 31 ("Last"), stripping a leading state letter if present.

    The gateway prefixes the last price with a state code when there's no live trade:
    ``"C195.50"`` (previous close, pre/post-market) or ``"H195.50"`` (halted). Without
    stripping it, ``_to_decimal`` returns None and a real price is reported as missing.
    """
    if isinstance(value, str) and value[:1].isalpha():
        value = value[1:]
    return _to_decimal(value)


def _to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    # Reject NaN/Infinity: a non-finite money value would crash a later quantize, or
    # silently become a NaN balance/price.
    return result if result.is_finite() else None
