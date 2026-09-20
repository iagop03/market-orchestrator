import httpx

from orchestrator.integrations.discovery_client import DiscoveryClient


async def _instant_sleep(_seconds):
    return None


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


class FakeAsyncClient:
    """Stands in for httpx.AsyncClient; raise_exc may be an exception or a list of
    exceptions/None consumed one per call, to simulate "fails N times then succeeds"."""

    def __init__(self, response=None, raise_exc=None):
        self._response = response
        self._raise_exc = raise_exc
        self.posted = None
        self.call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def _next_exc(self):
        if isinstance(self._raise_exc, list):
            return self._raise_exc[self.call_count] if self.call_count < len(self._raise_exc) else None
        return self._raise_exc

    async def get(self, url, timeout=None):
        exc = self._next_exc()
        self.call_count += 1
        if exc:
            raise exc
        return self._response

    async def post(self, url, json=None, timeout=None):
        exc = self._next_exc()
        self.call_count += 1
        if exc:
            raise exc
        self.posted = (url, json)
        return self._response


async def test_get_new_opportunities_returns_parsed_json(monkeypatch):
    fake_response = FakeResponse([{"niche_title": "x", "source": "reddit"}])
    monkeypatch.setattr(
        "orchestrator.integrations.discovery_client.httpx.AsyncClient",
        lambda: FakeAsyncClient(response=fake_response),
    )

    client = DiscoveryClient("http://discovery.test")
    result = await client.get_new_opportunities()

    assert result == [{"niche_title": "x", "source": "reddit"}]


async def test_get_new_opportunities_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("orchestrator.retry.asyncio.sleep", _instant_sleep)
    fake_response = FakeResponse([{"niche_title": "x", "source": "reddit"}])
    fake_client = FakeAsyncClient(raise_exc=[httpx.ConnectError("boom"), None], response=fake_response)
    monkeypatch.setattr(
        "orchestrator.integrations.discovery_client.httpx.AsyncClient",
        lambda: fake_client,
    )

    client = DiscoveryClient("http://discovery.test")
    result = await client.get_new_opportunities()

    assert result == [{"niche_title": "x", "source": "reddit"}]
    assert fake_client.call_count == 2


async def test_get_new_opportunities_returns_empty_list_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("orchestrator.retry.asyncio.sleep", _instant_sleep)
    fake_client = FakeAsyncClient(raise_exc=httpx.ConnectError("boom"))
    monkeypatch.setattr(
        "orchestrator.integrations.discovery_client.httpx.AsyncClient",
        lambda: fake_client,
    )

    client = DiscoveryClient("http://discovery.test")
    result = await client.get_new_opportunities()

    assert result == []
    assert fake_client.call_count == 3  # default retry_async attempts


def test_base_url_strips_trailing_slash():
    client = DiscoveryClient("http://discovery.test/")
    assert client.base_url == "http://discovery.test"


async def test_ack_opportunities_posts_ids(monkeypatch):
    fake_response = FakeResponse({"acked": 2})
    fake_client = FakeAsyncClient(response=fake_response)
    monkeypatch.setattr(
        "orchestrator.integrations.discovery_client.httpx.AsyncClient",
        lambda: fake_client,
    )

    client = DiscoveryClient("http://discovery.test")
    await client.ack_opportunities([1, 2])

    assert fake_client.posted == ("http://discovery.test/opportunities/ack", {"ids": [1, 2]})


async def test_ack_opportunities_is_noop_for_empty_list(monkeypatch):
    def boom():
        raise AssertionError("should not be called for an empty id list")

    monkeypatch.setattr("orchestrator.integrations.discovery_client.httpx.AsyncClient", boom)

    client = DiscoveryClient("http://discovery.test")
    await client.ack_opportunities([])  # must not raise, must not touch httpx


async def test_ack_opportunities_swallows_http_errors_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("orchestrator.retry.asyncio.sleep", _instant_sleep)
    fake_client = FakeAsyncClient(raise_exc=httpx.ConnectError("boom"))
    monkeypatch.setattr(
        "orchestrator.integrations.discovery_client.httpx.AsyncClient",
        lambda: fake_client,
    )

    client = DiscoveryClient("http://discovery.test")
    await client.ack_opportunities([1])  # must not raise

    assert fake_client.call_count == 3
