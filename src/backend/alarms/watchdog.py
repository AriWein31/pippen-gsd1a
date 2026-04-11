"""Alarm daemon watchdog — monitors daemon health and alerts if silent.

Critical for safety: if the alarm daemon crashes, night safety fails silently.
This watchdog provides external monitoring and automatic restart capability.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class DaemonHealth:
    """Health status of the alarm daemon."""
    last_heartbeat: datetime
    tick_count: int
    is_healthy: bool
    missed_ticks: int


class AlarmDaemonWatchdog:
    """Monitors alarm daemon health via heartbeat table.
    
    Usage:
        watchdog = AlarmDaemonWatchdog(pool, check_interval_seconds=60)
        
        # In daemon:
        await watchdog.record_heartbeat()
        
        # In monitor:
        health = await watchdog.check_health()
        if not health.is_healthy:
            await watchdog.restart_daemon()
    """
    
    def __init__(
        self,
        pool: asyncpg.Pool,
        check_interval_seconds: int = 60,
        max_missed_ticks: int = 2,
    ):
        self.pool = pool
        self.check_interval_seconds = check_interval_seconds
        self.max_missed_ticks = max_missed_ticks
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self) -> None:
        """Create heartbeat table if not exists."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daemon_heartbeat (
                    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    tick_count INTEGER NOT NULL DEFAULT 0,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            # Insert initial row if not exists
            await conn.execute(
                """
                INSERT INTO daemon_heartbeat (id, last_heartbeat, tick_count)
                VALUES (1, NOW(), 0)
                ON CONFLICT (id) DO NOTHING
                """
            )
    
    async def record_heartbeat(self, tick_count: int) -> None:
        """Record daemon heartbeat. Call this from daemon's run loop."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE daemon_heartbeat
                SET last_heartbeat = NOW(),
                    tick_count = $1,
                    updated_at = NOW()
                WHERE id = 1
                """,
                tick_count,
            )
    
    async def check_health(self) -> DaemonHealth:
        """Check if daemon is healthy based on last heartbeat."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT last_heartbeat, tick_count
                FROM daemon_heartbeat
                WHERE id = 1
                """
            )
        
        if not row:
            return DaemonHealth(
                last_heartbeat=datetime.min.replace(tzinfo=timezone.utc),
                tick_count=0,
                is_healthy=False,
                missed_ticks=999,
            )
        
        last_heartbeat = row["last_heartbeat"]
        tick_count = row["tick_count"]
        
        # Calculate missed ticks
        seconds_since_heartbeat = (datetime.now(timezone.utc) - last_heartbeat).total_seconds()
        missed_ticks = int(seconds_since_heartbeat / self.check_interval_seconds)
        
        is_healthy = missed_ticks <= self.max_missed_ticks
        
        if not is_healthy:
            logger.error(
                "ALARM DAEMON UNHEALTHY: last_heartbeat=%s, missed_ticks=%d",
                last_heartbeat,
                missed_ticks,
            )
        
        return DaemonHealth(
            last_heartbeat=last_heartbeat,
            tick_count=tick_count,
            is_healthy=is_healthy,
            missed_ticks=missed_ticks,
        )
    
    async def monitor_loop(self, on_unhealthy: Optional[callable] = None) -> None:
        """Run continuous health monitoring."""
        self._running = True
        while self._running:
            health = await self.check_health()
            if not health.is_healthy:
                logger.critical("ALARM DAEMON FAILURE DETECTED")
                if on_unhealthy:
                    await on_unhealthy(health)
            await asyncio.sleep(self.check_interval_seconds)
    
    def start_monitoring(self, on_unhealthy: Optional[callable] = None) -> asyncio.Task:
        """Start watchdog monitoring in background."""
        if self._monitor_task and not self._monitor_task.done():
            return self._monitor_task
        self._monitor_task = asyncio.create_task(self.monitor_loop(on_unhealthy))
        return self._monitor_task
    
    async def stop(self) -> None:
        """Stop watchdog monitoring."""
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
