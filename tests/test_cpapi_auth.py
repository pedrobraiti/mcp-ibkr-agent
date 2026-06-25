import httpx
import respx

from ibkr_agent.adapters.cpapi import CpapiClient, GatewayAuth

BASE = "https://localhost:5000/v1/api"


@respx.mock
async def test_account_info_trusts_ibkr_is_paper_flag():
    respx.get(f"{BASE}/iserver/accounts").mock(
        return_value=httpx.Response(200, json={"selectedAccount": "U24235856", "isPaper": False})
    )
    auth = GatewayAuth(CpapiClient(BASE))

    info = await auth.account_info()

    assert info["account_id"] == "U24235856"
    assert info["is_paper"] is False
    assert info["account_type"] == "LIVE"


@respx.mock
async def test_account_info_falls_back_to_prefix_when_flag_missing():
    respx.get(f"{BASE}/iserver/accounts").mock(
        return_value=httpx.Response(200, json={"selectedAccount": "DU456"})
    )
    auth = GatewayAuth(CpapiClient(BASE))

    info = await auth.account_info()

    assert info["is_paper"] is True
    assert info["account_type"] == "PAPER"


@respx.mock
async def test_account_info_coerces_string_is_paper():
    # Some gateway builds send isPaper as a string — it must resolve to a strict bool.
    respx.get(f"{BASE}/iserver/accounts").mock(
        return_value=httpx.Response(200, json={"selectedAccount": "U1", "isPaper": "false"})
    )
    info = await GatewayAuth(CpapiClient(BASE)).account_info()
    assert info["is_paper"] is False
    assert info["account_type"] == "LIVE"


@respx.mock
async def test_account_info_unknown_prefix_stays_none_not_paper():
    # A real-money non-"U" account (advisor "F…") with no isPaper must NOT be guessed as
    # paper — it stays unknown (None) so the guard fails closed.
    respx.get(f"{BASE}/iserver/accounts").mock(
        return_value=httpx.Response(200, json={"selectedAccount": "F1234567"})
    )
    info = await GatewayAuth(CpapiClient(BASE)).account_info()
    assert info["is_paper"] is None
    assert info["account_type"] is None
