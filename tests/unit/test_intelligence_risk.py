import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, 'src')

from backend.events.bus import InMemoryEventBus, set_event_bus
from backend.intelligence.risk import RiskEngine


class MockPool:
    def __init__(self, events=None, courses=None):
        self.events = events or []
        self.courses = courses or []
        self.baselines = {}
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
        if 'from coverage_courses' in q:
            patient_id, start, end = params
            return [
                course for course in self.pool.courses
                if course['patient_id'] == patient_id and start <= course['started_at'] <= end
            ]
        return []

    async def fetchrow(self, query, *params):
        q = ' '.join(query.lower().split())
        if "from patient_patterns" in q and "overnight_risk" in q:
            patient_id = params[0]
            return self.pool.patterns.get((patient_id, 'overnight_risk', 'current'))
        if 'from patient_baselines' in q:
            patient_id, metric = params
            return self.pool.baselines.get((patient_id, metric))
        return None

    async def execute(self, query, *params):
        q = ' '.join(query.lower().split())
        if 'insert into patient_baselines' in q:
            patient_id, metric_type, metric_value, computed_from_events, sample_count, computed_at, valid_until = params
            self.pool.baselines[(patient_id, metric_type)] = {
                'metric_type': metric_type,
                'metric_value': metric_value,
                'computed_from_events': computed_from_events,
                'sample_count': sample_count,
                'computed_at': computed_at,
                'valid_until': valid_until,
            }
            return 'INSERT 0 1'
        if 'insert into patient_patterns' in q:
            if len(params) == 7:
                patient_id, pattern_type, pattern_key, pattern_value, confidence, sample_count, detected_at = params
            else:
                patient_id, pattern_value, confidence, sample_count, detected_at = params
                pattern_type = 'overnight_risk'
                pattern_key = 'current'
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
async def test_compute_risk_generates_weighted_score_and_persists_snapshot():
    patient_id = 'patient-risk-1'
    now = datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc)
    pool = MockPool(events=_build_events(patient_id), courses=_build_courses(patient_id))

    engine = RiskEngine(pool)
    risk = await engine.compute_risk(patient_id, now=now)

    assert risk.risk_level in {'medium', 'high', 'critical'}
    assert risk.risk_score > 0
    assert risk.confidence > 0
    assert any(factor['factor'] == 'coverage_gap_frequency' for factor in risk.factors)

    stored = pool.patterns[(patient_id, 'overnight_risk', 'current')]
    payload = json.loads(stored['pattern_value'])
    assert payload['risk_level'] == risk.risk_level
    assert payload['risk_score'] == risk.risk_score


@pytest.mark.asyncio
async def test_get_risk_returns_stored_snapshot_when_available():
    patient_id = 'patient-risk-2'
    pool = MockPool()
    pool.patterns[(patient_id, 'overnight_risk', 'current')] = {
        'pattern_value': json.dumps({
            'patient_id': patient_id,
            'risk_score': 4.5,
            'risk_level': 'medium',
            'confidence': 0.83,
            'factors': [{'factor': 'recent_instability'}],
            'supporting_events': ['evt-1'],
            'generated_at': '2026-04-11T06:00:00+00:00',
        })
    }

    engine = RiskEngine(pool)
    risk = await engine.get_risk(patient_id)

    assert risk.risk_level == 'medium'
    assert risk.risk_score == 4.5
    assert risk.supporting_events == ['evt-1']


def _build_events(patient_id: str) -> list[dict]:
    events = []

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

    return events


def _build_courses(patient_id: str) -> list[dict]:
    courses = []
    for day in range(8):
        bedtime = datetime(2026, 4, 1 + day, 22, 30, tzinfo=timezone.utc)
        courses.append({
            'id': f'course-{day}',
            'patient_id': patient_id,
            'started_at': bedtime,
            'expected_end_at': bedtime + timedelta(hours=5, minutes=9),
            'actual_end_at': None,
            'gap_minutes': 12 if day % 2 == 0 else 0,
            'overlap_minutes': 0,
            'trigger_type': 'cornstarch',
            'is_bedtime_dose': True,
        })
    return courses


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
