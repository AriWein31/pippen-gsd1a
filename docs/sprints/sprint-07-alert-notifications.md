# Sprint 07: Smart Notifications — Intelligence-to-Alert Delivery

**Sprint Duration:** Week 7 (April 13-19, 2026)  
**Goal:** Turn intelligence (risk scores, patterns, briefs) into actionable, explainable alerts  
**Lead:** Candidate 1 (backend), Candidate 3 (mobile UX)  
**Model:** MiniMax 2.7  
**Status:** ✅ Backend Complete (2026-04-16)

**Commits:**
- `f857dd0` — Week 7: FastAPI main.py, AsyncTelegramNotificationService, NotificationDispatcher, quiet hours
- `a2577cc` — Fix: httpx client reuse + timezone-aware quiet hours

---

## Context

Weeks 5–6 built the intelligence layer:
- `BaselineEngine` — computes overnight baselines with confidence scores
- `PatternEngine` — detects 3 pattern types with severity + confidence
- `RiskEngine` — computes weighted overnight risk scores with explainable factors
- `BriefGenerator` — composes daily brief summaries
- `PATTERN_DETECTED`, `BASELINE_UPDATED`, `RISK_UPDATED` events published to bus

**The gap:** Intelligence signals are published but nothing subscribes to them. Intelligence is displayed in the app but never proactively delivered as alerts.

Week 7 closes that gap.

---

## Week 7 Tasks

### Task 7.1: Alert Decision Engine (3h)
**Owner:** Candidate 1

Deterministic rules — same inputs always produce the same alert decision:

**Pattern signal thresholds:**
- `confidence >= 0.70` AND `severity >= 3/10` → alert fires
- Severity 8–10 → `high`
- Severity 5–7 → `medium`
- Severity 3–4 → `low`

**Risk score thresholds:**
- `risk_score >= 3.0` AND `confidence >= 0.70` → alert fires
- Severity mapped directly from `risk_level`

**Throttle:** 1 alert per pattern_type per patient per hour (in-process, reset on restart).

**Deliverable:** `src/backend/intelligence/alerts.py` — `AlertDecisionEngine`, `AlertDecision` dataclass, pure helper functions.

---

### Task 7.2: Alert Router — Event Bus Integration (2h)
**Owner:** Candidate 1

Subscribe to `PATTERN_DETECTED` events, evaluate with `AlertDecisionEngine`, persist to DB, publish `ALARM_TRIGGERED`:

```
PATTERN_DETECTED event
  → AlertDecisionEngine.evaluate_pattern()
  → Throttle check (in-process)
  → INSERT into recommendations (is_dismissed=FALSE, alert_severity set)
  → Publish ALARM_TRIGGERED to event bus
```

**Deliverable:** `AlertRouter` class in `intelligence/alerts.py`.

---

### Task 7.3: Active Alerts API (2h)
**Owner:** Candidate 1

Add to `patients.py`:

```
GET  /patients/{id}/alerts          → list active (unacknowledged, undismissed) alerts
POST /patients/{id}/alerts/{id}/acknowledge → mark acknowledged
POST /patients/{id}/alerts/{id}/dismiss     → mark dismissed
```

Ordered by severity (critical first) then creation time (newest first).

**Deliverable:** `AlertResponse`, `AlertsListResponse` Pydantic models; endpoints wired in `create_patients_router`.

---

### Task 7.4: DB Migration for Active Alerts (1h)
**Owner:** Candidate 1

Add to `recommendations` table:
- `alert_source` VARCHAR — 'pattern', 'risk', 'brief'
- `alert_severity` VARCHAR — 'low', 'medium', 'high', 'critical'
- `triggered_by_event_ids` JSONB — event IDs that caused the alert

**Deliverable:** `db/migrations/003_add_active_alerts.sql`.

---

### Task 7.5: Mobile — useAlerts Hook (2h)
**Owner:** Candidate 3

React hook that:
- Fetches `GET /patients/{id}/alerts` every 5 minutes
- Exposes `acknowledge(alertId)` and `dismiss(alertId)` functions
- Returns severity counts (critical, high, medium, low)

**Deliverable:** `src/mobile/src/hooks/useAlerts.ts`.

---

### Task 7.6: Mobile — AlertCard Component (2h)
**Owner:** Candidate 3

Display a single alert with:
- Severity badge (critical=red, high=orange, medium=amber, low=blue)
- Pulsing dot for critical/high
- Title, description, confidence
- "Why this alert fired" expandable rationale
- Acknowledge / Dismiss action buttons

**Deliverable:** `src/mobile/src/components/AlertCard.tsx`.

---

### Task 7.7: Mobile — NowPage AlertsSection (1h)
**Owner:** Candidate 3

Add alerts section to NowPage, above the Intelligence Panel:
- Shows only when `hasActiveAlerts === true`
- Renders list of `AlertCard` components

**Deliverable:** `NowPage.tsx` updated.

---

## Files Changed

### Backend
| File | Change |
|------|--------|
| `src/backend/intelligence/alerts.py` | NEW — AlertDecisionEngine, AlertRouter, ActiveAlert, helpers |
| `src/backend/api/patients.py` | ADD — AlertResponse, AlertsListResponse, GET/POST endpoints |
| `src/backend/db/migrations/003_add_active_alerts.sql` | NEW — alert columns on recommendations |
| `src/backend/alarms/engine.py` | FIX — add missing `logger` import |

### Mobile
| File | Change |
|------|--------|
| `src/mobile/src/types/index.ts` | ADD — `Alert` interface |
| `src/mobile/src/api/client.ts` | ADD — `fetchAlerts`, `acknowledgeAlert`, `dismissAlert` |
| `src/mobile/src/hooks/useAlerts.ts` | NEW — `useAlerts()` hook |
| `src/mobile/src/components/AlertCard.tsx` | NEW — AlertCard component |
| `src/mobile/src/pages/NowPage.tsx` | ADD — AlertsSection + imports |

### Tests
| File | Change |
|------|--------|
| `tests/unit/test_intelligence_alerts.py` | NEW — AlertDecisionEngine unit tests |

---

## Remaining Blockers

1. ~~AlertRouter wiring~~ — ✅ `src/backend/main.py` created; AlertRouter instantiated and subscribed at startup
2. ~~Notification dispatch~~ — ✅ `AsyncTelegramNotificationService` + `NotificationDispatcher` wired to `ALARM_TRIGGERED` bus events
3. ~~Quiet hours / fatigue prevention~~ — ✅ `NotificationDispatcher._is_in_quiet_hours()` reads `patient.preferences.notification_quiet_hours`; critical alerts bypass quiet hours

**Status as of 2026-04-16:** Tasks 1–4 backend work complete. FastAPI app (`main.py`) starts AlertRouter and NotificationDispatcher on startup. Telegram messages flow from `ALARM_TRIGGERED` events → dispatcher → API. Sprint doc updated.

---

## Next Steps (Week 8)

1. Wire AlertRouter into FastAPI main.py
2. Connect ALARM_TRIGGERED → TelegramNotificationFormatter pipeline
3. Add patient preference support (quiet hours, severity thresholds)
4. Push notification support for iOS/Android

---

**Last Updated:** 2026-04-16
