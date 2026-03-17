from typing import Any
import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from telegram_api_server.core.config import get_settings
from telegram_api_server.core.metrics import webhook_delivery_total, webhook_timeout_total

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    def __init__(self) -> None:
        self.settings = get_settings()

    @retry(
        stop=stop_after_attempt(get_settings().webhook_retry_attempts + 1),
        wait=wait_fixed(0.4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def dispatch(
        self,
        webhook_url: str,
        payload: dict[str, Any],
        file_content: bytes | None = None,
        file_name: str | None = None,
    ) -> None:
        timeout = self.settings.webhook_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                if file_content:
                    data = {k: str(v) if v is not None else "" for k, v in payload.items()}
                    files = {"file": (file_name or "file.bin", file_content)}
                    response = await client.post(webhook_url, data=data, files=files)
                else:
                    response = await client.post(webhook_url, json=payload)
            except httpx.TimeoutException:
                webhook_timeout_total.inc()
                raise

            if response.status_code >= 500:
                webhook_delivery_total.labels(status="5xx").inc()
                response.raise_for_status()
            if response.status_code < 200 or response.status_code > 299:
                webhook_delivery_total.labels(status="non_2xx").inc()
                logger.warning("Webhook returned non-2xx", extra={"status_code": response.status_code})
                return
            webhook_delivery_total.labels(status="ok").inc()


webhook_dispatcher = WebhookDispatcher()
