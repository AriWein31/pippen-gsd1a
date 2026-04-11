import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, 'src')

from backend.events.bus import InMemoryEventBus, set_event_bus
from backend.intelligence.baseline import BaselineEngine


class MockPool:
    def __init__(self, events=None, courses=None):
        self.events = events or []
        self.courses = courses or []
        self.baselines = {}
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
        if 'from patient_baselines' in q:
            patient_id, metric = params
            row = self.pool.baselines.get((patient_id, metric))
            return row
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
        return 'OK'


@pytest.fixture(autouse=True)
def reset_event_bus():
    set_event_bus(InMemoryEventBus())


@pytest.mark.asyncio
async def test_compute_baselines_persists_expected_metrics():
    patient_id = 'patient-1'
    base = datetime(2026, 4, 1, 0, 30, tzinfo=timezone.utc)
    events = []
    courses = []

    for day in range(8):
        overnight = base + timedelta(days=day)
        bedtime = (base + timedelta(days=day)).replace(hour=22, minute=30)
        next_event = bedtime + timedelta(hours=4)

        events.extend([
            {
                'id': f'g-{day}-1',
                'patient_id': patient_id,
                'event_type': 'glucose_reading',
                'source_type': 'manual',
                'payload': {'value_mg_dl': 80 + day},
                'occurred_at': overnight,
                'recorded_at': overnight,
                'amends': None,
                'amended_by': None,
            },
            {
                'id': f'g-{day}-2',
                'patient_id': patient_id,
                'event_type': 'glucose_reading',
                'source_type': 'manual',
                'payload': {'value_mg_dl': 60 if day < 2 else 90 + day},
                'occurred_at': overnight + timedelta(hours=2),
                'recorded_at': overnight + timedelta(hours=2),
                'amends': None,
                'amended_by': None,
            },
            {
                'id': f'dose-{day}',
                'patient_id': patient_id,
                'event_type': 'cornstarch_dose',
                'source_type': 'manual',
                'payload': {'grams': 30, 'is_bedtime_dose': True},
                'occurred_at': bedtime,
                'recorded_at': bedtime,
                'amends': None,
                'amended_by': None,
            },
            {
                'id': f'next-{day}',
                'patient_id': patient_id,
                'event_type': 'glucose_reading',
                'source_type': 'manual',
                'payload': {'value_mg_dl': 100 + day},
                'occurred_at': next_event,
                'recorded_at': next_event,
                'amends': None,
                'amended_by': None,
            },
        ])
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

    pool = MockPool(events=events, courses=courses)
    engine = BaselineEngine(pool)

    baselines = await engine.compute_baselines(patient_id)

    avg = baselines.get_metric('overnight_average_glucose')
    assert avg is not None
    assert avg.value == 90.96
    assert avg.qualifying_days == 9
    assert avg.confidence == 0.64

    variability = baselines.get_metric('overnight_glucose_variability_cv')
    assert variability is not None
    assert variability.value is not None
    assert variability.value > 0

    low_frequency = baselines.get_metric('overnight_low_glucose_frequency')
    assert low_frequency is not None
    assert low_frequency.value == 0.0833
    assert low_frequency.metadata['low_count'] == 2

    bedtime_interval = baselines.get_metric('median_bedtime_to_next_event_interval_minutes')
    assert bedtime_interval is not None
    assert bedtime_interval.value == 240.0

    gap_frequency = baselines.get_metric('coverage_gap_frequency')
    assert gap_frequency is not None
    assert gap_frequency.value == 0.5

    stored = await engine.get_baseline(patient_id, 'coverage_gap_frequency')
    assert stored is not None
    assert stored.value == 0.5

    persisted_record = json.loads(pool.baselines[(patient_id, 'overnight_average_glucose')]['metric_value'])
    assert persisted_record['value'] == 90.96
    assert len(persisted_record['supporting_event_ids']) == 24


@pytest.mark.asyncio
async def test_compute_baselines_returns_null_metrics_when_data_is_sparse():
    patient_id = 'patient-2'
    base = datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc)
    events = []
    courses = []

    for day in range(3):
        overnight = base + timedelta(days=day)
        bedtime = (base + timedelta(days=day)).replace(hour=22, minute=15)
        events.extend([
            {
                'id': f'sparse-g-{day}',
                'patient_id': patient_id,
                'event_type': 'glucose_reading',
                'source_type': 'manual',
                'payload': {'value_mg_dl': 85},
                'occurred_at': overnight,
                'recorded_at': overnight,
                'amends': None,
                'amended_by': None,
            },
            {
                'id': f'sparse-dose-{day}',
                'patient_id': patient_id,
                'event_type': 'cornstarch_dose',
                'source_type': 'manual',
                'payload': {'grams': 25, 'is_bedtime_dose': True},
                'occurred_at': bedtime,
                'recorded_at': bedtime,
                'amends': None,
                'amended_by': None,
            },
        ])
        courses.append({
            'id': f'sparse-course-{day}',
            'patient_id': patient_id,
            'started_at': bedtime,
            'expected_end_at': bedtime + timedelta(hours=5),
            'actual_end_at': None,
            'gap_minutes': 0,
            'overlap_minutes': 0,
            'trigger_type': 'cornstarch',
            'is_bedtime_dose': True,
        })

    pool = MockPool(events=events, courses=courses)
    engine = BaselineEngine(pool)

    baselines = await engine.compute_baselines(patient_id)

    for metric in baselines.metrics.values():
        assert metric.value is None
        assert metric.confidence == 0.0
        assert 'Insufficient data' in metric.rationale
