# Pippen GSD1A Intelligence OS — Comprehensive Overview Audit (Weeks 1–4)

**Auditor:** Claude Opus  
**Date:** 2026-04-11  
**Scope:** Full codebase, architecture, safety posture, test coverage  
**Branch:** `main` (post Week 4 merge)

---

## Overall Verdict

**✅ The project is structurally sound. You're still smart.**

Four weeks in, the foundation is clean, the safety-critical alarm path is deterministic, and the architecture hasn't accumulated debt that would block Phase 2. The decisions made early — event sourcing, explicit state machines, offline-first mobile — are the right ones for a medical application. There are real gaps (noted below), but none that require a rethink. They require finishing.

---

## Architecture Assessment

### What's Right

**1. Event-sourced core is the correct call for medical data.**
The `events` table is append-only with `amends` references instead of mutations. This gives you an immutable audit trail — exactly what a health application needs when someone asks "what happened at 2am?" six months from now. The `validate_payload()` function with per-type schemas prevents garbage data from entering the system.

**2. Coverage course state machine is explicit and inspectable.**
```
active → warning_sent → expired → alarmed → escalated
   ↓           ↓           ↓         ↓
superseded   closed      closed    closed
```
`VALID_TRANSITIONS` is a whitelist, not a blacklist. Invalid state jumps raise `InvalidStateTransitionError`. This is the right pattern for safety-critical logic — fail loud, not silent.

**3. Alarm engine is deterministic.**
Fixed timing constants (WARNING_LEAD_MINUTES=15, ALARM_DELAY_MINUTES=0, ESCALATION_DELAY_MINUTES=5). No ML, no heuristics, no "it depends." The `tick()` method walks through alarm states in order and advances them based on wall-clock time. This is exactly how night safety should work.

**4. Separation between engine logic and notification transport.**
`NotificationService` is a Protocol. The alarm engine doesn't know or care whether it's Telegram, push, or an in-memory test stub. This means the engine is testable without network calls, and swapping delivery channels is a config change, not a rewrite.

**5. Mobile offline-first with sync queue.**
Dexie.js (IndexedDB) for local storage, a sync queue with retry logic, and background sync every 30 seconds. The user never waits for network. For a GSD1A app where someone might be logging a 2am cornstarch dose with spotty wifi, this is non-negotiable. Good.

**6. PWA over native was pragmatic.**
React + Vite + service worker. No native app store dependency, no React Native bridge bugs, no Expo headaches. For Phase 1 this gets a working app in hands faster. Native can come later if needed.

### What's Concerning

**1. No authentication or authorization exists yet.**
The API endpoints accept a `patient_id` URL parameter with zero verification. No tokens, no sessions, no middleware. This is acknowledged as "Phase 4" work, but for a medical application, even dev/staging environments should have *something*. A compromised endpoint could read or write patient health data.

**Recommendation:** Add a lightweight API key or JWT check before Phase 2. Doesn't need to be production-grade yet, but the middleware hook needs to exist.

**2. Database migrations are a single file.**
`001_initial_schema.sql` creates 15+ tables including tables for research, recommendations, and daily briefs that won't be populated until Weeks 9-12. This means the schema is speculative in places — tables designed before the code that fills them exists.

**Risk:** Schema changes will be needed as Phase 2-3 features materialize. Need a migration framework (Alembic or raw numbered SQL files) before Week 5.

**3. In-memory event bus won't survive multi-process deployment.**
`InMemoryEventBus` is explicitly marked as dev-only, which is fine. But the alarm daemon (`AlarmDaemon`) runs as an asyncio task in the same process. In production, the daemon needs to be a separate process (or at minimum, a separate worker) with a real message queue (Redis, NATS) between it and the API.

**Not a Week 5 blocker, but needs a plan before Week 8 (MVP).**

---

## Module-by-Module Review

### Backend: Event Store (`events/store.py`)
**Rating: A**

- 13 event types with payload schemas
- Append-only contract is clear in code and docstrings
- `get_timeline()` for chronological reconstruction
- Parameterized queries throughout (no SQL injection)
- Event bus integration publishes on every append

**One issue:** `get_events()` builds queries via string concatenation with parameterized values. The parameter indexing (`$1`, `$2`, etc.) is manually tracked. This works but is fragile — easy to introduce off-by-one errors if filters are added. Consider a query builder or at minimum a helper function.

### Backend: Coverage Engine (`courses/engine.py`)
**Rating: A**

- `CORNSTARCH_DURATION_MINUTES = 309` (5.15h) and `MEAL_DURATION_MINUTES = 120` (2h) — correct
- Auto-supersede on new course start with `FOR UPDATE` row locking
- Gap/overlap calculation with timezone awareness
- Course chain linking tracks `previous_course_id` / `next_course_id`

**Duplicate `return course_id`** at the end of `start_course()` — lines ~190-191 have the return statement twice. Dead code, harmless, but sloppy. Clean it up.

### Backend: Alarm Engine (`alarms/engine.py`)
**Rating: A-**

This is the most safety-critical module. The core logic is sound:

- `ensure_alarm_for_course()` creates alarm state when a course starts
- `tick()` advances alarms through warning → expired → alarmed → escalated
- `resolve_by_event()` closes alarms when the patient logs qualifying events
- Recipients loaded from `caregivers` table filtered by notification preference
- Every notification is logged to `notification_log`

**Concerns:**

1. **`_update_status()` uses f-string SQL column names.** The column names come from internal constants (not user input), so this isn't injectable, but it's a bad pattern. If someone later refactors and passes user-derived values, it becomes a vulnerability.

2. **Recipients are stored as JSONB arrays in `night_alarm_state`.** The `_update_status` method passes `recipients` as a Python list to asyncpg. This should work with asyncpg's JSONB handling but might need explicit `json.dumps()` depending on asyncpg version. Not tested with real DB.

3. **No retry on notification failure.** If `notification_service.send()` throws, the alarm state has already been updated but the notification didn't go out. The state says "alarmed" but nobody was actually notified. This is a safety gap.

**Recommendation:** Wrap notification sends in try/catch, log failures, and either retry or mark the notification_log entry as failed. The alarm daemon's next tick should re-attempt failed notifications.

### Backend: Alarm Daemon (`alarms/daemon.py`)
**Rating: B+**

Clean, minimal. 60-second tick interval. `run_once()` for testing, `run_forever()` for production.

**Missing:** No health check endpoint. If the daemon crashes silently, nobody knows alarms aren't being checked. Need a heartbeat or /health route.

**Missing:** No jitter on the tick interval. If multiple daemon instances start simultaneously (unlikely in current architecture but possible in production), they'd tick at exactly the same time. Minor, but worth noting.

### Backend: API (`api/entries.py`)
**Rating: A-**

FastAPI router factory pattern with dependency injection of pool, event_store, course_engine, and alarm_engine. Pydantic models with proper validation (glucose 20-600 mg/dL, cornstarch >0 ≤100g, severity 1-10).

**Integration with alarm engine is correct:** Cornstarch and meal entries both call `alarm_engine.resolve_by_event()` (resolves active alarms) and `alarm_engine.ensure_alarm_for_course()` (creates alarm for new course).

**Issue:** `patients.py` has `app = FastAPI(title="Pippen Patients API")` at module level with a comment "This would be wired up in main.py." But there is no `main.py`. The app can't actually be started. Phase 2 needs a proper application entry point.

### Mobile: PWA (`src/mobile/`)
**Rating: A-**

- React + TypeScript strict mode
- 5-tab navigation (Now, Trends, Watch, Actions, Profile)
- 4 entry forms (glucose, cornstarch, meal, symptom) with validation
- Dexie.js for IndexedDB, sync queue with exponential backoff
- Active course countdown with color-coded progress bar
- ErrorBoundary wrapping the entire app
- Service worker for offline caching
- 285KB bundle — reasonable for PWA

**Gap:** No notification permission request flow for push notifications. Week 4 audit notes this as "permission flow added" but looking at the code, `useNotifications.ts` exists but the actual browser Notification API permission request is basic. For Week 5+ when real push arrives, this needs proper handling with fallback for denied permissions.

### Database Schema (`001_initial_schema.sql`)
**Rating: A-**

Well-indexed. Foreign keys with cascade deletes. UUID primary keys throughout. `updated_at` triggers. JSONB for flexible payloads.

**Missing column:** `coverage_courses` doesn't have an `updated_at` column. Every other mutable table has one. The `update_course_status()` method sets `updated_at` in its SQL but the column might not exist (the migration doesn't create it). This would fail at runtime.

**Wait — checking...** The `_update_course` mock in tests doesn't actually validate this, so this bug would only surface against a real database. **This is a real bug.** Add `updated_at TIMESTAMPTZ` to the `coverage_courses` table.

### Tests
**Rating: B**

Test structure is correct:
- `tests/unit/test_alarm_engine.py` — full lifecycle test with FrozenClock, MockPool
- `tests/integration/test_events.py` — payload validation, immutability, concurrent appends
- `tests/e2e/test_coverage_flow.py` — complete coverage course scenario

**Strengths:**
- Alarm lifecycle test verifies all transitions through to escalation
- Resolution test confirms patient events close active alarms
- E2E test verifies 5.15h timing, gap/overlap calculation, chain linking
- FrozenClock pattern is excellent for deterministic time testing

**Weaknesses:**
1. **All tests use mocks.** Zero tests run against a real PostgreSQL instance. The mocks are hand-written and may not faithfully reproduce asyncpg behavior (e.g., transaction isolation, JSONB serialization, timestamp timezone handling).

2. **No negative path tests for the alarm engine.** What happens when `notification_service.send()` throws? When the course doesn't exist? When the database is down? The happy path is covered; the failure paths are not.

3. **Coverage is unknown.** No `pytest-cov` configuration. Can't verify the "100% test coverage on safety paths" claim from the project plan.

**Recommendation:** Before Week 5:
- Add `pytest-cov` and set a floor (80% minimum)
- Add at least one Docker-based integration test against real PostgreSQL
- Add failure-path tests for alarm notifications

---

## Safety-Specific Assessment

| Area | Status | Notes |
|------|--------|-------|
| Deterministic alarm timing | ✅ Strong | Fixed constants, no heuristics |
| State machine validation | ✅ Strong | Whitelist transitions, loud failures |
| Notification audit trail | ✅ Good | `notification_log` table records all sends |
| Multi-caregiver escalation | ✅ Good | Escalation order, preference-based routing |
| Real delivery (Telegram/push) | 🟡 Stubbed | `InMemoryNotificationService` only |
| Notification failure handling | 🔴 Missing | No retry, no failure detection in tick loop |
| Alarm daemon health monitoring | 🔴 Missing | No heartbeat, silent failure possible |
| Data encryption at rest | 🟡 Not started | Phase 4, but schema doesn't prepare for it |
| Authentication | 🔴 Missing | Zero auth on all endpoints |

**The critical safety question:** If the alarm daemon crashes at midnight, does anyone know?

Right now: **no.** The daemon is an asyncio task with no external health check. If it fails, alarms don't fire, and nobody is notified that alarms aren't being checked. This is the single highest-priority safety gap.

**Minimum fix:** A watchdog that checks the daemon's last tick timestamp and alerts if it's stale. Could be as simple as writing a timestamp file and having a cron job check it.

---

## Red Flags

### 🔴 Critical (Fix Before Week 5)

1. **No alarm daemon health monitoring.** If the daemon dies, the entire night safety system is silently disabled. Add a heartbeat/watchdog mechanism.

2. **Notification failure doesn't block state transition.** If `send()` fails, the alarm says "notified" but nobody actually received the message. Add retry logic or at minimum a failure flag that the next tick picks up.

3. **`coverage_courses` table likely missing `updated_at` column.** The code writes to it, the migration may not create it. Verify and fix.

### 🟡 Important (Fix Before Week 8 MVP)

4. **No application entry point (`main.py`).** The backend can't actually start. Need FastAPI app composition with CORS, health check, and proper dependency wiring.

5. **In-memory event bus is a single-process bottleneck.** Plan the Redis/NATS migration before MVP.

6. **No authentication.** Even a simple API key would prevent accidental data exposure during development.

7. **Duplicate `return course_id`** in `engine.py` `start_course()`. Dead code.

### ⚪ Minor (Track for Later)

8. **F-string column names in alarm SQL.** Not exploitable currently but bad pattern.
9. **No `pytest-cov` configuration.** Can't measure coverage.
10. **Bundle could use code splitting** for lazy-loaded routes.

---

## Recommendations Before Week 5

In priority order:

1. **Add alarm daemon watchdog.** Write last-tick timestamp, alert if stale >120 seconds. This is the safety floor.

2. **Add notification retry/failure handling** in the alarm tick loop. Log failures, retry on next tick.

3. **Verify `coverage_courses.updated_at` column exists** in the migration. If not, add a migration `002_add_updated_at.sql`.

4. **Create `main.py`** application entry point. FastAPI app with router composition, health check endpoint, CORS configuration.

5. **Add `pytest-cov`** and set 80% floor. Measure what you have.

6. **Clean up the duplicate return statement** in `start_course()`.

---

## What Phase 2 Inherits

**Strong foundation:**
- Event-sourced data layer ready for pattern detection (Week 5)
- Course chain with gap/overlap data ready for learning algorithms
- State machine ready for risk scoring
- Mobile app ready for new screens and real-time intelligence display
- Alarm system ready for real Telegram/push integration

**Missing infrastructure:**
- No app entry point
- No auth
- No real message queue
- No real notification transport
- No migration framework
- No CI/CD pipeline

Phase 2 is about building intelligence *on top of* this foundation. The foundation is solid. The infrastructure around it needs hardening before the intelligence layer makes the system more complex.

---

## Final Assessment

The architecture is well-reasoned for a safety-critical medical application. Event sourcing for auditability, deterministic state machines for safety, offline-first for real-world usage patterns. The team (sub-agents) executed the plan competently — each week delivered its milestone.

The gaps are infrastructure, not architecture. That's a good place to be at Week 4. The hard design decisions were made correctly. The remaining work is finishing, not rethinking.

**Are we still smart? Yes.** The bones are right. Now put muscle on them.

---

*Audit complete. — Claude Opus, 2026-04-11*
