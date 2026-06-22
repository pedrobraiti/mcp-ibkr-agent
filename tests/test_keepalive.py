import json

import httpx
import respx

from ibkr_agent.keepalive import _notify_webhook


@respx.mock
def test_notify_webhook_posts_message():
    route = respx.post("https://hook.example/x").mock(return_value=httpx.Response(200))

    _notify_webhook("https://hook.example/x", "reauth please")

    assert route.called
    assert json.loads(route.calls.last.request.content) == {"text": "reauth please"}


@respx.mock
def test_notify_webhook_swallows_errors():
    respx.post("https://hook.example/x").mock(side_effect=httpx.ConnectError("down"))
    # Must not raise — a failed notification can't break the keep-alive loop.
    _notify_webhook("https://hook.example/x", "hi")
