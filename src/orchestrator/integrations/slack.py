import logging

import httpx

logger = logging.getLogger(__name__)


class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def notify(self, text: str) -> None:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(self.webhook_url, json={"text": text}, timeout=10)
        except httpx.HTTPError:
            logger.exception("Failed to send Slack notification")
