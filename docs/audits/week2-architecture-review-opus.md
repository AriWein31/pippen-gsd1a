# Week 2 Architecture Review — Technical Architect (Claude Opus)

**Review Date:** 2026-04-11  
**Reviewer:** Technical Architect (Claude Opus)  
**Subject:** Week 2 Deliverables — Coverage Course Engine, Chain Linking, Entry APIs, E2E Tests  
**Cross-reference:** [Week 1 Architecture Review](./week1-architecture-review-opus.md)

---

## Preamble

The `architecture-v2.md` document remains absent from the repository. This was flagged as Critical finding C4 in the Week 1 review. It still hasn't been committed. I'm reviewing against the sprint plan (`sprints/sprint-01-foundation.md`), the Week 1 codebase patterns, and architectural intent as documented.

**Recurring action:** Commit the architecture spec. Two weeks of building against an unversioned spec is two weeks too many.

---

## 1. Alignment Assessment

### What Week 2 Called For

Per sprint plan, Week 2 deliverables:
- Coverage Course State Machine (`engine.py`)
- Course Chain Linking (`linking.py`)
- Manual Entry APIs (`entries.py`)
- End-to-End Coverage Flow Test (`test_coverage_flow.py`)

### What Was Delivered

| Deliverable | Status | Notes |
|-------------|--------|-------|
| State machine engine | ✅ Delivered | Full state machine with transitions, validation, event publishing |
| Chain linking | ✅ Delivered | Gap/overlap detection, chain validation, summary statistics |
| Entry APIs | ✅ Delivered | Glucose, cornstarch, meal, symptom endpoints + course queries |
| E2E tests | ⚠️ Delivered with issues | Coverage flow tested, but mock infrastructure is fragile and one test has a known broken assertion |

### Alignment Verdict: **Strong delivery, with real bugs that need fixing**

The core architectural intent — a state machine driving coverage courses, with chain linking and event-driven side effects — is correctly implemented. The event bus recommended in Week 1's review was built and integrated. The API layer properly triggers course creation from entry endpoints. This is solid Week 2 work.

But there are bugs. Not design disagreements — actual bugs in the code that will produce incorrect behavior in production. Details below.

---

## 2. Detailed File Reviews

### 2.1 Coverage Course Engine (`engine.py`)

**The good:**

1. **State machine is clean and explicit.** `VALID_TRANSITIONS` as a dictionary of sets is the right pattern — declarative, easy to audit, impossible to accidentally bypass. The `validate_transition()` function is a pure function. This is exactly what was recommended in Week 1 ("establish the state machine implementation pattern").

2. **`CourseStatus` as `str, Enum`.** Dual inheritance means the enum values serialize naturally to strings while still providing type safety. Smart choice for a system that stores status in PostgreSQL text columns.

3. **`FOR UPDATE` locking on status transitions.** `update_course_status` acquires a row-level lock before checking the current state. This prevents race conditions where two concurrent transitions could both see `active` and both succeed. Critical for a medical system. Well done.

4. **Automatic supersession in `start_course`.** When a new course starts, the previous active course is automatically superseded. This correctly models the real-world scenario: taking a new cornstarch dose doesn't invalidate the old one retroactively — it supersedes it going forward.

5. **Event publishing on every state change.** Course started, superseded, warning, expired, closed — all published to the event bus. This enables the alarm daemon (Week 4) to react without polling. The Week 1 gap is filled.

6. **Timing constants are correct.** `CORNSTARCH_DURATION_MINUTES = int(5.15 * 60) = 309` ✅. `MEAL_DURATION_MINUTES = 2 * 60 = 120` ✅.

**Bugs found:**

### 🔴 BUG: `superseded_by` field in event publishes the WRONG course ID

```python
# Line ~113-120 in start_course()
previous_course_id = previous_course["id"]

await bus.publish(
    EventTypes.COVERAGE_COURSE_CLOSED,
    {
        "course_id": str(previous_course["id"]),
        "patient_id": patient_id,
        "reason": "superseded",
        "superseded_by": str(previous_course_id),  # ← BUG
    }
)
```

`previous_course_id` is set to `previous_course["id"]` — the course being superseded. So `superseded_by` points to itself. It should point to the NEW course that supersedes it, but `course_id` (the new UUID) is generated *after* this event is published.

**Fix:** Move the `course_id = str(uuid.uuid4())` generation above the supersession block, then use it:
```python
course_id = str(uuid.uuid4())
# ... supersede previous ...
"superseded_by": course_id,
```

**Severity:** 🔴 High — any downstream consumer of this event (dashboards, audit logs, alarm system) will get incorrect chain data.

### 🟡 ISSUE: `_get_event_type_for_status` is incomplete

```python
def _get_event_type_for_status(self, status: CourseStatus) -> str:
    mapping = {
        CourseStatus.WARNING_SENT: EventTypes.COVERAGE_COURSE_WARNING,
        CourseStatus.EXPIRED: EventTypes.COVERAGE_COURSE_EXPIRED,
        CourseStatus.CLOSED: EventTypes.COVERAGE_COURSE_CLOSED,
    }
    return mapping.get(status, EventTypes.COVERAGE_COURSE_CLOSED)
```

`ALARMED` and `ESCALATED` transitions fall through to `COVERAGE_COURSE_CLOSED`. This means when the alarm system (Week 4) escalates a course, it publishes a "closed" event instead of an "alarm triggered" or "alarm escalated" event. The `EventTypes` class already defines `ALARM_TRIGGERED` and `ALARM_ESCALATED` — they should be mapped here.

**Fix:**
```python
mapping = {
    CourseStatus.WARNING_SENT: EventTypes.COVERAGE_COURSE_WARNING,
    CourseStatus.EXPIRED: EventTypes.COVERAGE_COURSE_EXPIRED,
    CourseStatus.ALARMED: EventTypes.ALARM_TRIGGERED,
    CourseStatus.ESCALATED: EventTypes.ALARM_ESCALATED,
    CourseStatus.CLOSED: EventTypes.COVERAGE_COURSE_CLOSED,
}
```

**Severity:** 🟡 Medium — won't bite until Week 4, but will cause incorrect event routing when the alarm daemon is built.

### 🟡 ISSUE: No `ACTIVE → CLOSED` transition

The `VALID_TRANSITIONS` dict doesn't allow `active → closed`. This means a caregiver cannot manually close an active coverage course. The only exit from `active` is through `warning_sent`, `expired`, or `superseded`.

Real-world scenario: "Oops, I logged the wrong cornstarch dose. Let me close this course and start over." Currently impossible without first superseding it with a new course.

The sprint plan notes "Manual state override (for false alarms)" as a Week 4 task, but the state machine should support it structurally now.

**Recommendation:** Add `CourseStatus.CLOSED` to `VALID_TRANSITIONS[CourseStatus.ACTIVE]`.

### 🟡 ISSUE: `start_course` doesn't compute gap/overlap

When `start_course` supersedes a previous course, it links `previous_course_id` and `next_course_id`, but never calls `calculate_gap` or writes `gap_minutes`/`overlap_minutes`. This means the denormalized fields in the database will be NULL until someone explicitly calls `CoverageCourseLinking.link_courses()`.

The entry API (`entries.py`) calls `engine.start_course()` directly — it never touches `CoverageCourseLinking`. So in practice, gap/overlap data is never populated through the normal flow.

**Fix:** Either:
- (a) Call `calculate_gap` inside `start_course` and write the result, or
- (b) Have the entry API explicitly call `linking.link_courses()` after `engine.start_course()`, or
- (c) Use a database trigger (not recommended — keep logic in application layer)

**Severity:** 🟡 Medium — gap/overlap queries will return empty results until this is wired up.

---

### 2.2 Course Chain Linking (`linking.py`)

**The good:**

1. **Clean separation from engine.** Linking is a supplementary concern, not core state management. Keeping it separate from `engine.py` is correct — the engine manages individual course lifecycles; linking manages inter-course relationships.

2. **`validate_chain` is comprehensive.** Checks bidirectional link integrity, chronological ordering, undocumented overlaps, stale active courses, and gap calculation consistency. This is exactly the kind of defensive validation a medical system needs.

3. **`get_chain_summary` provides aggregate statistics.** Total gap minutes, average gap, overlap totals — useful for patient reports and clinical dashboards.

4. **`detect_gap` and `detect_overlap` use SQL JOINs.** Rather than fetching all courses and computing in Python, the queries leverage the database. Efficient.

**Concerns:**

1. **`validate_chain` issue #2 (chronological ordering check) doesn't account for superseded courses.** It iterates all courses by `started_at` and flags overlaps between consecutive courses. But superseded courses *will* overlap with their successors — that's the whole point of supersession. The check should skip superseded courses or at least treat them differently.

2. **`link_courses` is standalone but never called in the normal flow.** As noted above, `engine.start_course` doesn't call it. The linking module exists but isn't wired into the pipeline. It's library code without integration.

3. **`CoverageCourseLinking` creates its own `CoverageCourseEngine` internally.** This is a hidden dependency — the linking module uses the engine for `calculate_gap`, but it constructs its own engine instance instead of accepting one via dependency injection. If the engine gets constructor parameters in the future, linking will silently use a default-configured engine.

---

### 2.3 Manual Entry APIs (`entries.py`)

**The good:**

1. **Uses `APIRouter`, not `FastAPI()`.** The Week 1 bug is fixed. ✅

2. **Router factory pattern with dependency injection.** `create_entries_router(pool, event_store, course_engine)` accepts optional pre-built services. This enables testing with mocks and production with real instances. Clean pattern.

3. **Pydantic models with field constraints.** `value_mg_dl: int = Field(..., ge=20, le=600)` — glucose readings are constrained to physically plausible values. `grams: float = Field(..., gt=0, le=100)` — cornstarch doses are bounded. This is exactly right for medical data entry.

4. **Cornstarch → coverage course flow is correct.** Log event → start course → return both IDs. The chain of causation is explicit in the response.

5. **Meal logic is correct.** Meals containing cornstarch don't create a separate coverage course (the cornstarch endpoint handles that). Meals without cornstarch get a 2-hour course. The response message explains why. Good UX.

**Concerns:**

### 🟡 ISSUE: No transaction wrapping for event + course creation

In `log_cornstarch`:
```python
event_id = await event_store.append_event(...)  # INSERT 1
course_id = await course_engine.start_course(...)  # INSERT 2 + UPDATE previous
```

If `start_course` fails (e.g., database error during course creation), the event is already committed. You now have an orphaned cornstarch event with no corresponding course. In a medical system, this means the patient thinks they logged a dose, but coverage tracking doesn't know about it.

**Fix:** Wrap both operations in a single database transaction:
```python
async with pool.acquire() as conn:
    async with conn.transaction():
        event_id = await event_store.append_event(..., conn=conn)
        course_id = await course_engine.start_course(..., conn=conn)
```

This requires `append_event` and `start_course` to accept an optional connection parameter. The refactor is small but important.

**Severity:** 🟡 Medium — failure is unlikely under normal operation, but the consequence (silent data inconsistency) is severe in a medical context.

### 🟡 ISSUE: Patient existence check is separate from data operations

Same pattern as Week 1's caregiver creation bug. The patient could be deleted between the existence check and the event insert. Use a single connection with a transaction, or rely on foreign key constraints to catch it.

### ⚪ NOTE: `occurred_at` defaults to UTC, but users are in specific timezones

All request models default `occurred_at` to `datetime.now(timezone.utc)`. This is correct for storage. But the API should document that clients are expected to send timezone-aware timestamps if the reading occurred in the past. A caregiver logging a 2 AM reading at 7 AM needs to send `occurred_at` with the correct value, not rely on the default.

---

### 2.4 End-to-End Tests (`test_coverage_flow.py`)

**The good:**

1. **Scenario-based testing.** The E2E test mirrors the sprint plan's scenario exactly: cornstarch at 9 PM, verify 5.15h course, second dose at 2 AM, verify chain linking and gap detection. This is readable, purposeful testing.

2. **Timing math is explicitly verified.** `assert CORNSTARCH_DURATION_MINUTES == 309` and the gap calculation `2:18 AM - 2:09 AM = 9 minutes` are tested with clear assertions.

3. **State transition tests cover the full chain.** `active → warning_sent → expired → alarmed → escalated` is tested step by step.

4. **Invalid transition test exists.** `active → alarmed` (skipping intermediate states) correctly raises `InvalidStateTransitionError`.

**Bugs found:**

### 🔴 BUG: `test_get_active_course_returns_none_when_superseded` has a broken assertion

```python
async def test_get_active_course_returns_none_when_superseded(self, ...):
    # Start first course
    course_1_id = await course_engine.start_course(...)
    # Start second course (supersedes first)
    await course_engine.start_course(...)
    
    active = await course_engine.get_active_course(patient_id)
    assert active["id"] == course_1_id  # Wait, this is the superseded one
```

The test name says "returns none when superseded" but the assertion checks that the active course IS the superseded one. The comment in the code even acknowledges this: "Wait, this is the superseded one." This test is wrong — it should assert `active["id"] != course_1_id` or `active["id"] == course_2_id`.

This likely passes only because the mock's `fetchrow` for active courses iterates `reversed(courses)` and returns the first match, which happens to be the superseded course due to the mock's simplified query matching. In a real database, this test would fail.

**Severity:** 🔴 High — a passing test that validates incorrect behavior is worse than no test at all. It creates false confidence.

### 🟡 CONCERN: Mock infrastructure is brittle and misleading

The `MockPool` / `MockConnection` implementation is ~150 lines of hand-written query parsing:
```python
if "insert into coverage_courses" in query_lower:
    return self._insert_course(query, *params)
elif "update coverage_courses" in query_lower:
    return self._update_course(query, *params)
```

This approach has fundamental problems:
- The mock must be updated every time a query changes. Forgotten updates produce silent wrong behavior.
- String matching on SQL fragments is fragile — `"set status = 'superseded'"` will break if the query formatting changes.
- The mock doesn't enforce foreign keys, unique constraints, or transaction isolation — the very things integration tests should validate.
- `fetchrow` returns `MagicMock(**course)` which behaves differently from `asyncpg.Record` (e.g., `dict(row)` works on Records but not MagicMock).

**Recommendation:** These are unit tests. Call them that. For actual E2E/integration testing, use `testcontainers-python` with a real PostgreSQL instance. The mock is acceptable for fast iteration, but it must not be the final line of defense for a medical system's core logic.

---

### 2.5 Event Bus (`bus.py`)

**The good:**

1. **Abstract base class + concrete implementation.** `EventBus` ABC defines the contract; `InMemoryEventBus` implements it. Swapping to Redis/NATS later requires only a new implementation. This was the exact pattern recommended in Week 1's review. ✅

2. **Async-safe with `asyncio.Lock`.** Subscriber modification is locked; handler invocation happens outside the lock. This prevents deadlocks while maintaining subscriber list consistency.

3. **Error isolation.** A failing handler doesn't crash the publisher or block other handlers. Errors are logged and swallowed. Correct for a non-critical notification path.

4. **`EventTypes` constants.** Centralized event type strings prevent typo-driven bugs. Coverage events, alarm events, and system events are all defined.

**Concerns:**

1. **`datetime.utcnow()` is deprecated.** Python 3.12+ deprecates `datetime.utcnow()` in favor of `datetime.now(timezone.utc)`. The engine and store use the correct form; the event bus doesn't. Minor but should be consistent.

2. **No event history/replay.** The in-memory bus is fire-and-forget. If a subscriber isn't registered when an event fires, it misses it. This is fine for Week 2 but will be a problem for the alarm daemon (Week 4), which needs to recover missed events after a restart. Document this limitation now.

3. **Global singleton via `get_event_bus()`.** Works for single-process, but won't work for multi-worker deployments (e.g., gunicorn with multiple workers). Each worker gets its own bus instance. Document the production migration path.

---

## 3. Key Questions Answered

### Q1: Does the state machine match the spec?

**Yes, with one gap.** The state machine implements:
```
active → warning_sent → expired → alarmed → escalated
   ↓           ↓           ↓
superseded  closed      closed
```

This matches the sprint plan exactly. The gap: `active → closed` is not permitted (no manual close of active courses). This is a deliberate restriction that should be reconsidered for Week 4's "manual state override" requirement.

### Q2: Is event bus integration correct?

**Yes.** Every state transition publishes to the event bus. The bus implementation follows the abstract interface recommended in Week 1. The coverage engine imports `get_event_bus()` and publishes `COVERAGE_COURSE_STARTED`, `COVERAGE_COURSE_WARNING`, `COVERAGE_COURSE_EXPIRED`, and `COVERAGE_COURSE_CLOSED` events.

Two issues: (1) the `superseded_by` field in the supersession event points to the wrong course, and (2) `ALARMED`/`ESCALATED` transitions publish `CLOSED` events instead of their proper types.

### Q3: Are there architectural concerns for Week 3+?

**Yes, three:**

1. **No transaction safety on multi-step operations.** The entry API creates events and courses in separate database calls without transactional wrapping. Week 3's mobile sync will make this worse — network retries could create duplicate events. The idempotency strategy flagged in Week 1 still isn't implemented.

2. **Linking module isn't integrated.** `CoverageCourseLinking` exists but isn't called from the normal course creation flow. Gap/overlap data will be NULL in production. Week 3's mobile dashboard can't show coverage gap analytics until this is wired up.

3. **Event bus is in-process only.** Week 4's alarm daemon is described as a "separate process." The `InMemoryEventBus` doesn't cross process boundaries. Either the alarm daemon runs in-process (different from the sprint plan) or you need Redis/NATS by Week 4.

### Q4: Is the timing logic (5.15h/2h) correctly implemented?

**Yes.** 
- `CORNSTARCH_DURATION_MINUTES = int(5.15 * 60) = 309` ✅
- `MEAL_DURATION_MINUTES = 2 * 60 = 120` ✅
- `expected_end_at = started_at + timedelta(minutes=expected_duration)` ✅
- The E2E test verifies: 9:00 PM + 309 min = 2:09 AM ✅
- Gap calculation: 2:18 AM - 2:09 AM = 9 minutes ✅

---

## 4. Risks & Concerns Summary

### 🔴 Critical (Must fix before merge)

| # | Issue | File | Impact | Fix |
|---|-------|------|--------|-----|
| C1 | `superseded_by` points to wrong course ID | `engine.py` L113-120 | Incorrect chain data in all downstream consumers | Generate `course_id` before supersession block |
| C2 | Broken test assertion passes due to mock quirk | `test_coverage_flow.py` | False confidence in active course retrieval | Fix assertion to check for course_2, not course_1 |

### 🟡 Important (Fix in Week 2 or early Week 3)

| # | Issue | File | Impact | Fix |
|---|-------|------|--------|-----|
| I1 | Event type mapping incomplete for ALARMED/ESCALATED | `engine.py` | Wrong events published in Week 4 alarm flow | Add mappings to `_get_event_type_for_status` |
| I2 | No `ACTIVE → CLOSED` transition | `engine.py` | Can't manually close active courses | Add to `VALID_TRANSITIONS` |
| I3 | Gap/overlap never computed in normal flow | `engine.py` + `entries.py` | NULL gap data in database | Integrate `calculate_gap` into `start_course` |
| I4 | No transaction wrapping on entry endpoints | `entries.py` | Orphaned events on partial failure | Wrap event + course creation in transaction |
| I5 | Mock-based E2E tests mask real behavior | `test_coverage_flow.py` | Can't verify actual DB behavior | Add real PostgreSQL tests alongside mocks |
| I6 | `datetime.utcnow()` deprecated | `bus.py` | Python 3.12+ deprecation warning | Use `datetime.now(timezone.utc)` |

### ⚪ Technical Debt (Track)

| # | Debt | When to Address |
|---|------|-----------------|
| D1 | `architecture-v2.md` still not committed | NOW |
| D2 | Event deduplication still missing (Week 1 I1) | Before Week 3 mobile sync |
| D3 | Event bus doesn't cross process boundaries | Before Week 4 alarm daemon |
| D4 | Linking module not dependency-injected | Week 3 |
| D5 | `validate_chain` doesn't handle superseded courses in overlap check | Week 3 |

---

## 5. Week 1 Follow-ups

Checking resolution of Week 1 critical findings:

| Week 1 Finding | Status | Notes |
|----------------|--------|-------|
| C1: `events_immutable` CHECK constraint | ❓ Unknown | Not visible in Week 2 code; check migration |
| C2: No event notification mechanism | ✅ Resolved | `InMemoryEventBus` implemented and integrated |
| C3: `FastAPI()` instead of `APIRouter()` | ✅ Resolved | `entries.py` uses `APIRouter` correctly |
| C4: Architecture spec not committed | ❌ Not resolved | Still missing from repo |
| I1: No event deduplication | ❌ Not resolved | Still needed before Week 3 |
| I2: Mock-based integration tests | ❌ Not resolved | Week 2 continues the pattern |

**2 of 4 critical items resolved. 0 of 2 important items resolved.** The event bus was the right priority — but the debt is accumulating.

---

## 6. Recommendations for Week 3

### Must Do

1. **Fix the two bugs (C1, C2) immediately.** The `superseded_by` bug will corrupt chain data. The broken test will mask regressions. These are 10-minute fixes with outsized impact.

2. **Wire gap/overlap computation into `start_course`.** The linking module's `calculate_gap` should be called during course creation. Without this, the chain linking feature is dead code.

3. **Add transaction safety to entry endpoints.** Refactor `EventStore.append_event` and `CoverageCourseEngine.start_course` to accept an optional `conn` parameter. Wrap the entry endpoint flows in explicit transactions.

4. **Commit the architecture spec.** Third time asking. The mobile developer joining in Week 3 will need a canonical reference. Don't make them reverse-engineer it from code.

### Should Do

5. **Add the ALARMED/ESCALATED event type mappings.** This is a 2-line fix that prevents a Week 4 headache.

6. **Add `ACTIVE → CLOSED` to valid transitions.** Manual close is a reasonable operation. Guard it with a `reason` requirement if needed.

7. **Start a real PostgreSQL test suite.** Keep the mock tests for fast feedback. Add a `tests/integration/` directory with `testcontainers` tests that validate actual database behavior. The Week 2 mock already has one test producing incorrect results — real DB tests would have caught it.

### Nice to Have

8. **Document the event bus's production migration path.** A comment in `bus.py` noting "Replace with Redis Pub/Sub for multi-process deployment" is enough.

9. **Add an event deduplication strategy.** Client-generated event IDs with UNIQUE constraint on the events table. This is Week 3 mobile's dependency.

---

## 7. Approval to Proceed

### Can Week 3 proceed on this foundation?

**Yes, conditionally.**

The coverage course engine works. The state machine is correct. The timing logic is correct. The event bus fills the Week 1 gap. The entry APIs create the right data structures. This is a functional Week 2 delivery.

**Conditions:**
1. Fix C1 (superseded_by bug) and C2 (broken test) before any Week 3 code builds on this
2. Wire gap/overlap into the normal creation flow (I3)
3. The mobile developer must not build sync logic without event deduplication (D2)

### Confidence Level

**Medium-High.** The architecture is sound. The patterns are clean. The bugs are fixable — they're implementation mistakes, not design flaws. The recurring issue is testing rigor: mock-based tests that don't validate what they claim to validate. This is a cultural problem, not a technical one. It needs to be addressed before Week 4's safety-critical alarm code.

The foundation supports what's coming. Fix the bugs, wire the gaps, and Week 3 can proceed.

---

*Review completed by Technical Architect (Claude Opus)*  
*2026-04-11*
