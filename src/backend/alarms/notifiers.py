"""Notification adapters for Week 4 alarm system."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from .engine import NotificationMessage, NotificationService, NotificationChannel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory services (existing)
# ---------------------------------------------------------------------------

class InMemoryNotificationService(NotificationService):
    sent: List[NotificationMessage] = field(default_factory=list)

    async def send(self, message: NotificationMessage) -> None:
        self.sent.append(message)


class FanoutNotificationService(NotificationService):
    def __init__(self, services: list[NotificationService]):
        self.services = services

    async def send(self, message: NotificationMessage) -> None:
        for service in self.services:
            await service.send(message)


class NoopNotificationService(NotificationService):
    async def send(self, message: NotificationMessage) -> None:
        return None


class TelegramNotificationFormatter:
    @staticmethod
    def format(message: NotificationMessage) -> str:
        prefix = {
            NotificationChannel.TELEGRAM: "🚨",
            NotificationChannel.PUSH: "🔔",
        }[message.channel]
        return f"{prefix} Pippen {message.status.value.replace('_', ' ')}: {message.text}"


# ---------------------------------------------------------------------------
# AsyncTelegramNotificationService — sends to Telegram API
# ---------------------------------------------------------------------------

class AsyncTelegramNotificationService(NotificationService):
    """
    Sends NotificationMessage to Telegram using the Bot API.

    Parses `message.recipient` as a Telegram chat ID.
    Handles 429 rate limits with exponential backoff (max 3 retries).
    Logs and continues gracefully if BOT_TOKEN is missing or invalid.
    """

    BASE_URL = "https://api.telegram.org/bot{bot_token}/sendMessage"

    def __init__(self, bot_token: Optional[str] = None, max_retries: int = 3):
        self._bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create and reuse a single httpx client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def send(self, message: NotificationMessage) -> None:
        if not self._bot_token:
            logger.warning(
                "AsyncTelegramNotificationService: TELEGRAM_BOT_TOKEN not set, skipping send"
            )
            return

        if message.channel != NotificationChannel.TELEGRAM:
            logger.debug(
                "AsyncTelegramNotificationService: non-Telegram message skipped (channel=%s)",
                message.channel,
            )
            return

        text = TelegramNotificationFormatter.format(message)
        chat_id = message.recipient

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        success = False
        last_error: Optional[str] = None

        for attempt in range(self._max_retries):
            try:
                client = await self._get_client()
                response = await client.post(
                    self.BASE_URL.format(bot_token=self._bot_token),
                    json=payload,
                )

                if response.status_code == 200:
                    success = True
                    logger.info(
                        "Telegram message sent to %s: %s",
                        chat_id,
                        text[:50],
                    )
                elif response.status_code == 429:
                    # Rate limited — retry with backoff
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    wait_seconds = retry_after * (2 ** attempt)
                    logger.warning(
                        "Telegram rate limited (429), attempt %d/%d, waiting %ds",
                        attempt + 1, self._max_retries, wait_seconds,
                    )
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(wait_seconds)
                    else:
                        last_error = f"Rate limited after {self._max_retries} retries"
                elif response.status_code == 401 or response.status_code == 403:
                    last_error = f"Invalid token ({response.status_code})"
                    logger.error(
                        "Telegram bot token invalid (%d): %s",
                        response.status_code,
                        response.text[:100],
                    )
                    break  # Don't retry on auth errors
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    logger.warning(
                        "Telegram API error (attempt %d/%d): %s",
                        attempt + 1, self._max_retries, last_error,
                    )
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))

                if success:
                    break

            except httpx.TimeoutException:
                last_error = "Timeout"
                logger.warning(
                    "Telegram request timeout (attempt %d/%d)",
                    attempt + 1, self._max_retries,
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
            except Exception as exc:
                last_error = str(exc)
                logger.error(
                    "Telegram send failed (attempt %d/%d): %s",
                    attempt + 1, self._max_retries, exc,
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))

        if not success:
            logger.error(
                "AsyncTelegramNotificationService: all %d attempts failed for chat %s: %s",
                self._max_retries, chat_id, last_error,
            )

    async def close(self) -> None:
        """Close the shared httpx client. Call on app shutdown."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
