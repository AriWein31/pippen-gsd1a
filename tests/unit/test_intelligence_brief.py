import json
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

sys.path.insert(0, 'src')

from backend.intelligence.brief import BriefGenerator


class MockPool:
    def __init__(self, events=None, courses=None):
        self.events = events or []
        self.courses = courses or []
        self.baselines = {}
        self.patterns = {}
        self.briefs = {}
        self.patients = set()
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
        if 'select id from patients' in q:
            patient_id = params[0]
            if patient_id in self.pool.patients:
                return {'id': patient_id}
            return None
        if 'from patient_baselines' in q:
            patient_id, metric = params
            return self.pool.baselines.get((patient_id, metric))
        if 'from daily_briefs' in q:
            patient_id, brief_date = params
            return self.pool.briefs.get((patient_id, brief_date.isoformat()))
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
        if 'insert into daily_briefs' in q:
            patient_id, brief_date, summary, key_insights, risk_alerts, recommendations, coverage_summary, confidence, created_at = params
            self.pool.briefs[(patient_id, brief_date.isoformat())] = {
                'patient_id': patient_id,
                'brief_date': brief_date,
                'summary': summary,
                'key_insights': key_insights,
                'risk_alerts': risk_alerts,
                'recommendations': recommendations,
                'coverage_summary': coverage_summary,
                'confidence': confidence,
                'created_at': created_at,
            }
            return 'INSERT 0 1'
        return 'OK'


@pytest.mark.asyncio
async def test_generate_daily_brief_persists_high_confidence_patient_brief():
    patient_id = 'patient-brief-1'
    now = datetime(2026, 4, 11, 6, 5, tzinfo=timezone.utc)
    pool = MockPool(
        events=_build_events(patient_id),
        courses=_build_courses(patient_id),
    )
    pool.patients.add(patient_id)

    generator = BriefGenerator(pool)
    brief = await generator.generate_daily_brief(patient_id, now=now)

    assert brief.brief_date == '2026-04-11'
    assert brief.generated_at == '2026-04-11T06:00:00+00:00'
    assert brief.confidence >= 0.71
    assert brief.summary == 'Overnight readings were more variable than the recent baseline.'
    assert len(brief.what_changed) <= 3
    assert len(brief.what_matters) <= 3
    assert len(brief.recommended_attention) <= 3
    assert brief.supporting_events
    assert 'events:' in brief.what_changed[0]

    stored = pool.briefs[(patient_id, '2026-04-11')]
    stored_changes = json.loads(stored['key_insights'])
    stored_summary = json.loads(stored['coverage_summary'])
    assert stored_changes == brief.what_changed
    assert stored_summary['supporting_events'] == brief.supporting_events


@pytest.mark.asyncio
async def test_get_daily_brief_returns_existing_snapshot_without_regeneration():
    patient_id = 'patient-brief-2'
    pool = MockPool()
    pool.patients.add(patient_id)
    pool.briefs[(patient_id, '2026-04-11')] = {
        'patient_id': patient_id,
        'brief_date': date(2026, 4, 11),
        'summary': 'Stored summary',
        'key_insights': json.dumps(['stored change']),
        'risk_alerts': json.dumps(['stored matter']),
        'recommendations': json.dumps(['stored attention']),
        'coverage_summary': json.dumps({'supporting_events': ['evt-1'], 'generated_at': '2026-04-11T06:00:00+00:00'}),
        'confidence': 0.88,
        'created_at': datetime(2026, 4, 11, 6, 0, tzinfo=timezone.utc),
    }

    generator = BriefGenerator(pool)
    brief = await generator.get_daily_brief(patient_id, brief_date=date(2026, 4, 11))

    assert brief.summary == 'Stored summary'
    assert brief.what_changed == ['stored change']
    assert brief.supporting_events == ['evt-1']


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
