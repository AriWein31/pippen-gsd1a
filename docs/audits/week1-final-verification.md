# Week 1 Final Verification Report

**Reviewer:** Ezra (Technical Lead)  
**Date:** 2026-04-11  
**Branch:** main

---

## Summary

Three critical issues were flagged by Opus's architecture review. Two are **FIXED**. One is **PARTIALLY FIXED** with a remaining concern.

---

## Issue Status

### 1. CHECK constraint blocking amendments
**Status: ✅ FIXED**

The events table schema (`001_initial_schema.sql`) no longer contains any CHECK constraint. Immutability is enforced via:
- No `updated_at` column on the events table
- Application-layer enforcement (no UPDATE/DELETE)
- `amends` / `amended_by` columns for amendment workflow support

This is the correct approach — amendments are handled by referencing the original event via `amends`, not by modifying it.

---

### 2. FastAPI used instead of APIRouter
**Status: ⚠️ PARTIALLY FIXED**

The `create_patients_router()` factory function correctly uses `APIRouter`:
```python
router = APIRouter(prefix="/patients", tags=["patients"])
```

**Remaining concern:** The bottom of `patients.py` has:
```python
app = FastAPI(title="Pippen Patients API")
```
This module-level FastAPI app is unused by the router factory but is a footgun — if anything imports this module and uses `app`, it will fail. It should either be removed or properly wired to the router in `main.py`.

**Verdict:** Not a blocker for Week 2, but should be cleaned up.

---

### 3. Missing event bus
**Status: ✅ FIXED**

`src/backend/events/bus.py` is a new, well-designed addition:
- `EventBus` abstract interface with `publish`, `subscribe`, `unsubscribe`
- `InMemoryEventBus` concrete implementation (dev/test only — noted appropriately)
- `EventTypes` constants for type safety
- `get_event_bus()` / `set_event_bus()` singleton pattern

---

### 4. Event bus integration in store
**Status: ✅ FIXED**

`store.py`'s `append_event()` correctly publishes to the bus after insert:
```python
bus = get_event_bus()
await bus.publish(EventTypes.EVENT_STORED, {...})
```

---

## Remaining Concerns

| Priority | Issue | File | Note |
|----------|-------|------|------|
| Low | Module-level `app = FastAPI(...)` | `patients.py` | Dead code / footgun; clean up before production |

---

## Week 2 Approval

**✅ APPROVED TO PROCEED**

All critical architecture issues are resolved. The codebase is in a valid state to continue into Week 2 (coverage engine + alarm state machine). The `patients.py` FastAPI app issue is low-priority technical debt and does not block progress.

---

*Next: Week 2 coverage engine implementation*
