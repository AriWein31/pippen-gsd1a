import sys
from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, 'src')

from backend.api.patients import create_patients_router


class MockPool:
    def __init__(self):
        self.patients = {'patient-1'}
        self.baselines = {}
        self.patterns = {}
        self.briefs = {}
        self.events = []
        self.courses = []
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

    async def fetchrow(self, query, *params):
        q = ' '.join(query.lower().split())
        if 'select id from patients' in q:
            patient_id = params[0]
            return {'id': patient_id} if patient_id in self.pool.patients else None
        if 'from daily_briefs' in q:
            patient_id, brief_date = params
            return self.pool.briefs.get((patient_id, brief_date.isoformat()))
        if 'from patient_baselines' in q:
            patient_id, metric = params
            return self.pool.baselines.get((patient_id, metric))
        if 'from patient_patterns' in q and "overnight_risk" in q:
            patient_id = params[0]
            return self.pool.patterns.get((patient_id, 'overnight_risk', 'current'))
        return None

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


@pytest.fixture
def client():
    pool = MockPool()
    app = FastAPI()
    app.include_router(create_patients_router(pool))
    return TestClient(app)


def test_patient_intelligence_endpoints_require_existing_patient(client):
    response = client.get('/patients/missing/risk')
    assert response.status_code == 404


def test_regenerate_briefs_validates_payload(client):
    response = client.post('/patients/admin/regenerate-briefs', json=['patient-1'])
    assert response.status_code == 200
    assert isinstance(response.json(), list)
