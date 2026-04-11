import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, 'src')

from backend.alarms.engine import CoverageAlarmEngine, AlarmStatus
from backend.alarms.notifiers import InMemoryNotificationService


class FrozenClock:
    def __init__(self, now: datetime):
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now


class MockPool:
    def __init__(self):
        self.tables = {
            'coverage_courses': [],
            'night_alarm_state': [],
            'caregivers': [],
            'notification_log': [],
        }
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
        if 'select id from night_alarm_state where course_id = $1' in q:
            course_id = params[0]
            for row in self.pool.tables['night_alarm_state']:
                if row['course_id'] == course_id:
                    return row
            return None
        if 'from coverage_courses' in q and 'where id = $1' in q:
            course_id = params[0]
            for row in self.pool.tables['coverage_courses']:
                if row['id'] == course_id:
                    return row
            return None
        if 'from night_alarm_state' in q and 'where patient_id = $1' in q and 'limit 1' in q:
            patient_id = params[0]
            rows = [r for r in self.pool.tables['night_alarm_state'] if r['patient_id'] == patient_id]
            rows.sort(key=lambda r: r['created_at'], reverse=True)
            return rows[0] if rows else None
        return None

    async def fetch(self, query, *params):
        q = ' '.join(query.lower().split())
        if 'from night_alarm_state nas join coverage_courses cc' in q:
            rows = []
            for alarm in self.pool.tables['night_alarm_state']:
                if alarm['status'] in ('active', 'warning_sent', 'expired', 'alarmed'):
                    course = next(c for c in self.pool.tables['coverage_courses'] if c['id'] == alarm['course_id'])
                    rows.append({**alarm, 'trigger_type': course['trigger_type'], 'is_bedtime_dose': course['is_bedtime_dose']})
            rows.sort(key=lambda r: r['course_expected_end'])
            return rows
        if 'from night_alarm_state' in q and 'where patient_id = $1 and status in' in q:
            patient_id = params[0]
            return [r for r in self.pool.tables['night_alarm_state'] if r['patient_id'] == patient_id and r['status'] in ('active','warning_sent','expired','alarmed','escalated')]
        if 'from caregivers' in q:
            patient_id = params[0]
            preference_column = 'notify_warning' if 'notify_warning' in q else 'notify_alarm' if 'notify_alarm' in q else 'notify_escalation'
            rows = [r for r in self.pool.tables['caregivers'] if r['patient_id'] == patient_id and r.get(preference_column, False)]
            rows.sort(key=lambda r: r['escalation_order'])
            return rows
        return []

    async def execute(self, query, *params):
        q = ' '.join(query.lower().split())
        if 'insert into night_alarm_state' in q:
            self.pool.tables['night_alarm_state'].append({
                'id': params[0],
                'patient_id': params[1],
                'course_id': params[2],
                'status': params[3],
                'course_expected_end': params[4],
                'warning_sent_at': None,
                'expired_at': None,
                'alarmed_at': None,
                'escalated_at': None,
                'resolved_at': None,
                'warning_recipients': [],
                'alarm_recipients': [],
                'escalation_recipients': [],
                'last_patient_event_id': None,
                'resolution': None,
                'created_at': params[5],
                'updated_at': params[5],
            })
            return 'INSERT 0 1'
        if 'update night_alarm_state set status' in q:
            alarm_id = params[0]
            for row in self.pool.tables['night_alarm_state']:
                if row['id'] == alarm_id:
                    row['status'] = params[1]
                    # generic timestamp handling
                    if 'warning_sent_at' in q:
                        row['warning_sent_at'] = params[2]
                        row['warning_recipients'] = params[3]
                    elif 'expired_at' in q:
                        row['expired_at'] = params[2]
                    elif 'alarmed_at' in q:
                        row['alarmed_at'] = params[2]
                        row['alarm_recipients'] = params[3]
                    elif 'escalated_at' in q:
                        row['escalated_at'] = params[2]
                        row['escalation_recipients'] = params[3]
                    elif 'resolved_at' in q:
                        row['resolved_at'] = params[1] if isinstance(params[1], datetime) else params[2]
                    row['updated_at'] = params[2] if len(params) > 2 and isinstance(params[2], datetime) else row['updated_at']
                    if 'resolution = $3' in q:
                        row['status'] = 'resolved'
                        row['resolved_at'] = params[1]
                        row['resolution'] = params[2]
                        row['last_patient_event_id'] = params[3]
                    return 'UPDATE 1'
            return 'UPDATE 0'
        if 'insert into notification_log' in q:
            self.pool.tables['notification_log'].append({'id': params[0], 'patient_id': params[1], 'notification_type': params[2], 'channel': params[3], 'recipient_id': params[4], 'recipient_address': params[5], 'message_text': params[6]})
            return 'INSERT 0 1'
        return 'OK'


@pytest.fixture
def setup_engine():
    now = datetime(2026, 4, 12, 0, 0, tzinfo=timezone.utc)
    pool = MockPool()
    patient_id = str(uuid.uuid4())
    course_id = str(uuid.uuid4())
    pool.tables['coverage_courses'].append({
        'id': course_id,
        'patient_id': patient_id,
        'expected_end_at': now + timedelta(minutes=30),
        'status': 'active',
        'trigger_type': 'cornstarch',
        'is_bedtime_dose': True,
    })
    pool.tables['caregivers'].extend([
        {'id': str(uuid.uuid4()), 'patient_id': patient_id, 'name': 'A', 'telegram_id': '111', 'escalation_order': 1, 'notify_warning': True, 'notify_alarm': True, 'notify_escalation': True},
        {'id': str(uuid.uuid4()), 'patient_id': patient_id, 'name': 'B', 'telegram_id': '222', 'escalation_order': 2, 'notify_warning': True, 'notify_alarm': True, 'notify_escalation': True},
    ])
    clock = FrozenClock(now)
    notifications = InMemoryNotificationService()
    engine = CoverageAlarmEngine(pool, notifications, clock)
    return engine, pool, notifications, clock, patient_id, course_id


@pytest.mark.asyncio
async def test_alarm_lifecycle_transitions(setup_engine):
    engine, pool, notifications, clock, patient_id, course_id = setup_engine
    alarm_id = await engine.ensure_alarm_for_course(course_id)
    assert alarm_id

    clock.set(clock.now() + timedelta(minutes=15))
    summary = await engine.tick()
    assert summary['warnings'] == 1

    clock.set(clock.now() + timedelta(minutes=15))
    summary = await engine.tick()
    assert summary['expired'] == 1
    assert summary['alarmed'] == 1

    clock.set(clock.now() + timedelta(minutes=5))
    summary = await engine.tick()
    assert summary['escalated'] == 1

    alarm = await engine.get_active_alarm(patient_id)
    assert alarm['status'] == AlarmStatus.ESCALATED.value
    assert len(notifications.sent) == 12  # 2 caregivers x telegram+push x 3 stages


@pytest.mark.asyncio
async def test_resolution_by_patient_event(setup_engine):
    engine, _, _, clock, patient_id, course_id = setup_engine
    await engine.ensure_alarm_for_course(course_id)

    clock.set(clock.now() + timedelta(minutes=16))
    await engine.tick()
    resolved = await engine.resolve_by_event(patient_id, 'meal', 'evt-1')
    assert resolved == 1

    alarm = await engine.get_active_alarm(patient_id)
    assert alarm['status'] == 'resolved'
    assert alarm['resolution'] == 'patient_logged'
