from decimal import Decimal

import httpx
import respx

from ibkr_agent.adapters.cpapi import CpapiClient, CpapiMarketData

BASE = "https://localhost:5000/v1/api"
ACCT = "DU123"


@respx.mock
async def test_resolve_conid_prefers_us_contract():
    stocks = respx.get(f"{BASE}/trsrv/stocks").mock(
        return_value=httpx.Response(
            200,
            json={
                "AAPL": [
                    {
                        "contracts": [
                            {"conid": 111, "exchange": "LSE", "isUS": False},
                            {"conid": 265598, "exchange": "NASDAQ", "isUS": True},
                        ]
                    }
                ]
            },
        )
    )
    client = CpapiClient(BASE)
    md = CpapiMarketData(client, ACCT, warmup_delay_seconds=0)

    assert await md.resolve_conid("aapl") == 265598
    # 2nd call uses the cache (doesn't hit the API again).
    assert await md.resolve_conid("AAPL") == 265598
    assert stocks.call_count == 1
    await client.aclose()


@respx.mock
async def test_get_quote_handles_snapshot_warmup():
    respx.get(f"{BASE}/trsrv/stocks").mock(
        return_value=httpx.Response(
            200, json={"AAPL": [{"contracts": [{"conid": 265598, "isUS": True}]}]}
        )
    )
    snapshot = respx.get(f"{BASE}/iserver/marketdata/snapshot").mock(
        side_effect=[
            httpx.Response(200, json=[{"conid": 265598}]),  # warmup: no price
            httpx.Response(
                200, json=[{"conid": 265598, "31": "150.25", "84": "150.20", "86": "150.30"}]
            ),
        ]
    )
    client = CpapiClient(BASE)
    md = CpapiMarketData(client, ACCT, warmup_delay_seconds=0)

    quote = await md.get_quote("AAPL")

    assert quote is not None
    assert quote.last_price == Decimal("150.25")
    assert quote.bid == Decimal("150.20")
    assert quote.ask == Decimal("150.30")
    assert snapshot.call_count == 2
    await client.aclose()


@respx.mock
async def test_get_quotes_batches_symbols_in_one_snapshot():
    respx.get(f"{BASE}/trsrv/stocks", params={"symbols": "AAPL"}).mock(
        return_value=httpx.Response(
            200, json={"AAPL": [{"contracts": [{"conid": 1, "isUS": True}]}]})
    )
    respx.get(f"{BASE}/trsrv/stocks", params={"symbols": "MSFT"}).mock(
        return_value=httpx.Response(
            200, json={"MSFT": [{"contracts": [{"conid": 2, "isUS": True}]}]})
    )
    snapshot = respx.get(f"{BASE}/iserver/marketdata/snapshot").mock(
        return_value=httpx.Response(200, json=[
            {"conid": 1, "31": "150.00"},
            {"conid": 2, "31": "400.00"},
        ])
    )
    client = CpapiClient(BASE)
    md = CpapiMarketData(client, ACCT, warmup_delay_seconds=0)

    quotes = await md.get_quotes(["aapl", "msft"])

    assert {q.symbol: q.last_price for q in quotes} == {
        "AAPL": Decimal("150.00"), "MSFT": Decimal("400.00")
    }
    assert snapshot.call_count == 1  # both symbols in a single snapshot call
    await client.aclose()


@respx.mock
async def test_get_positions_skips_zero_quantity_rows():
    respx.get(f"{BASE}/portfolio/{ACCT}/positions/0").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"conid": 265598, "contractDesc": "AAPL", "position": 0.0066},
                {"conid": 8314, "contractDesc": "IBM", "position": 0.0},
            ],
        )
    )
    respx.get(f"{BASE}/portfolio/{ACCT}/positions/1").mock(
        return_value=httpx.Response(200, json=[])
    )
    client = CpapiClient(BASE)
    md = CpapiMarketData(client, ACCT, warmup_delay_seconds=0)

    rows = await md.get_positions()

    assert len(rows) == 1
    assert rows[0].symbol == "AAPL"
    assert rows[0].quantity == Decimal("0.0066")
    await client.aclose()


@respx.mock
async def test_account_summary_parses_amount_objects():
    respx.get(f"{BASE}/portfolio/{ACCT}/summary").mock(
        return_value=httpx.Response(
            200,
            json={
                "availablefunds": {"amount": 1000.5, "currency": "USD"},
                "netliquidation": {"amount": 2500.0, "currency": "USD"},
            },
        )
    )
    client = CpapiClient(BASE)
    md = CpapiMarketData(client, ACCT, warmup_delay_seconds=0)

    summary = await md.get_account_summary()

    assert summary.available_funds == Decimal("1000.5")
    assert summary.net_liquidation == Decimal("2500.0")
    await client.aclose()
