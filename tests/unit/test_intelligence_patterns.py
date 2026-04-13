import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, 'src')

from backend.events.bus import InMemoryEventBus, get_event_bus, set_event_bus
from backend.intelligence.patterns import PatternEngine


class MockPool:
    def __init__(self, events=None):
        self.events = events or []
        self.patterns = {}
        self._conn = MockConnection(self)

    def acquire(self):
        return self._conn


class MockConnection:
    def __init__(self, pool):
        self.pool = pool

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def fetch(self, query, *params):
        q = ' '.join(query.lower().split())
        if 'from events' in q:
            patient_id, start, end = params
            return [
                event for event in self.pool.events
                if event['patient_id'] == patient_id and start <= event['occurred_at'] <= end
            ]
        return []

    async def execute(self, query, *params):
        q = ' '.join(query.lower().split())
        if 'insert into patient_patterns' in q:
            patient_id, pattern_type, pattern_key, pattern_value, confidence, sample_count, detected_at = params
            self.pool.patterns[(patient_id, pattern_type, pattern_key)] = {
                'pattern_type': pattern_type,
                'pattern_key': pattern_key,
                'pattern_value': pattern_value,
                'confidence': confidence,
                'sample_count': sample_count,
                'last_updated': detected_at,
            }
            return 'INSERT 0 1'
        return 'OK'


@pytest.fixture(autouse=True)
def reset_event_bus():
    set_event_bus(InMemoryEventBus())


@pytest.mark.asyncio
async def test_compute_patterns_detects_and_persists_supported_signals():
    patient_id = 'patient-1'
    now = datetime(2026, 4, 11, 5, 0, tzinfo=timezone.utc)
    events = []

    # Prior week, stable overnight readings.
    for day, values in enumerate([
        (100, 102),
        (99, 101),
        (98, 100),
        (101, 103),
        (100, 101),
        (99, 100),
        (100, 102),
    ]):
        bedtime = datetime(2026, 4, 1 + day, 21, 45, tzinfo=timezone.utc)
        for idx, value in enumerate(values):
            occurred_at = bedtime + timedelta(hours=3 + idx)
            events.append(_event(patient_id, f'prior-{day}-{idx}', 'glucose_reading', {'value_mg_dl': value}, occurred_at))
        events.append(_event(patient_id, f'prior-dose-{day}', 'cornstarch_dose', {'grams': 30, 'is_bedtime_dose': True}, bedtime))

    # Recent 3 days, late bedtime doses + overnight low clusters + more variable readings.
    recent_days = [
        (datetime(2026, 4, 8, 22, 30, tzinfo=timezone.utc), [65, 62, 150, 140]),
        (datetime(2026, 4, 9, 22, 40, tzinfo=timezone.utc), [68, 64, 155, 145]),
        (datetime(2026, 4, 10, 22, 50, tzinfo=timezone.utc), [70, 150, 60, 140]),
    ]
    for day, (bedtime, readings) in enumerate(recent_days):
        events.append(_event(patient_id, f'recent-dose-{day}', 'cornstarch_dose', {'grams': 35, 'is_bedtime_dose': True}, bedtime))
        for idx, value in enumerate(readings):
            occurred_at = bedtime + timedelta(hours=2, minutes=30 + idx * 45)
            events.append(_event(patient_id, f'recent-{day}-{idx}', 'glucose_reading', {'value_mg_dl': value}, occurred_at))

    pool = MockPool(events=events)
    engine = PatternEngine(pool)

    signals = await engine.compute_patterns(patient_id, now=now)
    by_type = {signal.pattern_type: signal for signal in signals}

    assert set(by_type) == {'late_bedtime_dosing', 'overnight_low_cluster', 'recent_instability'}

    late = by_type['late_bedtime_dosing']
    assert late.severity == 5
    assert late.confidence == 1.0
    assert len(late.supporting_event_ids) == 3
    assert 'after 22:00' in late.reason

    lows = by_type['overnight_low_cluster']
    assert lows.severity == 6
    assert lows.confidence == 0.64
    assert lows.metadata['nights_affected'] == 2
    assert len(lows.supporting_event_ids) == 4

    instability = by_type['recent_instability']
    assert instability.severity >= 8
    assert instability.confidence == 1.0
    assert 'increased by' in instability.reason
    assert len(instability.supporting_event_ids) == 12

    persisted = pool.patterns[(patient_id, 'recent_instability', 'recent_instability')]
    persisted_value = json.loads(persisted['pattern_value'])
    assert persisted_value['pattern_type'] == 'recent_instability'
    assert persisted_value['metadata']['recent_readings'] == 12

    published = []
    get_event_bus().subscribe('pattern.detected', lambda event: published.append(event))
    await engine._publish_patterns(patient_id, signals)
    assert len(published) == 3
    assert published[0]['data']['pattern_key'] == published[0]['data']['pattern_type']


@pytest.mark.asyncio
async def test_compute_patterns_returns_no_signals_for_sparse_data():
    patient_id = 'patient-2'
    now = datetime(2026, 4, 11, 5, 0, tzinfo=timezone.utc)
    events = [
        _event(patient_id, 'dose-1', 'cornstarch_dose', {'grams': 30, 'is_bedtime_dose': True}, datetime(2026, 4, 10, 21, 50, tzinfo=timezone.utc)),
        _event(patient_id, 'g-1', 'glucose_reading', {'value_mg_dl': 85}, datetime(2026, 4, 11, 2, 0, tzinfo=timezone.utc)),
        _event(patient_id, 'g-2', 'glucose_reading', {'value_mg_dl': 83}, datetime(2026, 4, 11, 4, 0, tzinfo=timezone.utc)),
    ]

    pool = MockPool(events=events)
    engine = PatternEngine(pool)

    signals = await engine.compute_patterns(patient_id, now=now)

    assert signals == []
    assert pool.patterns == {}


def _event(patient_id: str, event_id: str, event_type: str, payload: dict, occurred_at: datetime) -> dict:
    return {
        'id': event_id,
        'patient_id': patient_id,
        'event_type': event_type,
        'source_type': 'manual',
        'payload': payload,
        'occurred_at': occurred_at,
        'recorded_at': occurred_at,
        'amends': None,
        'amended_by': None,
    }
