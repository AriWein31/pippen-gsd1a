"""High-availability alarm daemon.

Runs a deterministic 60-second tick over active night alarms.
Includes heartbeat recording for watchdog monitoring.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .engine import CoverageAlarmEngine
from .watchdog import AlarmDaemonWatchdog

logger = logging.getLogger(__name__)


class AlarmDaemon:
    def __init__(
        self,
        engine: CoverageAlarmEngine,
        watchdog: Optional[AlarmDaemonWatchdog] = None,
        tick_seconds: int = 60,
    ):
        self.engine = engine
        self.watchdog = watchdog
        self.tick_seconds = tick_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._tick_count = 0

    async def run_once(self) -> dict:
        summary = await self.engine.tick()
        self._tick_count += 1
        
        # Record heartbeat if watchdog configured
        if self.watchdog:
            await self.watchdog.record_heartbeat(self._tick_count)
        
        logger.info(
            "alarm_tick tick=%s warnings=%s expired=%s alarmed=%s escalated=%s",
            self._tick_count,
            summary["warnings"],
            summary["expired"],
            summary["alarmed"],
            summary["escalated"],
        )
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
