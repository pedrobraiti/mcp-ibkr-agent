"""Runnable: mantém a sessão da IBKR viva e alerta quando ela cair.

    python -m ibkr_agent.keepalive      # ou: ibkr-keepalive

Requer o Client Portal Gateway rodando e logado. Roda até Ctrl+C. Rode-o ao lado
do uso manual ou de jobs agendados para manter a brokerage session aquecida.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from .config import get_settings
from .server.services import build_services
from .session import SessionKeeper

logger = logging.getLogger("ibkr_agent.keepalive")


def _alert(reason: str) -> None:
    logger.error("[ALERTA] Reautenticacao necessaria: %s", reason)
    try:
        sys.stderr.write("\a")  # bip do terminal para chamar atenção
        sys.stderr.flush()
    except Exception:  # noqa: BLE001
        pass


async def _run() -> None:
    settings = get_settings()
    services = build_services(settings)
    keeper = SessionKeeper(
        services.auth,
        interval_seconds=settings.tickle_interval_seconds,
        on_alert=_alert,
    )
    logger.info(
        "Keep-alive iniciado (tickle a cada %ss). Ctrl+C para sair.",
        settings.tickle_interval_seconds,
    )
    try:
        await keeper.run()
    finally:
        await services.client.aclose()


def main() -> None:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Keep-alive encerrado.")


if __name__ == "__main__":
    main()
