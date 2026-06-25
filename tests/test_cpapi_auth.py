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
