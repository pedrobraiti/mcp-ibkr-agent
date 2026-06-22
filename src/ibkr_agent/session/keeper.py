"""Keep-alive da sessão da IBKR + alerta de reautenticação.

A CPAPI de varejo não tem OAuth: a brokerage session do gateway expira (sem
``/tickle`` em ~6min, dura no máx ~24h, e a manutenção diária ~01:00 derruba).
Este componente mantém a sessão viva com ``/tickle`` e dispara um alerta quando
ela cai e precisa de login manual no navegador — coisa que nenhum código faz
sozinho para conta de varejo.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class SessionManager(Protocol):
    """Subconjunto do AuthPort que o keeper precisa (o ``GatewayAuth`` satisfaz)."""

    async def status(self) -> dict: ...
    async def tickle(self) -> dict: ...
    async def ensure_session(self) -> None: ...


def _default_alert(reason: str) -> None:
    logger.error("[ALERTA] Reautenticacao necessaria: %s", reason)


class SessionKeeper:
    """Mantém a sessão viva (tickle) e alerta quando ela cai.

    Não tenta logar no navegador (impossível p/ varejo) — apenas avisa via
    ``on_alert``. Quando está *connected* mas sem brokerage session, faz uma
    recuperação leve (``ensure_session``), que às vezes religa sem novo 2FA.

    O alerta não é repetido a cada ciclo: dispara na queda e só volta a disparar
    a cada ``realert_every`` ciclos enquanto seguir caída.
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
        """Executa um ciclo de keep-alive. Retorna True se a sessão está viva."""
        try:
            status = await self._session.status()
        except Exception as exc:  # noqa: BLE001 - qualquer falha = sessão suspeita
            self._mark_down(f"falha ao consultar status: {exc}")
            return False

        if status.get("authenticated") and status.get("connected"):
            try:
                await self._session.tickle()
            except Exception as exc:  # noqa: BLE001
                self._mark_down(f"falha no tickle: {exc}")
                return False
            self._mark_up()
            return True

        if status.get("connected"):
            try:
                await self._session.ensure_session()
                self._mark_up()
                return True
            except Exception:  # noqa: BLE001 - recuperação leve falhou; cai no alerta
                pass

        self._mark_down(
            "sessao caiu — faça login no Client Portal Gateway "
            "(https://localhost:5000, com 2FA) para reautenticar."
        )
        return False

    async def run(self, *, stop_event: asyncio.Event | None = None) -> None:
        """Loop de keep-alive até ``stop_event``. Faz um ciclo a cada ``interval_seconds``."""
        stop_event = stop_event or asyncio.Event()
        while not stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._interval)
            except TimeoutError:
                continue

    def _mark_up(self) -> None:
        if self._alive is False:
            logger.info("Sessao restabelecida.")
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
