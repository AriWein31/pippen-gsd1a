"""FastAPI entry point — wires together all routers and the notification pipeline."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .events.bus import get_event_bus, EventTypes
from .events.store import EventStore
from .courses.engine import CoverageCourseEngine
from .alarms.engine import CoverageAlarmEngine
from .alarms.notifiers import (
    InMemoryNotificationService,
    FanoutNotificationService,
    AsyncTelegramNotificationService,
)
from .intelligence.alerts import AlertRouter
from .api.patients import create_patients_router
from .api.entries import create_entries_router

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notification dispatcher — consumes ALARM_TRIGGERED, sends Telegram
# ---------------------------------------------------------------------------

class NotificationDispatcher:
    """
    Subscribes to ALARM_TRIGGERED on the event bus, looks up caregivers,
    formats messages, and sends via AsyncTelegramNotificationService.

    Respects patient notification_quiet_hours (critical severity bypasses).
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        notification_service: AsyncTelegramNotificationService,
    ):
        self.pool = pool
        self._notifier = notification_service
        self._bus = get_event_bus()
        self._stopping = False

    async def start(self) -> None:
        self._bus.subscribe(EventTypes.ALARM_TRIGGERED, self._on_alarm_triggered)
        logger.info("NotificationDispatcher started")

    async def stop(self) -> None:
        self._stopping = True
        self._bus.unsubscribe(EventTypes.ALARM_TRIGGERED, self._on_alarm_triggered)
        logger.info("NotificationDispatcher stopped")

    async def _on_alarm_triggered(self, event: dict) -> None:
        """Handle ALARM_TRIGGERED events from the event bus."""
        if self._stopping:
            return
        data = event.get("data", event)
        try:
            await self._dispatch(data)
        except Exception as exc:
            logger.error("NotificationDispatcher failed to dispatch: %s", exc)

    async def _dispatch(self, data: dict) -> None:
        patient_id = data["patient_id"]
        alert_severity = data.get("alert_severity", "medium")

        # Check quiet hours (critical bypasses)
        if alert_severity != "critical":
            if await self._is_in_quiet_hours(patient_id):
                logger.info(
                    "NotificationDispatcher: skipped %s alert for patient %s (quiet hours)",
                    alert_severity, patient_id,
                )
                return

        # Load caregivers with notification preferences
        caregivers = await self._get_notify_caregivers(patient_id, alert_severity)
        if not caregivers:
            logger.debug("No notify caregivers found for patient %s", patient_id)
            return

        from .alarms.engine import NotificationMessage, NotificationChannel, AlarmStatus

        # Map severity to AlarmStatus for the formatter
        status_map = {
            "low": AlarmStatus.WARNING_SENT,
            "medium": AlarmStatus.WARNING_SENT,
            "high": AlarmStatus.ALARMED,
            "critical": AlarmStatus.ESCALATED,
        }
        status = status_map.get(alert_severity, AlarmStatus.WARNING_SENT)

        message_text = (
            f"🚨 Pippen Alert [{alert_severity.upper()}]\n"
            f"{data.get('title', 'Alert')}\n"
            f"{data.get('description', '')}\n"
            f"Source: {data.get('source', 'intelligence')}"
        )

        for caregiver in caregivers:
            message = NotificationMessage(
                patient_id=patient_id,
                alarm_id=data.get("alert_id", ""),
                course_id="",
                status=status,
                channel=NotificationChannel.TELEGRAM,
                recipient=caregiver["telegram_id"],
                text=message_text,
                metadata={
                    "caregiver_id": caregiver["id"],
                    "alert_severity": alert_severity,
                },
            )
            await self._notifier.send(message)

        logger.info(
            "NotificationDispatcher: sent %d Telegram messages for patient %s [%s]",
            len(caregivers), patient_id, alert_severity,
        )

    async def _get_notify_caregivers(
        self,
        patient_id: str,
        alert_severity: str,
    ) -> list[dict]:
        """Load caregivers who want notifications for this severity level."""
        column_map = {
            "low": "notify_warning",
            "medium": "notify_warning",
            "high": "notify_alarm",
            "critical": "notify_escalation",
        }
        column = column_map.get(alert_severity, "notify_warning")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, name, telegram_id
                FROM caregivers
                WHERE patient_id = $1 AND {column} = TRUE AND telegram_id IS NOT NULL
                ORDER BY escalation_order ASC
                """,
                patient_id,
            )
        return [dict(row) for row in rows]

    async def _is_in_quiet_hours(self, patient_id: str) -> bool:
        """Check if current time falls within patient's quiet hours."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT preferences FROM patients WHERE id = $1",
                patient_id,
            )

        if not row:
            return False

        preferences = row["preferences"]
        if isinstance(preferences, str):
            import json
            preferences = json.loads(preferences)

        quiet_hours = preferences.get("notification_quiet_hours") if isinstance(preferences, dict) else None
        if not quiet_hours:
            return False

        start_str = quiet_hours.get("start", "22:00")
        end_str = quiet_hours.get("end", "07:00")

        try:
            start_hour, start_min = map(int, start_str.split(":"))
            end_hour, end_min = map(int, end_str.split(":"))
        except (ValueError, AttributeError):
            return False

        now = datetime.now(timezone.utc)
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        if start_minutes <= end_minutes:
            # Same day range (e.g., 09:00-17:00)
            in_quiet = start_minutes <= current_minutes <= end_minutes
        else:
            # Overnight range (e.g., 22:00-07:00)
            in_quiet = current_minutes >= start_minutes or current_minutes <= end_minutes

        return in_quiet


# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Set up DB pool and start background services; tear down on shutdown."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    # Create connection pool
    pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    app.state.db_pool = pool
    logger.info("Database pool created")

    # Instantiate AlertRouter and start it
    alert_router = AlertRouter(pool)
    await alert_router.start()
    app.state.alert_router = alert_router
    logger.info("AlertRouter started")

    # Instantiate notification dispatcher
    telegram_service = AsyncTelegramNotificationService()
    dispatcher = NotificationDispatcher(pool, telegram_service)
    await dispatcher.start()
    app.state.notification_dispatcher = dispatcher
    logger.info("NotificationDispatcher started")

    # Wire patients and entries routers
    patients_router = create_patients_router(pool, alert_router)
    entries_router = create_entries_router(pool)
    app.include_router(patients_router)
    app.include_router(entries_router)
    logger.info("Routers registered")

    yield

    # Shutdown
    await dispatcher.stop()
    await alert_router.stop()
    app.state.db_pool.close()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Pippen Backend",
    lifespan=lifespan,
)

# CORS for mobile (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
