"""Healthcheck for the IBKR connection.

Checks whether the Client Portal Gateway is logged in and connected, and prints a
readable report (server version, account, fractional flags, balance and a quote).

Usage: python -m ibkr_agent.healthcheck   (with the gateway running and logged in)
"""

from __future__ import annotations

import asyncio
import warnings

from .adapters.cpapi import CpapiClient, CpapiMarketData, GatewayAuth
from .config import get_settings

warnings.filterwarnings("ignore")


async def _run() -> int:
    settings = get_settings()
    client = CpapiClient(settings.ibkr_api_base_url, timeout=settings.request_timeout_seconds)
    auth = GatewayAuth(client)
    try:
        status = await auth.status()
        server = (status.get("serverInfo") or {}).get("serverVersion", "?")
        print(f"Server: {server}")
        print(
            f"Auth: authenticated={status.get('authenticated')} "
            f"connected={status.get('connected')} competing={status.get('competing')}"
        )
        if not status.get("authenticated"):
            print("\n[WARN] Session not authenticated.")
            print("   Log in at https://localhost:5000 (with the gateway running) and run again.")
            return 1

        accounts = await client.get("/iserver/accounts")
        acct = accounts.get("selectedAccount") if isinstance(accounts, dict) else None
        props = (accounts.get("acctProps", {}) or {}).get(acct, {}) if acct else {}
        print(f"\nAccount: {acct}  (paper={accounts.get('isPaper')})")
        print(
            f"  supportsCashQty={props.get('supportsCashQty')} "
            f"supportsFractions={props.get('supportsFractions')} "
            f"lite={props.get('liteUnderPro')}"
        )

        market = CpapiMarketData(client, acct or settings.ibkr_account_id)
        summary = await market.get_account_summary()
        print(
            f"\nBalance: US${summary.available_funds}  "
            f"(net liq US${summary.net_liquidation}, buying power US${summary.buying_power})"
        )

        quote = await market.get_quote("AAPL")
        if quote:
            print(f"AAPL quote: last={quote.last_price} bid={quote.bid} ask={quote.ask}")

        positions = await market.get_positions()
        print(f"Open positions: {len(positions)}")

        print("\n[OK] Connection healthy.")
        return 0
    finally:
        await client.aclose()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
