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

    async def account_info(self) -> dict:
        """Ground truth about the logged-in account, straight from IBKR.

        ``/iserver/accounts`` reports ``isPaper`` — the only reliable signal of
        whether real money is at stake. The configured ``IBKR_TRADING_MODE`` is just
        a label and can disagree with the account the gateway is actually logged
        into, so never trust it for this. Returns ``account_id``, ``is_paper`` and a
        human ``account_type`` ("LIVE"/"PAPER"). Falls back to the account-id prefix
        (paper ids start with ``DU``) only if the API omits ``isPaper``.
        """
        data = await self._client.get("/iserver/accounts")
        data = data if isinstance(data, dict) else {}
        account_id = data.get("selectedAccount")
        is_paper = data.get("isPaper")
        if is_paper is None and isinstance(account_id, str) and account_id:
            is_paper = not account_id.upper().startswith("U")
        return {
            "account_id": account_id,
            "is_paper": is_paper,
            "account_type": None if is_paper is None else ("PAPER" if is_paper else "LIVE"),
        }

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
