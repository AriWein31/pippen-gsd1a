# Week 1 Architecture Review — Technical Architect (Claude Opus)

**Review Date:** 2026-04-11  
**Reviewer:** Technical Architect (Claude Opus)  
**Subject:** Week 1 Deliverables — Foundation Data Layer  
**Cross-reference:** [Ezra's Week 1 Audit](./week1-audit-ezra.md)

---

## Preamble

The architecture-v2.md document is not present on disk at its expected path (`docs/architecture-v2.md`). This review is conducted against the architectural intent documented in the PROJECT_PLAN.md, README, and the structural commitments visible in the codebase itself. If the architecture spec was generated in a prior session but never persisted, **that's the first finding**: the canonical architecture document needs to be committed to the repository. A team building against a spec that only one agent remembers is a team building on sand.

**Action Required:** Reconstruct and commit `docs/architecture-v2.md` before Week 2 begins.

---

## 1. Alignment Assessment

### What the Architecture Called For (Week 1)

Per PROJECT_PLAN.md, Week 1 deliverables:
- PostgreSQL database schema (migration files)
- Event store implementation (append/query API)
- Patient/Caregiver models (user management API)
- Integration tests passing

### What Was Delivered

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Database schema | ✅ Delivered | 15 tables, proper migration file |
| Event store | ✅ Delivered | Append-only, typed, validated |
| Patient/Caregiver API | ✅ Delivered | CRUD + caregiver management |
| Integration tests | ⚠️ Partial | Tests exist but use mocks, not a real database |

### Alignment Verdict: **Strong, with one significant caveat**

The implementation follows the architectural intent faithfully. The event-sourced core, the coverage course model, the patient learning layer, the research tables, the night alarm state machine — all present in the schema. The code structure (`src/backend/events/`, `src/backend/api/`, `tests/integration/`) follows clean separation.

The caveat: "integration tests passing" was the milestone definition-of-done. What was delivered are unit tests with mocked database connections labeled as integration tests. That's not the same thing. More on this below.

---

## 2. Foundation Strength

### Schema Analysis (001_initial_schema.sql)

**Solid decisions:**

1. **UUID primary keys everywhere.** Correct for a distributed system that may need to sync across mobile/backend. No auto-increment collision risks.

2. **`occurred_at` vs `recorded_at` separation on events.** This is critical for a medical system where a reading might be logged minutes after it happens. The distinction enables accurate timeline reconstruction vs. audit trails. Well done.

3. **JSONB payloads with validation at the application layer.** The schema stores flexible payloads; the Python code validates structure per event type. This is the right split — schema handles storage guarantees, application handles business rules. Avoids the trap of encoding business logic in CHECK constraints that become migration nightmares.

4. **Coverage course chaining** (`previous_course_id`, `next_course_id`). Linked-list structure for course sequences enables gap/overlap detection. The `gap_minutes` and `overlap_minutes` computed fields are a smart denormalization for query performance.

5. **Night alarm state machine as a table.** Separate from events (which are immutable), the alarm state table is mutable by design — it tracks a process, not a fact. This is the correct architectural separation.

6. **Research layer included from Week 1.** Tables for `research_sources`, `research_claims`, `tracked_trials` are present even though they're Phase 3 deliverables. Pre-creating the schema is fine — it establishes the data model early and prevents future migrations from touching the core tables.

**Concerns:**

1. **The `events` table has a CHECK constraint that will fight the codebase.**
   ```sql
   CONSTRAINT events_immutable CHECK (amended_by IS NULL)
   ```
   This constraint means `amended_by` can never be non-NULL on any row. But the column exists precisely to mark events that have been superseded. The intent is clearly that when an amending event is appended, the *original* event's `amended_by` should be set to point to the new event. This CHECK constraint prevents that update. Either:
   - (a) The constraint is wrong and should be removed (if the design intends to update `amended_by` on the original), or
   - (b) The design intends `amended_by` to be populated only via the amending event's `amends` field, and `amended_by` should be a computed/derived value (query-time join, not stored).
   
   **This is a design ambiguity that must be resolved before Week 2.** If option (b), remove the `amended_by` column entirely and derive it. If option (a), remove the CHECK constraint.

2. **No partitioning strategy for the events table.** For a single patient, this is fine for years. But the schema should document the expected scale: how many patients, how many events/day, and when partitioning becomes necessary. Even a comment in the migration file helps future developers.

3. **`ON DELETE CASCADE` on events → patients.** If a patient is deleted, all their events vanish. For a medical system, this is dangerous. Events should be retained even if a patient record is deactivated. Consider:
   - Soft-delete on patients (add `deleted_at` column)
   - Change CASCADE to RESTRICT on the events table
   - This is a **Week 4 security concern** but worth flagging now.

4. **No `source_id` column documentation.** The events table has `source_id VARCHAR(255)` but no comment explaining what it references. Is it a sensor serial number? An API key? A user ID? Document it.

### Event Store Analysis (store.py)

**Solid decisions:**

1. **Strict payload validation with typed schemas.** Every event type has required/optional fields defined in `PAYLOAD_SCHEMAS`. This prevents garbage data from entering the immutable log. Once a bad event is in, it's in forever — validation at the gate is essential.

2. **Custom exception hierarchy.** `EventStoreError` → `PayloadValidationError` / `EventTypeError` / `ImmutableEventError`. Clean, specific, catchable. This is how error handling should look.

3. **`Event` dataclass with `to_dict()`.** Immutable data carrier. Not an ORM model — a value object. Right choice for event-sourced data.

4. **Async throughout.** `asyncpg` with connection pooling. No sync database calls that would block the event loop. This is the correct foundation for a system that will handle real-time sensor data.

5. **Timeline reconstruction as a first-class method.** `get_timeline()` reverses the DESC-ordered query to produce chronological output. Simple, correct.

**Concerns:**

1. **`get_events` builds SQL via string concatenation with parameterized values.** The pattern is:
   ```python
   query += f" AND occurred_at >= ${param_idx}"
   ```
   This is safe (parameterized), but fragile. As filters grow, this becomes a maintenance burden. Consider a query builder or at minimum, extract the filter-building logic into a helper. Week 2's coverage engine will need similar queries.

2. **`get_timeline` fetches up to 10,000 events then reverses in Python.** For large timelines, this is memory-intensive. A simpler approach: change the ORDER BY to ASC in the underlying query. The reversal is unnecessary overhead.

3. **No event deduplication.** If the same glucose reading is submitted twice (network retry, mobile sync), two events are created. For an append-only store, this needs an idempotency strategy:
   - Option A: Client-generated event IDs (the client generates the UUID, and the store rejects duplicates)
   - Option B: Deduplication window based on (patient_id, event_type, occurred_at, payload hash)
   
   **This must be solved before mobile sync in Week 3.**

4. **`create_event_store` hardcodes pool configuration.** `min_size=5, max_size=20` should be configurable via environment variables. This is a minor point but shows a pattern of hardcoding that should be caught early.

5. **No event publishing/notification mechanism.** The store appends and queries, but has no way to notify other components that an event was created. Week 2's coverage engine needs to react to new events (e.g., a cornstarch dose triggers a new coverage course). Options:
   - PostgreSQL NOTIFY/LISTEN
   - Application-level event bus
   - Polling (worst option)
   
   **This is a critical architectural gap for Week 2.** The coverage engine *depends* on event reactivity.

### Patient API Analysis (patients.py)

**Solid decisions:**

1. **Pydantic models for validation.** Request/response separation, field constraints, `ConfigDict(from_attributes=True)` for ORM compatibility. Modern FastAPI patterns.

2. **Partial updates via `model_dump(exclude_unset=True)`.** Only submitted fields are updated. This prevents accidental nullification of fields.

3. **Caregiver endpoints nested under patient.** `POST /patients/{id}/caregivers` is the right REST structure — caregivers belong to patients.

**Concerns:**

1. **`create_patients_router` returns a `FastAPI()` app, not an `APIRouter`.** Line:
   ```python
   router = FastAPI(prefix="/patients", tags=["patients"])
   ```
   This creates a full FastAPI application, not a router. It should be:
   ```python
   router = APIRouter(prefix="/patients", tags=["patients"])
   ```
   This is a **bug**. The prefix won't work as expected when mounted, and the OpenAPI schema will be wrong. FastAPI apps don't support prefix in the constructor the same way APIRouter does.

2. **Two separate `pool.acquire()` calls in `add_caregiver`.** The patient existence check and the caregiver insert are in separate connection acquisitions. Under concurrent load, the patient could be deleted between the check and the insert. Use a single connection with a transaction:
   ```python
   async with pool.acquire() as conn:
       async with conn.transaction():
           patient = await conn.fetchrow(...)
           if not patient: raise 404
           row = await conn.fetchrow("INSERT INTO caregivers...")
   ```

3. **`care_protocol` and `preferences` are passed as Python dicts to asyncpg.** Depending on how asyncpg handles JSONB, these may need `json.dumps()` wrapping. The event store does this correctly (`json.dumps(payload)`), but the patient API does not. This may work in some asyncpg versions and fail in others. **Consistency risk.**

4. **Delete caregiver endpoint is `DELETE /caregivers/{id}` not `DELETE /patients/{pid}/caregivers/{id}`.** This breaks the REST nesting pattern. A caregiver deletion should still be scoped under a patient for authorization purposes. The current design allows deleting any caregiver if you know its ID, regardless of which patient it belongs to.

5. **No list patients endpoint.** Only create, get-by-id, and update. The system needs `GET /patients` with pagination for any administrative interface or multi-patient dashboards.

---

## 3. Key Decisions Validation

| Decision | Spec Intent | Implementation | Verdict |
|----------|-------------|----------------|---------|
| Event sourcing (append-only) | Immutable event log | ✅ No UPDATE/DELETE methods in store | ✅ Correct |
| JSONB payloads | Flexible, validated at app layer | ✅ `PAYLOAD_SCHEMAS` with validation | ✅ Correct |
| asyncpg for PostgreSQL | Async, performant | ✅ Pool-based async | ✅ Correct |
| FastAPI for REST | Modern, typed | ✅ Pydantic models, proper status codes | ✅ Correct |
| UUID primary keys | Distributed-safe | ✅ `uuid_generate_v4()` everywhere | ✅ Correct |
| Coverage course chaining | Gap/overlap tracking | ✅ Schema supports it, not yet implemented in code | ⚠️ Schema only |
| Night alarm state machine | Mutable state tracking | ✅ Schema supports it, not yet implemented in code | ⚠️ Schema only |

**Overall:** Architectural decisions were followed. The implementation is faithful to the design intent.

---

## 4. Risks & Concerns

### 🔴 Critical (Must resolve before Week 2)

| # | Risk | Impact | Resolution |
|---|------|--------|------------|
| C1 | **`events_immutable` CHECK constraint blocks `amended_by` updates** | Amendment workflow broken | Remove constraint or remove `amended_by` column (derive via JOIN) |
| C2 | **No event notification/subscription mechanism** | Coverage engine can't react to new events | Design pub/sub before Week 2 implementation |
| C3 | **`FastAPI()` instead of `APIRouter()`** in patients.py | Mounting/routing broken in production | Fix to `APIRouter` |
| C4 | **Architecture spec not committed to repo** | Team has no canonical reference | Reconstruct and commit `architecture-v2.md` |

### 🟡 Important (Should resolve in Week 2)

| # | Risk | Impact | Resolution |
|---|------|--------|------------|
| I1 | **No event deduplication** | Duplicate events from mobile sync | Implement idempotency before Week 3 mobile work |
| I2 | **Mock-based "integration" tests** | False confidence — real DB behavior untested | Add real PostgreSQL tests (testcontainers or Docker) |
| I3 | **JSONB handling inconsistency** | Patient API doesn't `json.dumps()` dicts; event store does | Standardize JSONB serialization |
| I4 | **No transaction isolation** in caregiver creation | Race condition on concurrent requests | Wrap in transaction |
| I5 | **`ON DELETE CASCADE` on events** | Patient deletion destroys medical history | Implement soft-delete pattern |

### ⚪ Technical Debt (Track for later)

| # | Debt | Phase to Address |
|---|------|-----------------|
| D1 | No RLS (row-level security) for multi-tenant access | Phase 4 |
| D2 | No audit logging on API endpoints | Phase 4 |
| D3 | No rate limiting | Phase 4 |
| D4 | Hardcoded pool configuration | Week 2 |
| D5 | Event query builder should be extracted as filters grow | Week 2-3 |

---

## 5. Recommendations

### Carry Forward (Keep Doing)

1. **The event-sourced pattern is clean and correct.** The separation between immutable events and mutable state (alarm, courses) is exactly right. Don't let scope creep blur this boundary.

2. **Payload validation at the application layer.** This is the right place for it. The database stores; the code validates. Keep this pattern.

3. **Async-first architecture.** asyncpg + FastAPI is the right stack for real-time medical monitoring. No sync code should enter this codebase.

4. **Type hints on all public interfaces.** This is non-negotiable for a medical system. Types are documentation that the compiler enforces.

5. **Custom exception hierarchy.** Specific exceptions enable specific error handling. This pattern should be replicated in the coverage engine and alarm system.

### Adjust

1. **Rename `tests/integration/` to `tests/unit/` for the current mock-based tests.** Create a real `tests/integration/` directory for tests that hit PostgreSQL. Naming matters — it sets expectations about what's actually being tested.

2. **Add an event bus interface before building the coverage engine.** Even if the first implementation is simple (in-process callbacks), define the interface now:
   ```python
   class EventBus:
       async def subscribe(self, event_types: list[str], handler: Callable)
       async def publish(self, event: Event)
   ```
   The coverage engine, alarm system, and notification router will all need this.

3. **Establish a `config.py` pattern.** Pool sizes, timeouts, feature flags — all should come from environment variables via a central config module. Don't let hardcoded values spread.

4. **Add a `CHANGELOG.md` or use conventional commits.** As the team grows, knowing what changed and why becomes critical. Start the habit now.

### New Patterns Needed for Week 2

1. **State machine implementation pattern.** The coverage course engine is a state machine (active → superseded → closed → gap). Define how state machines are implemented: pure functions that take current state + event → new state? A base class? Document the pattern before Pituach implements three different state machines three different ways.

2. **Background worker pattern.** The night alarm daemon needs a long-running async process. Define: how are workers started? How do they report health? How are they restarted on failure? This is infrastructure that underpins Phase 1 Week 4.

3. **Repository/service layer.** Currently the API endpoint functions contain raw SQL. This works for Week 1's simplicity but won't scale. By Week 2, introduce:
   ```
   API endpoint → Service (business logic) → Repository (data access)
   ```
   The event store already *is* a repository. The patient API needs the same treatment.

---

## 6. Learnings for Subagents

### For Pituach (Backend Development)

1. **The `FastAPI()` vs `APIRouter()` mistake is a common one.** When creating modular routers, always use `APIRouter`. `FastAPI()` is only for the root application. This should be caught by a linter rule or code review checklist item.

2. **Consistency in serialization matters.** The event store uses `json.dumps()` for JSONB; the patient API doesn't. Pick one approach and apply it everywhere. Inconsistency in data handling is how silent corruption happens.

3. **"Integration test" means testing integration.** Mocks are for unit tests. Integration tests should hit the actual dependencies — in this case, PostgreSQL. Use `testcontainers-python` for ephemeral Postgres instances in CI.

4. **Think about the next consumer of your code.** The event store has no subscription mechanism. When building a component, ask: "Who will consume this, and how?" If the coverage engine needs to react to events, the event store should support that — even if it's Week 2 work, the interface should be designed in Week 1.

### For All Agents

1. **The schema is the contract.** 15 tables were created in one migration. That's fine for Week 1, but going forward, each sprint's schema changes should be in separate, numbered migration files. `002_add_event_bus_metadata.sql`, not editing `001_initial_schema.sql`.

2. **Immutable data structures require thinking about corrections differently.** You can't UPDATE an event. So how do you handle "oops, I logged the wrong glucose reading"? The `amends` pattern is the answer — but the current CHECK constraint blocks it. Understand the pattern before you implement on top of it.

3. **Medical data has unique constraints.** `ON DELETE CASCADE` is standard in most apps. In medical systems, data destruction is a compliance violation. Default to soft-delete. Default to retention. Default to "keep everything."

4. **Document your assumptions.** The `source_id` column has no documentation. The pool sizes are hardcoded without explanation. Every magic number, every undocumented column, every implicit assumption is a bug waiting for the developer who doesn't share that assumption.

---

## Final Assessment

### Should Week 1 code be merged?

**Yes, with conditions.**

The foundation is architecturally sound. The event-sourced pattern is correctly implemented. The schema supports the full 16-week roadmap. The code quality is good — not perfect, but good enough for a Week 1 deliverable that will evolve.

**Conditions before merge:**
1. Fix `FastAPI()` → `APIRouter()` in patients.py
2. Resolve the `events_immutable` CHECK constraint ambiguity
3. Add a note/TODO for the missing event bus interface

**Conditions before Week 2 starts:**
1. Commit the architecture spec document
2. Design the event notification mechanism
3. Establish the state machine implementation pattern

### Can Week 2 proceed on this foundation?

**Yes.** The data layer is solid. The event store's query interface supports what the coverage engine needs. The schema already has the `coverage_courses` table ready. The main gap — event reactivity — is a design task, not a rebuild.

### Confidence Level

**High.** This is clean Week 1 work. The issues found are refinements, not rewrites. The architectural intent was followed faithfully. The codebase is in good shape for the 15 weeks ahead.

---

*Review completed by Technical Architect (Claude Opus)*  
*Cross-audited with Ezra's Week 1 Audit — findings are complementary, not contradictory.*
