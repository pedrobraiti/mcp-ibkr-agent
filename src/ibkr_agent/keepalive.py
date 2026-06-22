"""Runnable: keeps the IBKR session alive and alerts when it drops.

    python -m ibkr_agent.keepalive      # or: ibkr-keepalive

Requires the Client Portal Gateway running and logged in. Runs until Ctrl+C. Run
it alongside manual use or scheduled jobs to keep the brokerage session warm.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import httpx

from .config import get_settings
from .server.services import build_services
from .session import SessionKeeper

logger = logging.getLogger("ibkr_agent.keepalive")


def _notify_webhook(url: str, message: str) -> None:
    """POST a one-way notification (no account data). Best-effort; never raises."""
    try:
        httpx.post(url, json={"text": message}, timeout=5)
    except Exception:  # noqa: BLE001
        logger.warning("Reauth webhook POST failed.")


def _alert(reason: str) -> None:
    logger.error("[ALERT] Reauthentication required: %s", reason)
    try:
        sys.stderr.write("\a")  # terminal bell to grab attention
        sys.stderr.flush()
    except Exception:  # noqa: BLE001
        pass
    url = get_settings().reauth_webhook_url
    if url:
        _notify_webhook(url, f"Valet: reauthentication required — {reason}")


async def _run() -> None:
    settings = get_settings()
    services = build_services(settings)
    keeper = SessionKeeper(
        services.auth,
        interval_seconds=settings.tickle_interval_seconds,
        on_alert=_alert,
    )
    logger.info(
        "Keep-alive started (tickle every %ss). Ctrl+C to exit.",
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
        logger.info("Keep-alive stopped.")


if __name__ == "__main__":
    main()
