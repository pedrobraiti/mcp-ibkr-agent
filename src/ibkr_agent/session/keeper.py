"""IBKR session keep-alive + reauthentication alert.

The retail CPAPI has no OAuth: the gateway's brokerage session expires (without
``/tickle`` in ~6min, lasts at most ~24h, and the daily maintenance ~01:00 drops
it). This component keeps the session alive with ``/tickle`` and fires an alert
when it drops and needs a manual login in the browser — something no code can do
on its own for a retail account.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class SessionManager(Protocol):
    """Subset of the AuthPort that the keeper needs (``GatewayAuth`` satisfies it)."""

    async def status(self) -> dict: ...
    async def tickle(self) -> dict: ...
    async def ensure_session(self) -> None: ...


def _default_alert(reason: str) -> None:
    logger.error("[ALERT] Reauthentication required: %s", reason)


class SessionKeeper:
    """Keeps the session alive (tickle) and alerts when it drops.

    Does not try to log in via the browser (impossible for retail) — it only
    warns via ``on_alert``. When *connected* but without a brokerage session, it
    performs a lightweight recovery (``ensure_session``), which sometimes
    reconnects without a new 2FA.

    The alert is not repeated every cycle: it fires on the drop and only fires
    again every ``realert_every`` cycles while it stays down.
    """

    def __init__(
        self,
        session: SessionManager,
        *,
        interval_seconds: float = 60,
        on_alert: Callable[[str], None] = _default_alert,
        realert_every: int = 5,
    ):
        self._session = session
        self._interval = interval_seconds
        self._on_alert = on_alert
        self._realert_every = max(1, realert_every)
        self._alive: bool | None = None
        self._cycles_since_alert = 0

    async def run_once(self) -> bool:
        """Run one keep-alive cycle. Returns True if the session is alive."""
        try:
            status = await self._session.status()
        except Exception as exc:  # noqa: BLE001 - any failure = suspect session
            self._mark_down(f"failed to query status: {exc}")
            return False

        if status.get("authenticated") and status.get("connected"):
            try:
                await self._session.tickle()
            except Exception as exc:  # noqa: BLE001
                self._mark_down(f"tickle failed: {exc}")
                return False
            self._mark_up()
            return True

        if status.get("connected"):
            try:
                await self._session.ensure_session()
                self._mark_up()
                return True
            except Exception:  # noqa: BLE001 - lightweight recovery failed; fall through to alert
                pass

        self._mark_down(
            "session dropped — log in to the Client Portal Gateway "
            "(https://localhost:5000, with 2FA) to reauthenticate."
        )
        return False

    async def run(self, *, stop_event: asyncio.Event | None = None) -> None:
        """Keep-alive loop until ``stop_event``. Runs one cycle every ``interval_seconds``."""
        stop_event = stop_event or asyncio.Event()
        while not stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._interval)
            except TimeoutError:
                continue

    def _mark_up(self) -> None:
        if self._alive is False:
            logger.info("Session re-established.")
        self._alive = True
        self._cycles_since_alert = 0

    def _mark_down(self, reason: str) -> None:
        first_drop = self._alive is not False
        if first_drop or self._cycles_since_alert >= self._realert_every:
            self._on_alert(reason)
            self._cycles_since_alert = 0
        else:
            self._cycles_since_alert += 1
        self._alive = False
