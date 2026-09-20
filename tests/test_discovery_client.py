import httpx

from orchestrator.integrations.discovery_client import DiscoveryClient


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
    def __init__(self, response=None, raise_exc=None):
        self._response = response
        self._raise_exc = raise_exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, timeout=None):
        if self._raise_exc:
            raise self._raise_exc
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


async def test_get_new_opportunities_returns_empty_list_on_http_error(monkeypatch):
    monkeypatch.setattr(
        "orchestrator.integrations.discovery_client.httpx.AsyncClient",
        lambda: FakeAsyncClient(raise_exc=httpx.ConnectError("boom")),
    )

    client = DiscoveryClient("http://discovery.test")
    result = await client.get_new_opportunities()

    assert result == []


def test_base_url_strips_trailing_slash():
    client = DiscoveryClient("http://discovery.test/")
    assert client.base_url == "http://discovery.test"
