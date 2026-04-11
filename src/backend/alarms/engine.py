"""Safety-critical night alarm engine.

Deterministic rules only. No ML, no heuristics.

State machine:
    active -> warning_sent -> expired -> alarmed -> escalated -> resolved
                       \-------------------------------> resolved

Core rules:
- Warning fires WARNING_LEAD_MINUTES before course end.
- Expired fires at course expected_end_at.
- Alarm fires ALARM_DELAY_MINUTES after expiry if unresolved.
- Escalation fires ESCALATION_DELAY_MINUTES after alarm if unresolved.
- Any new qualifying patient event resolves the active alarm state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Protocol, Sequence

import asyncpg

from ..events.bus import get_event_bus, EventTypes

WARNING_LEAD_MINUTES = 15
ALARM_DELAY_MINUTES = 0
ESCALATION_DELAY_MINUTES = 5
QUALIFYING_RESOLUTION_EVENTS = {"cornstarch_dose", "meal", "alarm_acknowledged"}


class AlarmStatus(str, Enum):
    ACTIVE = "active"
    WARNING_SENT = "warning_sent"
    EXPIRED = "expired"
    ALARMED = "alarmed"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


class NotificationChannel(str, Enum):
    TELEGRAM = "telegram"
    PUSH = "push"


class Clock(Protocol):
    def now(self) -> datetime:
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class NotificationMessage:
    patient_id: str
    alarm_id: str
    course_id: str
    status: AlarmStatus
    channel: NotificationChannel
    recipient: str
    text: str
    metadata: dict


class NotificationService(Protocol):
    async def send(self, message: NotificationMessage) -> None:
        ...


class AlarmEngineError(Exception):
    pass


class CoverageAlarmEngine:
    def __init__(
        self,
        pool: asyncpg.Pool,
        notification_service: NotificationService,
        clock: Optional[Clock] = None,
    ):
        self.pool = pool
        self.notification_service = notification_service
        self.clock = clock or SystemClock()

    async def ensure_alarm_for_course(self, course_id: str) -> str:
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow(
                """
                SELECT id FROM night_alarm_state WHERE course_id = $1
                """,
                course_id,
            )
            if existing:
                return str(existing["id"])

            course = await conn.fetchrow(
                """
                SELECT id, patient_id, expected_end_at, status
                FROM coverage_courses
                WHERE id = $1
                """,
                course_id,
            )
            if not course:
                raise AlarmEngineError(f"Course {course_id} not found")

            alarm_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO night_alarm_state (
                    id, patient_id, course_id, status, course_expected_end, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $6)
                """,
                alarm_id,
                str(course["patient_id"]),
                str(course["id"]),
                AlarmStatus.ACTIVE.value,
                course["expected_end_at"],
                self.clock.now(),
            )
            return alarm_id

    async def tick(self, now: Optional[datetime] = None) -> dict:
        now = now or self.clock.now()
        summary = {"warnings": 0, "expired": 0, "alarmed": 0, "escalated": 0}

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT nas.id, nas.patient_id, nas.course_id, nas.status,
                       nas.course_expected_end, nas.warning_sent_at,
                       nas.expired_at, nas.alarmed_at, nas.escalated_at,
                       cc.trigger_type, cc.is_bedtime_dose
                FROM night_alarm_state nas
                JOIN coverage_courses cc ON cc.id = nas.course_id
                WHERE nas.status IN ('active', 'warning_sent', 'expired', 'alarmed')
                ORDER BY nas.course_expected_end ASC
                """
            )

        for row in rows:
            status = AlarmStatus(row["status"])
            expected_end = row["course_expected_end"]
            warning_at = expected_end - timedelta(minutes=WARNING_LEAD_MINUTES)
            alarm_at = expected_end + timedelta(minutes=ALARM_DELAY_MINUTES)
            escalate_at = alarm_at + timedelta(minutes=ESCALATION_DELAY_MINUTES)

            if status == AlarmStatus.ACTIVE and now >= warning_at:
                await self._transition_to_warning(str(row["id"]), str(row["patient_id"]), str(row["course_id"]), now)
                summary["warnings"] += 1
                status = AlarmStatus.WARNING_SENT

            if status == AlarmStatus.WARNING_SENT and now >= expected_end:
                await self._transition_to_expired(str(row["id"]), str(row["patient_id"]), str(row["course_id"]), now)
                summary["expired"] += 1
                status = AlarmStatus.EXPIRED

            if status == AlarmStatus.EXPIRED and now >= alarm_at:
                await self._transition_to_alarmed(str(row["id"]), str(row["patient_id"]), str(row["course_id"]), now)
                summary["alarmed"] += 1
                status = AlarmStatus.ALARMED

            if status == AlarmStatus.ALARMED and now >= escalate_at:
                await self._transition_to_escalated(str(row["id"]), str(row["patient_id"]), str(row["course_id"]), now)
                summary["escalated"] += 1

        return summary

    async def resolve_by_event(self, patient_id: str, event_type: str, event_id: Optional[str] = None) -> int:
        if event_type not in QUALIFYING_RESOLUTION_EVENTS:
            return 0

        now = self.clock.now()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id FROM night_alarm_state
                WHERE patient_id = $1 AND status IN ('active', 'warning_sent', 'expired', 'alarmed', 'escalated')
                """,
                patient_id,
            )
            resolved = 0
            for row in rows:
                await conn.execute(
                    """
                    UPDATE night_alarm_state
                    SET status = 'resolved', resolved_at = $2, resolution = $3,
                        last_patient_event_id = $4, updated_at = $2
                    WHERE id = $1
                    """,
                    str(row["id"]),
                    now,
                    "patient_logged" if event_type != "alarm_acknowledged" else "caregiver_checked",
                    event_id,
                )
                resolved += 1

        if resolved:
            await get_event_bus().publish(
                EventTypes.ALARM_ACKNOWLEDGED,
                {
                    "patient_id": patient_id,
                    "event_type": event_type,
                    "event_id": event_id,
                    "resolved_count": resolved,
                    "resolved_at": now.isoformat(),
                },
            )
        return resolved

    async def get_active_alarm(self, patient_id: str) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, patient_id, course_id, status, course_expected_end,
                       warning_sent_at, expired_at, alarmed_at, escalated_at,
                       resolved_at, resolution, created_at, updated_at
                FROM night_alarm_state
                WHERE patient_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                patient_id,
            )
        return dict(row) if row else None

    async def _transition_to_warning(self, alarm_id: str, patient_id: str, course_id: str, now: datetime) -> None:
        recipients = await self._load_recipients(patient_id, "notify_warning")
        await self._update_status(alarm_id, AlarmStatus.WARNING_SENT, now, "warning_sent_at", "warning_recipients", recipients)
        await self._notify_many(patient_id, alarm_id, course_id, AlarmStatus.WARNING_SENT, recipients, "Coverage warning: 15 minutes remaining.")
        await get_event_bus().publish(EventTypes.COVERAGE_COURSE_WARNING, {
            "alarm_id": alarm_id,
            "patient_id": patient_id,
            "course_id": course_id,
            "at": now.isoformat(),
        })

    async def _transition_to_expired(self, alarm_id: str, patient_id: str, course_id: str, now: datetime) -> None:
        await self._update_status(alarm_id, AlarmStatus.EXPIRED, now, "expired_at")
        await get_event_bus().publish(EventTypes.COVERAGE_COURSE_EXPIRED, {
            "alarm_id": alarm_id,
            "patient_id": patient_id,
            "course_id": course_id,
            "at": now.isoformat(),
        })

    async def _transition_to_alarmed(self, alarm_id: str, patient_id: str, course_id: str, now: datetime) -> None:
        recipients = await self._load_recipients(patient_id, "notify_alarm")
        await self._update_status(alarm_id, AlarmStatus.ALARMED, now, "alarmed_at", "alarm_recipients", recipients)
        await self._notify_many(patient_id, alarm_id, course_id, AlarmStatus.ALARMED, recipients, "Coverage expired. Immediate action required.")
        await get_event_bus().publish(EventTypes.ALARM_TRIGGERED, {
            "alarm_id": alarm_id,
            "patient_id": patient_id,
            "course_id": course_id,
            "at": now.isoformat(),
        })

    async def _transition_to_escalated(self, alarm_id: str, patient_id: str, course_id: str, now: datetime) -> None:
        recipients = await self._load_recipients(patient_id, "notify_escalation")
        await self._update_status(alarm_id, AlarmStatus.ESCALATED, now, "escalated_at", "escalation_recipients", recipients)
        await self._notify_many(patient_id, alarm_id, course_id, AlarmStatus.ESCALATED, recipients, "Coverage alarm escalated. Check patient now.")
        await get_event_bus().publish(EventTypes.ALARM_ESCALATED, {
            "alarm_id": alarm_id,
            "patient_id": patient_id,
            "course_id": course_id,
            "at": now.isoformat(),
        })

    async def _update_status(
        self,
        alarm_id: str,
        status: AlarmStatus,
        now: datetime,
        timestamp_column: str,
        recipients_column: Optional[str] = None,
        recipients: Optional[Sequence[dict]] = None,
    ) -> None:
        async with self.pool.acquire() as conn:
            if recipients_column:
                await conn.execute(
                    f"""
                    UPDATE night_alarm_state
                    SET status = $2, {timestamp_column} = $3, {recipients_column} = $4, updated_at = $3
                    WHERE id = $1
                    """,
                    alarm_id,
                    status.value,
                    now,
                    [recipient for recipient in recipients or []],
                )
            else:
                await conn.execute(
                    f"""
                    UPDATE night_alarm_state
                    SET status = $2, {timestamp_column} = $3, updated_at = $3
                    WHERE id = $1
                    """,
                    alarm_id,
                    status.value,
                    now,
                )

    async def _load_recipients(self, patient_id: str, preference_column: str) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, name, telegram_id, escalation_order
                FROM caregivers
                WHERE patient_id = $1 AND {preference_column} = TRUE
                ORDER BY escalation_order ASC, created_at ASC
                """,
                patient_id,
            )
        recipients = []
        for row in rows:
            if row["telegram_id"]:
                recipients.append({
                    "caregiver_id": str(row["id"]),
                    "name": row["name"],
                    "channel": NotificationChannel.TELEGRAM.value,
                    "recipient": row["telegram_id"],
                })
            recipients.append({
                "caregiver_id": str(row["id"]),
                "name": row["name"],
                "channel": NotificationChannel.PUSH.value,
                "recipient": str(row["id"]),
            })
        return recipients

    async def _notify_many(
        self,
        patient_id: str,
        alarm_id: str,
        course_id: str,
        status: AlarmStatus,
        recipients: Sequence[dict],
        text: str,
    ) -> None:
        async with self.pool.acquire() as conn:
            for recipient in recipients:
                channel = NotificationChannel(recipient["channel"])
                message = NotificationMessage(
                    patient_id=patient_id,
                    alarm_id=alarm_id,
                    course_id=course_id,
                    status=status,
                    channel=channel,
                    recipient=recipient["recipient"],
                    text=text,
                    metadata={"caregiver_id": recipient["caregiver_id"]},
                )
                await self.notification_service.send(message)
                await conn.execute(
                    """
                    INSERT INTO notification_log (
                        id, patient_id, notification_type, channel, recipient_id, recipient_address,
                        message_text, message_payload, status, sent_at, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'sent', $9, $9)
                    """,
                    str(uuid.uuid4()),
                    patient_id,
                    status.value,
                    channel.value,
                    recipient["caregiver_id"],
                    recipient["recipient"],
                    text,
                    {"alarm_id": alarm_id, "course_id": course_id},
                    self.clock.now(),
                )
