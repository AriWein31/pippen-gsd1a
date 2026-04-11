"""Notification adapters for Week 4 alarm system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .engine import NotificationMessage, NotificationService, NotificationChannel


@dataclass
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
