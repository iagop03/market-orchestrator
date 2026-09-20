import logging

import httpx

logger = logging.getLogger(__name__)


class DiscoveryClient:
    """Client for market-discovery's HTTP API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def get_new_opportunities(self) -> list[dict]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/opportunities/new", timeout=15)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            logger.exception("Failed to fetch new opportunities from market-discovery")
            return []

    async def ack_opportunities(self, ids: list[int]) -> None:
        """Confirms durable receipt so market-discovery retires these claims for good.

        Best-effort: if this fails, the claim simply expires on market-discovery's side
        and the opportunity is redelivered later — safe, since callers dedupe on
        (niche_title, source) before storing.
        """
        if not ids:
            return
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/opportunities/ack", json={"ids": ids}, timeout=15)
                response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Failed to ack opportunities %s with market-discovery", ids)
