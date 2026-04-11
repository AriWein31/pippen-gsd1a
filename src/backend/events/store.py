"""
Event Store — Append-only event store for Pippen.

Implements the core event-sourced data layer for GSD1A patient tracking.

Key principles:
- Events are APPEND-ONLY. Never UPDATE or DELETE.
- Every event has a patient_id, event_type, payload, and occurred_at.
- Amending events are supported via `amends` reference (no actual modifications).
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

import asyncpg


# Event types
EVENT_TYPES = {
    "glucose_reading",
    "cornstarch_dose",
    "meal",
    "symptom",
    "coverage_course_start",
    "coverage_course_end",
    "alarm_triggered",
    "alarm_acknowledged",
    "alarm_escalated",
    "notification_sent",
    "pattern_detected",
    "baseline_updated",
    "caregiver_notified",
}

# Source types
SOURCE_TYPES = {"manual", "sensor", "api", "system"}

# Payload schemas per event type
PAYLOAD_SCHEMAS = {
    "glucose_reading": {
        "required": ["value_mg_dl"],
        "optional": ["reading_type", "context", "sensor_id"],
    },
    "cornstarch_dose": {
        "required": ["grams"],
        "optional": ["brand", "is_bedtime_dose", "notes"],
    },
    "meal": {
        "required": ["meal_type"],
        "optional": ["description", "contains_cornstarch", "carbs_estimated"],
    },
    "symptom": {
        "required": ["symptom_type"],
        "optional": ["severity", "context", "duration_minutes"],
    },
    "coverage_course_start": {
        "required": ["course_id", "trigger_type", "duration_minutes"],
        "optional": ["is_bedtime_dose", "notes"],
    },
    "coverage_course_end": {
        "required": ["course_id", "ended_at"],
        "optional": ["actual_duration_minutes", "notes"],
    },
    "alarm_triggered": {
        "required": ["alarm_state_id", "course_id", "reason"],
        "optional": ["notification_ids"],
    },
    "alarm_acknowledged": {
        "required": ["alarm_state_id", "acknowledged_by"],
        "optional": ["acknowledgment_type", "notes"],
    },
    "alarm_escalated": {
        "required": ["alarm_state_id", "escalated_to"],
        "optional": ["escalation_reason", "notification_ids"],
    },
    "notification_sent": {
        "required": ["notification_id", "channel", "recipient"],
        "optional": ["message_type", "status"],
    },
    "pattern_detected": {
        "required": ["pattern_type", "pattern_key"],
        "optional": ["pattern_value", "confidence", "sample_count"],
    },
    "baseline_updated": {
        "required": ["metric_type", "baseline"],
        "optional": ["sample_count", "computed_from"],
    },
    "caregiver_notified": {
        "required": ["caregiver_id", "notification_type"],
        "optional": ["channel", "message_id"],
    },
}


@dataclass
class Event:
    """Immutable event record."""
    id: str
    patient_id: str
    event_type: str
    source_type: str
    payload: dict
    occurred_at: datetime
    recorded_at: datetime
    amends: Optional[str] = None
    amended_by: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "event_type": self.event_type,
            "source_type": self.source_type,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat() if isinstance(self.occurred_at, datetime) else self.occurred_at,
            "recorded_at": self.recorded_at.isoformat() if isinstance(self.recorded_at, datetime) else self.recorded_at,
            "amends": self.amends,
            "amended_by": self.amended_by,
        }


class EventStoreError(Exception):
    """Base exception for event store errors."""
    pass


class PayloadValidationError(EventStoreError):
    """Raised when event payload doesn't match schema."""
    pass


class EventTypeError(EventStoreError):
    """Raised when event type is unknown."""
    pass


class ImmutableEventError(EventStoreError):
    """Raised when attempting to modify an existing event."""
    pass


def validate_payload(event_type: str, payload: dict) -> None:
    """Validate event payload against schema."""
    if event_type not in PAYLOAD_SCHEMAS:
        raise EventTypeError(f"Unknown event type: {event_type}")
    
    schema = PAYLOAD_SCHEMAS[event_type]
    
    # Check required fields
    for field_name in schema.get("required", []):
        if field_name not in payload:
            raise PayloadValidationError(
                f"Missing required field '{field_name}' for event type '{event_type}'"
            )


class EventStore:
    """
    Append-only event store implementation.
    
    Usage:
        store = EventStore(pool)
        event_id = await store.append_event(
            patient_id="...",
            event_type="glucose_reading",
            payload={"value_mg_dl": 95, "reading_type": "fingerstick"},
            source_type="manual"
        )
        
        events = await store.get_events(
            patient_id="...",
            since=datetime.now(timezone.utc) - timedelta(hours=24),
            event_types=["glucose_reading", "cornstarch_dose"]
        )
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def append_event(
        self,
        patient_id: str,
        event_type: str,
        payload: dict,
        source_type: str,
        source_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
        amends: Optional[str] = None,
    ) -> str:
        """
        Append a new event to the store.
        
        Returns:
            The UUID of the created event.
            
        Raises:
            PayloadValidationError: If payload doesn't match event type schema.
            EventTypeError: If event_type is unknown.
        """
        # Validate
        validate_payload(event_type, payload)
        
        if source_type not in SOURCE_TYPES:
            raise EventStoreError(f"Unknown source_type: {source_type}")
        
        # Generate ID and timestamps
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        occurred = occurred_at or now
        
        # Insert
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO events (
                    id, patient_id, event_type, source_type, source_id,
                    payload, occurred_at, recorded_at, amends
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                event_id,
                patient_id,
                event_type,
                source_type,
                source_id,
                json.dumps(payload),
                occurred,
                now,
                amends,
            )
        
        return event_id
    
    async def get_events(
        self,
        patient_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        event_types: Optional[list[str]] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Event]:
        """
        Retrieve events for a patient.
        
        Args:
            patient_id: The patient's UUID.
            since: Return events after this time (inclusive).
            until: Return events before this time (inclusive).
            event_types: Filter to these event types only.
            limit: Maximum number of events to return.
            offset: Skip first N events.
            
        Returns:
            List of Event objects, ordered by occurred_at DESC.
        """
        query = """
            SELECT id, patient_id, event_type, source_type, payload,
                   occurred_at, recorded_at, amends, amended_by
            FROM events
            WHERE patient_id = $1
        """
        params = [patient_id]
        param_idx = 2
        
        if since:
            query += f" AND occurred_at >= ${param_idx}"
            params.append(since)
            param_idx += 1
        
        if until:
            query += f" AND occurred_at <= ${param_idx}"
            params.append(until)
            param_idx += 1
        
        if event_types:
            placeholders = ", ".join(f"${param_idx + i}" for i in range(len(event_types)))
            query += f" AND event_type IN ({placeholders})"
            params.extend(event_types)
            param_idx += len(event_types)
        
        query += f" ORDER BY occurred_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return [self._row_to_event(row) for row in rows]
    
    async def get_timeline(
        self,
        patient_id: str,
        start: datetime,
        end: datetime,
        event_types: Optional[list[str]] = None,
    ) -> list[Event]:
        """
        Get a timeline of events within a time range.
        
        Args:
            patient_id: The patient's UUID.
            start: Start of time range.
            end: End of time range.
            event_types: Optional filter.
            
        Returns:
            List of Event objects in chronological order.
        """
        events = await self.get_events(
            patient_id=patient_id,
            since=start,
            until=end,
            event_types=event_types,
            limit=10000,
        )
        # Reverse to get chronological order
        return list(reversed(events))
    
    async def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Get a single event by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, patient_id, event_type, source_type, payload,
                       occurred_at, recorded_at, amends, amended_by
                FROM events WHERE id = $1
                """,
                event_id,
            )
        if row:
            return self._row_to_event(row)
        return None
    
    async def get_patient_events_count(self, patient_id: str) -> int:
        """Get total event count for a patient."""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM events WHERE patient_id = $1",
                patient_id,
            )
        return count
    
    async def get_latest_by_type(
        self,
        patient_id: str,
        event_type: str,
        limit: int = 10,
    ) -> list[Event]:
        """Get latest events of a specific type."""
        return await self.get_events(
            patient_id=patient_id,
            event_types=[event_type],
            limit=limit,
        )
    
    def _row_to_event(self, row: asyncpg.Record) -> Event:
        """Convert database row to Event object."""
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        
        return Event(
            id=row["id"],
            patient_id=row["patient_id"],
            event_type=row["event_type"],
            source_type=row["source_type"],
            payload=payload,
            occurred_at=row["occurred_at"],
            recorded_at=row["recorded_at"],
            amends=row["amends"],
            amended_by=row["amended_by"],
        )


# Convenience functions for direct usage

async def create_event_store(database_url: str) -> EventStore:
    """Create an EventStore with connection pool."""
    pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    return EventStore(pool)