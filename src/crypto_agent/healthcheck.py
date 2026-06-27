"""Healthcheck for the crypto (CCXT) connection.

Confirms the API keys authenticate, then prints a readable report (exchange, mode,
quote-currency balance and a sample quote).

Usage: python -m crypto_agent.healthcheck
"""

from __future__ import annotations

import asyncio
import warnings

from .server.services import build_services

warnings.filterwarnings("ignore")

_SAMPLE_SYMBOL = "BTC"


async def _run() -> int:
    svc = build_services()
    settings = svc.settings
    print(f"Exchange: {settings.crypto_exchange}  mode={settings.crypto_trading_mode.value}")
    try:
        await svc.client.ensure_markets()
        info = await svc.account_info()
        print(f"Auth: authenticated=True  account_type={info.get('account_type')}")

        summary = await svc.market_data.get_account_summary()
        print(
            f"Balance: {summary.available_funds} {summary.currency} (free, quote currency)"
        )

        quote = await svc.market_data.get_quote(_SAMPLE_SYMBOL)
        if quote:
            print(
                f"{quote.symbol} quote: last={quote.last_price} "
                f"bid={quote.bid} ask={quote.ask}"
            )

        positions = await svc.market_data.get_positions()
        print(f"Open positions: {len(positions)}")

        print("\n[OK] Connection healthy.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\n[WARN] Could not complete the healthcheck: {exc}")
        print(
            "   Check CRYPTO_API_KEY / CRYPTO_API_SECRET and that the keys match the "
            f"selected mode ({settings.crypto_trading_mode.value})."
        )
        return 1
    finally:
        await svc.client.aclose()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
