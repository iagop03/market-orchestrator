import httpx

from orchestrator.integrations.slack import SlackNotifier


class FakeAsyncClient:
    def __init__(self, raise_exc=None):
        self._raise_exc = raise_exc
        self.posted = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, timeout=None):
        if self._raise_exc:
            raise self._raise_exc
        self.posted = (url, json)


async def test_notify_posts_text_to_webhook(monkeypatch):
    fake_client = FakeAsyncClient()
    monkeypatch.setattr(
        "orchestrator.integrations.slack.httpx.AsyncClient",
        lambda: fake_client,
    )

    notifier = SlackNotifier("https://hooks.slack.test/webhook")
    await notifier.notify(":rocket: Shipped: thing")

    assert fake_client.posted == ("https://hooks.slack.test/webhook", {"text": ":rocket: Shipped: thing"})


async def test_notify_swallows_http_errors(monkeypatch):
    fake_client = FakeAsyncClient(raise_exc=httpx.ConnectError("boom"))
    monkeypatch.setattr(
        "orchestrator.integrations.slack.httpx.AsyncClient",
        lambda: fake_client,
    )

    notifier = SlackNotifier("https://hooks.slack.test/webhook")
    await notifier.notify("should not raise")  # must not propagate
