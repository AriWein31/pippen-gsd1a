# Sprint 01: Foundation

**Sprint Duration:** Weeks 1-4 (April 12 - May 9, 2026)  
**Goal:** Core data entry, coverage tracking, basic night alarms  
**Status:** 🟢 Started

---

## Week 1: Data Models & Event Store (April 12-18)

### Assigned To: Pituach (Backend Lead)

### Tasks

#### Task 1.1: PostgreSQL Database Schema
**Estimated:** 8 hours  
**Priority:** 🔴 Critical  
**Deliverable:** SQL migration files in `src/backend/db/migrations/`

Create tables:
- [x] `patients` — Patient identity and metadata
- [x] `caregivers` — Emergency contacts and escalation chain
- [x] `care_team_members` — Clinical team
- [x] `events` — Unified event store (polymorphic JSONB)
- [x] `coverage_courses` — The core timing model
- [x] `patient_patterns` — Learned patterns
- [x] `patient_baselines` — Computed normals
- [x] `research_sources` — Tracked research feeds
- [x] `research_claims` — Extracted claims with embeddings
- [x] `tracked_trials` — Clinical trial monitoring
- [x] `recommendations` — Generated actions
- [x] `open_questions` — Active hypotheses
- [x] `daily_briefs` — Intelligence snapshots
- [x] `notification_log` — Alert history
- [x] `night_alarm_state` — Alarm state machine

Reference: `/docs/architecture-v2.md` Section 4 (Core Data Models)

**Status: ✅ COMPLETE** (2026-04-11)

#### Task 1.2: Event Store Implementation
**Estimated:** 10 hours  
**Priority:** 🔴 Critical  
**Deliverable:** `src/backend/events/store.py`

Implement:
- [x] `append_event(patient_id, event_type, payload, source_type)` → returns event_id
- [x] `get_events(patient_id, since, event_types[])` → returns event stream
- [x] `get_timeline(patient_id, start, end)` → returns ordered events
- [x] Event validation (schema per event_type)
- [x] Immutable event guarantee (no updates, only amends)

Key requirement: All events are append-only. No UPDATE or DELETE on events table.

**Status: ✅ COMPLETE** (2026-04-11)

#### Task 1.3: Patient & Caregiver API
**Estimated:** 4 hours  
**Priority:** 🟡 High  
**Deliverable:** `src/backend/api/patients.py`

Endpoints:
- [x] `POST /patients` — Create patient
- [x] `GET /patients/{id}` — Get patient
- [x] `PUT /patients/{id}` — Update patient
- [x] `POST /patients/{id}/caregivers` — Add caregiver
- [x] `GET /patients/{id}/caregivers` — List caregivers
- [x] `DELETE /caregivers/{id}` — Remove caregiver

**Status: ✅ COMPLETE** (2026-04-11)

#### Task 1.4: Integration Tests
**Estimated:** 6 hours  
**Priority:** 🔴 Critical  
**Deliverable:** `tests/integration/test_events.py`

Write tests for:
- [x] Event append and retrieval
- [x] Timeline reconstruction
- [x] Event immutability (no updates)
- [x] Concurrent event appends
- [x] Event payload validation

**Coverage target:** 100% on data layer

**Status: ✅ COMPLETE** (2026-04-11)

### Definition of Done (Week 1)
- [ ] All migrations run successfully on fresh database
- [ ] `pytest tests/integration/` passes
- [ ] API endpoints return correct data
- [ ] No critical or high-severity issues
- [ ] Ezra (GPT-5.4) code review passed

---

## Week 2: Coverage Course Engine (April 19-25)

### Assigned To: Pituach (Backend Lead)

### Tasks

#### Task 2.1: Coverage Course State Machine
**Estimated:** 10 hours  
**Priority:** 🔴 Critical  
**Deliverable:** `src/backend/courses/engine.py`

Implement state machine:
```
active → warning_sent → expired → alarmed → escalated
   ↓           ↓           ↓
superseded  closed     closed
```

Methods:
- [ ] `start_course(patient_id, trigger_event_id, trigger_type, expected_duration)`
- [ ] `get_active_course(patient_id)` → returns current course or null
- [ ] `get_course_chain(patient_id, start, end)` → returns linked courses
- [ ] `calculate_gap(previous_course, new_course)` → returns gap in minutes

#### Task 2.2: Course Chain Linking
**Estimated:** 6 hours  
**Priority:** 🟡 High  
**Deliverable:** `src/backend/courses/linking.py`

Implement:
- [ ] Automatic linking of consecutive courses
- [ ] Gap detection (coverage gaps between courses)
- [ ] Overlap detection (double coverage)
- [ ] Chain integrity validation

#### Task 2.3: Manual Entry APIs
**Estimated:** 8 hours  
**Priority:** 🔴 Critical  
**Deliverable:** `src/backend/api/entries.py`

Endpoints:
- [ ] `POST /patients/{id}/glucose` — Log glucose reading
  - Payload: `{value_mg_dl, reading_type, context, occurred_at}`
  - Returns: event_id

- [ ] `POST /patients/{id}/cornstarch` — Log cornstarch dose
  - Payload: `{grams, brand, is_bedtime_dose, occurred_at}`
  - Side effect: Creates coverage_course with 5.15h default duration
  - Returns: event_id, course_id

- [ ] `POST /patients/{id}/meals` — Log meal
  - Payload: `{meal_type, description, contains_cornstarch, occurred_at}`
  - Side effect: Creates coverage_course with 2h default duration (if not cornstarch)
  - Returns: event_id, course_id

- [ ] `POST /patients/{id}/symptoms` — Log symptom
  - Payload: `{symptom_type, severity, context, occurred_at}`
  - Returns: event_id

#### Task 2.4: End-to-End Test
**Estimated:** 4 hours  
**Priority:** 🟡 High  
**Deliverable:** `tests/e2e/test_coverage_flow.py`

Test scenario:
1. Patient logs cornstarch at 9:00 PM
2. System creates 5.15h course (expires ~2:09 AM)
3. Verify course is active
4. Patient logs next cornstarch at 2:00 AM
5. Verify chain linking
6. Verify gap detection (2:00 AM start vs 2:09 AM expected end = 9 min gap)

### Definition of Done (Week 2)
- [ ] Course tracking works for 5.15h cornstarch
- [ ] Course tracking works for 2h meals
- [ ] Chain linking handles overlapping courses
- [ ] E2E test passes
- [ ] API documentation in `docs/api/endpoints.md`

---

## Week 3: Mobile App Shell (April 26 - May 2)

### Assigned To: [To be recruited] Mobile Lead

**Note:** Recruit mobile developer agent before Week 3 starts.

### Tasks

#### Task 3.1: React Native / PWA Setup
**Estimated:** 8 hours  
**Priority:** 🟡 High  
**Deliverable:** `src/mobile/` project scaffold

Setup:
- [ ] React Native project with TypeScript
- [ ] iOS and Android build configs
- [ ] Development environment (Metro, debugging)
- [ ] Basic app structure

#### Task 3.2: Navigation
**Estimated:** 4 hours  
**Priority:** 🟡 High  
**Deliverable:** `src/mobile/navigation/`

Implement:
- [ ] Bottom tab navigation (5 tabs)
- [ ] Stack navigation for screens
- [ ] Tab bar styling per design system
- [ ] Active/inactive states

#### Task 3.3: Offline-First Storage
**Estimated:** 8 hours  
**Priority:** 🔴 Critical  
**Deliverable:** `src/mobile/storage/`

Implement:
- [ ] SQLite local database
- [ ] Queue for pending syncs
- [ ] Conflict resolution strategy
- [ ] Background sync when online

#### Task 3.4: Entry Forms
**Estimated:** 10 hours  
**Priority:** 🔴 Critical  
**Deliverable:** `src/mobile/components/forms/`

Forms:
- [ ] Glucose entry (numeric, context picker)
- [ ] Cornstarch entry (grams, bedtime toggle)
- [ ] Meal entry (type picker, description)
- [ ] Symptom entry (type picker, severity)

Requirements:
- Works offline
- Validated inputs
- Quick entry (minimal taps)
- Matches design system

### Definition of Done (Week 3)
- [ ] App installs on iPhone
- [ ] All 5 tabs navigateable
- [ ] Entry forms work offline
- [ ] Data syncs when online
- [ ] UI matches design spec

---

## Week 4: Night Alarm System (May 3-9) ⭐ CRITICAL

### Assigned To: Pituach (Backend Lead)

**⚠️ This is life-safety critical code. 100% test coverage required.**

### Tasks

#### Task 4.1: Alarm Daemon (Dedicated HA Process)
**Estimated:** 12 hours  
**Priority:** 🔴 CRITICAL  
**Deliverable:** `src/backend/alarm/daemon.py`

Requirements:
- [ ] Separate process from API server
- [ ] 60-second tick loop (checks all active courses)
- [ ] High-availability mode (auto-restart on crash)
- [ ] Heartbeat endpoint for external monitoring
- [ ] Graceful shutdown handling
- [ ] Deterministic logic (no randomness, no ML)

Algorithm per tick:
```python
for each active course:
    if course.expected_end_at - now <= warning_threshold (15 min):
        if not course.warning_sent:
            send_warning(patient_id, course)
            mark course.warning_sent = true
    
    if now >= course.expected_end_at:
        if not course.expired:
            mark course.status = 'expired'
    
    if course.status == 'expired':
        if time_since_expiry >= alarm_delay (10 min):
            if not patient_logged_meal_since_expiry:
                trigger_alarm(patient_id, course)
```

#### Task 4.2: State Machine Implementation
**Estimated:** 8 hours  
**Priority:** 🔴 CRITICAL  
**Deliverable:** `src/backend/alarm/state.py`

States: `active` → `warning_sent` → `expired` → `alarmed` → `escalated`

Implement:
- [ ] State transitions with validation
- [ ] Transition logging (audit trail)
- [ ] State recovery on daemon restart
- [ ] Manual state override (for false alarms)

#### Task 4.3: Telegram Integration
**Estimated:** 6 hours  
**Priority:** 🔴 CRITICAL  
**Deliverable:** `src/backend/notifications/telegram.py`

Implement:
- [ ] Telegram Bot API client
- [ ] Message templates for each state
- [ ] Escalation chain logic
- [ ] Acknowledgment handling

Messages:
- Warning: "Coverage expires in 15 minutes. Please log your next dose."
- Alarm: "🚨 COVERAGE EXPIRED — No meal logged. Check glucose now."
- Escalation: "🚨 PATIENT {name} — Coverage expired, no response. Escalating to {contact}."

#### Task 4.4: Push Notifications
**Estimated:** 6 hours  
**Priority:** 🟡 High  
**Deliverable:** `src/backend/notifications/push.py`

Implement:
- [ ] APNs (iOS) integration
- [ ] FCM (Android) integration
- [ ] Push certificate management
- [ ] Notification payload formatting

#### Task 4.5: Safety Audit
**Estimated:** 4 hours  
**Priority:** 🔴 CRITICAL  
**Deliverable:** `docs/audits/safety-week4.md`

Review by Ezra (GPT-5.4 Codex):
- [ ] All alarm logic reviewed
- [ ] No race conditions
- [ ] No infinite loops
- [ ] Graceful error handling
- [ ] Audit trail complete
- [ ] Test coverage 100%

### Definition of Done (Week 4)
- [ ] 100% test coverage on alarm logic
- [ ] All state transitions tested
- [ ] Escalation chain tested end-to-end
- [ ] Safety audit passed
- [ ] No critical or high-severity issues
- [ ] Daemon runs continuously without errors

---

## Sprint Review Criteria

End of Sprint 01 (Week 4), the system must:
1. Allow glucose, cornstarch, meal, symptom entry (manual)
2. Track coverage courses with 5.15h/2h defaults
3. Send warnings before coverage expires
4. Trigger alarms if no meal logged
5. Escalate to emergency contacts
6. Work offline on mobile, sync when online
7. Pass all safety audits

---

**Sprint Start Date:** 2026-04-12  
**Sprint End Date:** 2026-05-09  
**Sprint Lead:** Ezra (Project Management)  
**Backend Lead:** Pituach  
**Mobile Lead:** [TBD]
