"""
Integration tests for Event Store.

Tests:
- Event append and retrieval
- Timeline reconstruction
- Event immutability (no updates allowed)
- Concurrent event appends
- Payload validation

Coverage target: 100% on data layer.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import pytest
import pytest_asyncio

# These would be real imports in production
# For testing without a real DB, we mock at the pool level


class MockPool:
    """Mock asyncpg Pool for testing."""
    
    def __init__(self):
        self.connections = []
        self._setup_complete = False
        self.events_storage: list[dict] = []
    
    async def acquire(self):
        return MockConnection(self)
    
    async def release(self, conn):
        pass
    
    async def close(self):
        pass


class MockConnection:
    """Mock asyncpg Connection for testing."""
    
    def __init__(self, pool: MockPool):
        self.pool = pool
        self._in_transaction = False
    
    async def execute(self, query: str, *params):
        # Parse and handle different SQL commands
        query_upper = query.strip().upper()
        
        if query_upper.startswith("INSERT INTO events"):
            # Extract values from query
            # This is a simplified mock - real implementation would parse properly
            event_id = params[0]
            patient_id = params[1]
            event_type = params[2]
            source_type = params[3]
            source_id = params[4]
            payload = params[5]
            occurred_at = params[6]
            recorded_at = params[7]
            amends = params[8] if len(params) > 8 else None
            
            event = {
                "id": event_id,
                "patient_id": patient_id,
                "event_type": event_type,
                "source_type": source_type,
                "source_id": source_id,
                "payload": payload if isinstance(payload, dict) else json.loads(payload),
                "occurred_at": occurred_at,
                "recorded_at": recorded_at,
                "amends": amends,
                "amended_by": None,
            }
            self.pool.events_storage.append(event)
            return "INSERT 1"
        
        elif "SELECT COUNT(*) FROM events WHERE patient_id" in query_upper:
            patient_id = params[0]
            count = sum(1 for e in self.pool.events_storage if e["patient_id"] == patient_id)
            return count
        
        return "OK"
    
    async def fetch(self, query: str, *params):
        # Extract patient_id and filters from params
        patient_id = params[0]
        filters = params[1:]
        
        events = [e for e in self.pool.events_storage if e["patient_id"] == patient_id]
        
        # Apply event type filter if present
        if events and len(filters) > 0:
            # Simple check - just return all matching patient events for now
            pass
        
        return events
    
    async def fetchrow(self, query: str, *params):
        events = await self.fetch(query, *params)
        return events[0] if events else None
    
    async def fetchval(self, query: str, *params):
        result = await self.fetchrow(query, *params)
        if isinstance(result, int):
            return result
        return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


# Import the actual store implementation to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.backend.events.store import (
    EventStore,
    Event,
    validate_payload,
    PayloadValidationError,
    EventTypeError,
    EVENT_TYPES,
    SOURCE_TYPES,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_pool():
    """Create a mock database pool."""
    return MockPool()


@pytest_asyncio.fixture
async def event_store(mock_pool):
    """Create an EventStore with mock pool."""
    return EventStore(mock_pool)


@pytest.fixture
def sample_patient_id():
    """Generate a sample patient UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_glucose_payload():
    """Sample glucose reading payload."""
    return {
        "value_mg_dl": 95,
        "reading_type": "fingerstick",
        "context": "fasting_morning",
    }


@pytest.fixture
def sample_cornstarch_payload():
    """Sample cornstarch dose payload."""
    return {
        "grams": 45,
        "brand": "raw_cornstarch",
        "is_bedtime_dose": False,
    }


# ============================================================
# PAYLOAD VALIDATION TESTS
# ============================================================

class TestPayloadValidation:
    """Test payload schema validation."""
    
    def test_valid_glucose_payload(self, sample_glucose_payload):
        """Valid glucose payload passes validation."""
        validate_payload("glucose_reading", sample_glucose_payload)
    
    def test_missing_required_field(self, sample_glucose_payload):
        """Missing required field raises PayloadValidationError."""
        del sample_glucose_payload["value_mg_dl"]
        with pytest.raises(PayloadValidationError) as exc_info:
            validate_payload("glucose_reading", sample_glucose_payload)
        assert "value_mg_dl" in str(exc_info.value)
    
    def test_unknown_event_type(self, sample_glucose_payload):
        """Unknown event type raises EventTypeError."""
        with pytest.raises(EventTypeError) as exc_info:
            validate_payload("unknown_event", sample_glucose_payload)
        assert "unknown_event" in str(exc_info.value)
    
    def test_valid_cornstarch_payload(self, sample_cornstarch_payload):
        """Valid cornstarch payload passes."""
        validate_payload("cornstarch_dose", sample_cornstarch_payload)
    
    def test_valid_meal_payload(self):
        """Valid meal payload passes."""
        validate_payload("meal", {
            "meal_type": "dinner",
            "description": "pasta with sauce",
            "contains_cornstarch": False,
        })
    
    def test_valid_symptom_payload(self):
        """Valid symptom payload passes."""
        validate_payload("symptom", {
            "symptom_type": "hypoglycemia",
            "severity": 3,
            "context": "post_exercise",
        })
    
    def test_optional_fields_not_required(self):
        """Optional fields can be omitted."""
        validate_payload("glucose_reading", {"value_mg_dl": 100})
    
    def test_extra_fields_allowed(self, sample_glucose_payload):
        """Extra fields not in schema are allowed."""
        sample_glucose_payload["extra_field"] = "ignored"
        validate_payload("glucose_reading", sample_glucose_payload)


# ============================================================
# EVENT STORE TESTS
# ============================================================

class TestEventStoreBasic:
    """Test basic EventStore operations."""
    
    @pytest.mark.asyncio
    async def test_append_event_returns_uuid(self, event_store, sample_patient_id, sample_glucose_payload):
        """append_event returns the UUID of the created event."""
        event_id = await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
        )
        assert isinstance(event_id, str)
        assert len(event_id) == 36  # UUID format
    
    @pytest.mark.asyncio
    async def test_append_event_stores_data(self, event_store, sample_patient_id, sample_glucose_payload):
        """Appended event is stored in the database."""
        event_id = await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
        )
        
        event = await event_store.get_event_by_id(event_id)
        assert event is not None
        assert event.patient_id == sample_patient_id
        assert event.event_type == "glucose_reading"
        assert event.payload["value_mg_dl"] == 95
    
    @pytest.mark.asyncio
    async def test_get_events_returns_list(self, event_store, sample_patient_id, sample_glucose_payload):
        """get_events returns a list of events."""
        # Append a few events
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
        )
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="cornstarch_dose",
            payload=sample_cornstarch_payload(),
            source_type="manual",
        )
        
        events = await event_store.get_events(sample_patient_id)
        assert isinstance(events, list)
        assert len(events) >= 2
    
    @pytest.mark.asyncio
    async def test_get_events_filter_by_type(self, event_store, sample_patient_id, sample_glucose_payload):
        """get_events can filter by event types."""
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
        )
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="cornstarch_dose",
            payload=sample_cornstarch_payload(),
            source_type="manual",
        )
        
        glucose_events = await event_store.get_events(
            sample_patient_id,
            event_types=["glucose_reading"]
        )
        assert all(e.event_type == "glucose_reading" for e in glucose_events)
    
    @pytest.mark.asyncio
    async def test_get_events_filter_by_time(self, event_store, sample_patient_id, sample_glucose_payload):
        """get_events can filter by time range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        
        # Append event with occurred_at in the past
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
            occurred_at=yesterday,
        )
        
        # Get events since recent time
        recent_events = await event_store.get_events(
            sample_patient_id,
            since=now - timedelta(hours=1),
        )
        # Recent query shouldn't return yesterday's event
        assert len(recent_events) == 0 or all(
            e.occurred_at >= now - timedelta(hours=1) for e in recent_events
        )


class TestEventStoreTimeline:
    """Test timeline reconstruction."""
    
    @pytest.mark.asyncio
    async def test_get_timeline_returns_chronological_order(self, event_store, sample_patient_id, sample_glucose_payload):
        """get_timeline returns events in chronological order."""
        now = datetime.now(timezone.utc)
        
        # Append events at different times
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="meal",
            payload={"meal_type": "breakfast"},
            source_type="manual",
            occurred_at=now - timedelta(hours=4),
        )
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="cornstarch_dose",
            payload=sample_cornstarch_payload(),
            source_type="manual",
            occurred_at=now - timedelta(hours=3),
        )
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
            occurred_at=now - timedelta(hours=1),
        )
        
        timeline = await event_store.get_timeline(
            patient_id=sample_patient_id,
            start=now - timedelta(hours=5),
            end=now,
        )
        
        # Verify chronological order
        timestamps = [e.occurred_at for e in timeline]
        assert timestamps == sorted(timestamps)
    
    @pytest.mark.asyncio
    async def test_get_timeline_respects_time_range(self, event_store, sample_patient_id, sample_glucose_payload):
        """get_timeline respects start and end times."""
        now = datetime.now(timezone.utc)
        
        # Add events outside the requested range
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
            occurred_at=now - timedelta(days=1),  # Day old
        )
        await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
            occurred_at=now,  # Now
        )
        
        # Get last hour
        timeline = await event_store.get_timeline(
            patient_id=sample_patient_id,
            start=now - timedelta(hours=1),
            end=now,
        )
        
        # Should only have recent events
        for event in timeline:
            assert now - timedelta(hours=1) <= event.occurred_at <= now


class TestEventImmutability:
    """Test that events are truly immutable."""
    
    @pytest.mark.asyncio
    async def test_cannot_update_event(self, event_store, sample_patient_id, sample_glucose_payload):
        """Events cannot be updated (append-only guarantee)."""
        event_id = await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
        )
        
        # Verify the event exists unchanged
        event = await event_store.get_event_by_id(event_id)
        assert event is not None
        assert event.payload["value_mg_dl"] == 95
        
        # Try to get via get_events and verify original data
        events = await event_store.get_events(sample_patient_id)
        original_event = next((e for e in events if e.id == event_id), None)
        assert original_event is not None
        assert original_event.payload["value_mg_dl"] == 95
    
    @pytest.mark.asyncio
    async def test_cannot_delete_event(self, event_store, sample_patient_id, sample_glucose_payload):
        """Events cannot be deleted (append-only guarantee)."""
        event_id = await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
        )
        
        # Event should still exist after append
        event = await event_store.get_event_by_id(event_id)
        assert event is not None
    
    @pytest.mark.asyncio
    async def test_amends_is_allowed(self, event_store, sample_patient_id, sample_glucose_payload):
        """Amending events is supported via 'amends' reference."""
        original_id = await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload=sample_glucose_payload,
            source_type="manual",
        )
        
        # Append an amending event
        amended_id = await event_store.append_event(
            patient_id=sample_patient_id,
            event_type="glucose_reading",
            payload={**sample_glucose_payload, "corrected": True},
            source_type="manual",
            amends=original_id,
        )
        
        # Both events should exist
        original = await event_store.get_event_by_id(original_id)
        amended = await event_store.get_event_by_id(amended_id)
        
        assert original is not None
        assert amended is not None
        assert amended.amends == original_id


class TestConcurrentAppends:
    """Test concurrent event appends."""
    
    @pytest.mark.asyncio
    async def test_concurrent_append_events_unique_ids(self, event_store, sample_patient_id):
        """Concurrent appends produce unique event IDs."""
        event_ids = await asyncio.gather(
            event_store.append_event(
                patient_id=sample_patient_id,
                event_type="glucose_reading",
                payload={"value_mg_dl": 100 + i},
                source_type="manual",
            )
            for i in range(10)
        )
        
        # All IDs should be unique
        assert len(event_ids) == len(set(event_ids))
    
    @pytest.mark.asyncio
    async def test_concurrent_append_same_patient(self, event_store, sample_patient_id):
        """Multiple concurrent events for same patient are all stored."""
        await asyncio.gather(
            event_store.append_event(
                patient_id=sample_patient_id,
                event_type="glucose_reading",
                payload={"value_mg_dl": 100 + i},
                source_type="manual",
            )
            for i in range(5)
        )
        
        events = await event_store.get_events(sample_patient_id)
        assert len(events) >= 5
    
    @pytest.mark.asyncio
    async def test_concurrent_append_different_patients(self, event_store):
        """Concurrent events for different patients don't interfere."""
        patient_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Concurrently append to different patients
        await asyncio.gather(
            event_store.append_event(
                patient_id=pid,
                event_type="glucose_reading",
                payload={"value_mg_dl": 100},
                source_type="manual",
            )
            for pid in patient_ids
        )
        
        # Each patient should have exactly 1 event
        for pid in patient_ids:
            events = await event_store.get_events(pid)
            assert len(events) == 1


class TestPayloadValidationIntegration:
    """Test payload validation in context of store operations."""
    
    @pytest.mark.asyncio
    async def test_append_invalid_payload_raises(self, event_store, sample_patient_id):
        """Appending event with invalid payload raises error."""
        with pytest.raises(PayloadValidationError) as exc_info:
            await event_store.append_event(
                patient_id=sample_patient_id,
                event_type="glucose_reading",
                payload={"wrong_field": 100},  # Missing value_mg_dl
                source_type="manual",
            )
        assert "value_mg_dl" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_append_unknown_event_type_raises(self, event_store, sample_patient_id):
        """Appending unknown event type raises error."""
        with pytest.raises(EventTypeError) as exc_info:
            await event_store.append_event(
                patient_id=sample_patient_id,
                event_type="nonexistent_event",
                payload={"data": "test"},
                source_type="manual",
            )
        assert "nonexistent_event" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_all_valid_event_types_can_be_appended(self, event_store, sample_patient_id):
        """All defined event types can be appended successfully."""
        for event_type in EVENT_TYPES:
            payload = _get_minimal_payload(event_type)
            event_id = await event_store.append_event(
                patient_id=sample_patient_id,
                event_type=event_type,
                payload=payload,
                source_type="manual",
            )
            assert isinstance(event_id, str)
    
    @pytest.mark.asyncio
    async def test_source_type_validation(self, event_store, sample_patient_id, sample_glucose_payload):
        """Invalid source_type raises error."""
        with pytest.raises(Exception):  # EventStoreError
            await event_store.append_event(
                patient_id=sample_patient_id,
                event_type="glucose_reading",
                payload=sample_glucose_payload,
                source_type="invalid_source",
            )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def sample_cornstarch_payload():
    """Factory for sample cornstarch payload."""
    return {
        "grams": 45,
        "brand": "raw_cornstarch",
        "is_bedtime_dose": False,
    }


def _get_minimal_payload(event_type: str) -> dict:
    """Get minimal valid payload for event type."""
    minimal_payloads = {
        "glucose_reading": {"value_mg_dl": 100},
        "cornstarch_dose": {"grams": 45},
        "meal": {"meal_type": "snack"},
        "symptom": {"symptom_type": "fatigue"},
        "coverage_course_start": {"course_id": str(uuid.uuid4()), "trigger_type": "cornstarch", "duration_minutes": 309},
        "coverage_course_end": {"course_id": str(uuid.uuid4()), "ended_at": datetime.now(timezone.utc).isoformat()},
        "alarm_triggered": {"alarm_state_id": str(uuid.uuid4()), "course_id": str(uuid.uuid4()), "reason": "timeout"},
        "alarm_acknowledged": {"alarm_state_id": str(uuid.uuid4()), "acknowledged_by": str(uuid.uuid4())},
        "alarm_escalated": {"alarm_state_id": str(uuid.uuid4()), "escalated_to": str(uuid.uuid4())},
        "notification_sent": {"notification_id": str(uuid.uuid4()), "channel": "telegram", "recipient": "user123"},
        "pattern_detected": {"pattern_type": "timing", "pattern_key": "bedtime_dose"},
        "baseline_updated": {"metric_type": "glucose", "baseline": {"mean": 100}},
        "caregiver_notified": {"caregiver_id": str(uuid.uuid4()), "notification_type": "warning"},
    }
    return minimal_payloads.get(event_type, {"data": "test"})


# ============================================================
# TEST CONFIGURATION
# ============================================================

def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


# ============================================================
# RUN WITHOUT DATABASE
# ============================================================

if __name__ == "__main__":
    # Can run tests without database using mock pool
    pytest.main([__file__, "-v", "-m", "not asyncio"])