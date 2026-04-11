"""High-availability alarm daemon.

Runs a deterministic 60-second tick over active night alarms.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .engine import CoverageAlarmEngine

logger = logging.getLogger(__name__)


class AlarmDaemon:
    def __init__(self, engine: CoverageAlarmEngine, tick_seconds: int = 60):
        self.engine = engine
        self.tick_seconds = tick_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def run_once(self) -> dict:
        summary = await self.engine.tick()
        logger.info("alarm_tick warnings=%s expired=%s alarmed=%s escalated=%s", summary["warnings"], summary["expired"], summary["alarmed"], summary["escalated"])
        return summary

    async def run_forever(self) -> None:
        self._running = True
        while self._running:
            await self.run_once()
            await asyncio.sleep(self.tick_seconds)

    def start(self) -> asyncio.Task:
        if self._task and not self._task.done():
            return self._task
        self._task = asyncio.create_task(self.run_forever())
        return self._task

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
