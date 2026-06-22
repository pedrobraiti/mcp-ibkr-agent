"""Authentication via Client Portal Gateway (the only path available for retail).

Flow: the user logs in manually in the browser (`https://localhost:5000`, with 2FA).
From here we take care of checking the status, reinitializing the brokerage session
when ``connected`` but not ``authenticated``, and keeping the keep-alive via ``/tickle``.
"""

from __future__ import annotations

from ..cpapi.client import CpapiClient, CpapiError


class GatewayAuth:
    """Implements ``AuthPort`` on top of the Client Portal Gateway."""

    def __init__(self, client: CpapiClient):
        self._client = client

    async def status(self) -> dict:
        data = await self._client.post("/iserver/auth/status")
        return data if isinstance(data, dict) else {}

    async def is_authenticated(self) -> bool:
        return bool((await self.status()).get("authenticated"))

    async def ensure_session(self) -> None:
        status = await self.status()
        if status.get("authenticated"):
            await self._confirm_accounts()
            return

        if status.get("connected"):
            # Connected to the gateway but without an active brokerage session: (re)initialize.
            await self._client.post(
                "/iserver/auth/ssodh/init", json={"publish": True, "compete": True}
            )
            await self.tickle()
            if await self.is_authenticated():
                await self._confirm_accounts()
                return

        raise CpapiError(
            "Session not authenticated. Log in to the Client Portal Gateway at "
            "https://localhost:5000 (with 2FA) and try again."
        )

    async def tickle(self) -> dict:
        """Session keep-alive. Should be called every ~60s. Returns the /tickle payload."""
        data = await self._client.post("/tickle")
        return data if isinstance(data, dict) else {}

    async def _confirm_accounts(self) -> None:
        """`GET /iserver/accounts` is a prerequisite before any order operation."""
        await self._client.get("/iserver/accounts")
