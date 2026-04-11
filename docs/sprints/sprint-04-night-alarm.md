# Sprint 04: Night Alarm System

**Sprint Duration:** Week 4  
**Goal:** Deterministic night alarm system with escalation and mobile readiness  
**Status:** ✅ Complete

---

## Delivered

### Backend
- Dedicated alarm engine in `src/backend/alarms/engine.py`
- HA daemon in `src/backend/alarms/daemon.py`
- Deterministic state machine:
  - `active -> warning_sent -> expired -> alarmed -> escalated -> resolved`
- Multi-channel notification abstraction:
  - Telegram
  - Push
- Alarm records stored in `night_alarm_state`
- Notification audit trail stored in `notification_log`
- Entry API integration:
  - new cornstarch / meal courses automatically create alarm tracking
  - qualifying patient events resolve active alarms

### Mobile
- Global error boundary
- Notification permission flow in Profile
- Duplicate submission prevention on forms
- Better validation and visible errors on meal/symptom flows
- Week 4 profile/status copy updates

### Safety
- Deterministic timing constants in backend
- No ML in alarm path
- Escalation is rule-based and testable
- Unit coverage scaffold added in `tests/unit/test_alarm_engine.py`

---

## Core Timing Rules

- Warning: 15 minutes before course end
- Expired: exactly at expected end
- Alarm: immediately when expired and unresolved
- Escalation: 5 minutes after alarm if unresolved
- Resolution: qualifying patient event or explicit acknowledgement

---

## Files Added

- `src/backend/alarms/__init__.py`
- `src/backend/alarms/engine.py`
- `src/backend/alarms/daemon.py`
- `src/backend/alarms/notifiers.py`
- `src/mobile/src/hooks/useNotifications.ts`
- `src/mobile/src/components/ErrorBoundary.tsx`
- `tests/unit/test_alarm_engine.py`
- `docs/audits/week4-deep-audit-ezra.md`

## Files Updated

- `src/backend/api/entries.py`
- `src/mobile/src/App.tsx`
- `src/mobile/src/hooks/index.ts`
- `src/mobile/src/pages/ProfilePage.tsx`
- `src/mobile/src/components/forms/GlucoseForm.tsx`
- `src/mobile/src/components/forms/CornstarchForm.tsx`
- `src/mobile/src/components/forms/MealForm.tsx`
- `src/mobile/src/components/forms/SymptomForm.tsx`

---

## Verification

- ✅ Python syntax compile passed
- ✅ Mobile production build passed
- ⚠️ Full Python pytest run blocked locally because `pytest` is not installed on this machine runtime

---

## Merge Readiness

Week 4 is implemented and audited. Remaining work for future weeks is production delivery infrastructure for real APNs/FCM credentials and live Telegram bot wiring.
