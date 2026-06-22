import asyncio

from ibkr_agent.session import SessionKeeper

AUTHED = {"authenticated": True, "connected": True}
CONNECTED_NOT_AUTHED = {"authenticated": False, "connected": True}
DEAD = {"authenticated": False, "connected": False}


class FakeSession:
    def __init__(self, statuses, *, ensure_ok=False):
        self._statuses = list(statuses)
        self._ensure_ok = ensure_ok
        self.tickles = 0
        self.ensure_calls = 0

    async def status(self) -> dict:
        return self._statuses.pop(0) if self._statuses else DEAD

    async def tickle(self) -> dict:
        self.tickles += 1
        return {}

    async def ensure_session(self) -> None:
        self.ensure_calls += 1
        if not self._ensure_ok:
            raise RuntimeError("no brokerage session")


async def test_tickles_when_authenticated():
    alerts: list[str] = []
    session = FakeSession([AUTHED])
    keeper = SessionKeeper(session, interval_seconds=0, on_alert=alerts.append)

    alive = await keeper.run_once()

    assert alive is True
    assert session.tickles == 1
    assert alerts == []


async def test_alerts_when_session_dead():
    alerts: list[str] = []
    session = FakeSession([DEAD])
    keeper = SessionKeeper(session, interval_seconds=0, on_alert=alerts.append)

    alive = await keeper.run_once()

    assert alive is False
    assert session.tickles == 0
    assert len(alerts) == 1
    assert "reauthenticate" in alerts[0].lower()


async def test_recovers_when_connected_but_not_authenticated():
    alerts: list[str] = []
    session = FakeSession([CONNECTED_NOT_AUTHED], ensure_ok=True)
    keeper = SessionKeeper(session, interval_seconds=0, on_alert=alerts.append)

    alive = await keeper.run_once()

    assert alive is True
    assert session.ensure_calls == 1
    assert alerts == []


async def test_alert_is_not_spammed_every_cycle():
    alerts: list[str] = []
    session = FakeSession([DEAD, DEAD, DEAD], ensure_ok=False)
    keeper = SessionKeeper(session, interval_seconds=0, on_alert=alerts.append, realert_every=5)

    for _ in range(3):
        await keeper.run_once()

    # Alert only on the first drop; it does not repeat in the following cycles within the window.
    assert len(alerts) == 1


async def test_run_stops_on_event():
    session = FakeSession([AUTHED])
    keeper = SessionKeeper(session, interval_seconds=0, on_alert=lambda _r: None)
    stop = asyncio.Event()
    stop.set()

    await asyncio.wait_for(keeper.run(stop_event=stop), timeout=1)

    assert session.tickles == 0  # stopped before any cycle
