# Changelog

All notable changes to the Pippen GSD1A Intelligence Operating System are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased] — Next Release

### Added
- Phase 3 (Research & Chat) planning in progress

### Changed
- README completely rewritten for clarity and professionalism

---

## [Phase 2] — Intelligence Layer — 2026-04-16

> **Milestone:** MVP Complete ✅

### Week 8 — Now Screen Intelligence — 2026-04-16

**Backend:**

- **`RecommendationEngine`** (`src/backend/intelligence/recommendations.py`)
  - Synthesizes brief, risk score, patterns, and active alerts into ranked `Recommendation` objects
  - Priority rules: unacknowledged alerts → critical, risk ≥ 4.0 → high, pattern confidence ≥ 0.75 → high
  - `rank_recommendations()` with weighted scoring formula

- **`ChangeDetector`** (`src/backend/intelligence/changes.py`)
  - Compares last 7 days vs days 8-14 across: avg glucose, low frequency, variability (CV), bedtime dose timing
  - Uses patient timezone from preferences (IANA format), falls back to UTC
  - Handles naive datetimes correctly

- **`/patients/{id}/now` endpoint** (`src/backend/api/now.py`)
  - Unified API returning: `recommendations`, `changes`, `risk`, `brief`, `active_alerts`
  - All signals fetched concurrently via `asyncio.gather`

- **E2E test script** (`scripts/e2e_test_now_screen.sh`)

**Mobile:**

- **`useNow` hook** (`src/mobile/src/hooks/useNow.ts`)
  - Polls `/patients/{id}/now` every 5 minutes
  - Falls back to realistic mock data when backend unavailable (dev mode badge)

- **`NowPage.tsx`** — full rewrite
  - Priority badge + pulsing dot on critical/high recommendations
  - Recommendation cards with headline, explanation, suggested action, Dismiss/Done buttons
  - Changes panel: week-over-week with up/down/stable arrows
  - Brief panel, Risk card, Active Coverage, Quick Log

- **`IntelligenceCard.tsx`** — updated to render Recommendation types

- **`Icons.tsx`** — added `TrendingUpIcon`, `TrendingDownIcon`, `MinusIcon`

**Audits (Ezra, 2 passes):**

- `asyncio` import moved from bottom to top of `recommendations.py`
- `MOCK_NOW` data replaced with generic placeholders (no real patient data in source)
- `ChangeDetector` timezone handling fixed: uses patient timezone from preferences

### Week 7 — Smart Notifications — 2026-04-16

**Backend:**

- **`FastAPI main.py`** (`src/backend/main.py`)
  - Lifespan context manager: pool setup/teardown, AlertRouter start/stop
  - `NotificationDispatcher` wired to `ALARM_TRIGGERED` events at startup
  - CORS locked to `localhost:5173`
  - `/health` endpoint

- **`AsyncTelegramNotificationService`** (`src/backend/alarms/notifiers.py`)
  - HTTP sender to Telegram Bot API using `httpx.AsyncClient`
  - 429 rate limit handling with exponential backoff (max 3 retries)
  - Graceful degradation if `TELEGRAM_BOT_TOKEN` is missing/invalid

- **`NotificationDispatcher`** (`src/backend/main.py`)
  - Subscribes to `ALARM_TRIGGERED` on event bus
  - Maps severity to caregiver notification preference column
  - Looks up caregivers with `telegram_id` from DB
  - Quiet hours: timezone-aware via `patient.preferences.notification_quiet_hours`
  - Critical alerts bypass quiet hours

- **DB migration** (`003_add_active_alerts.sql`)
  - `alert_source`, `alert_severity`, `triggered_by_event_ids` on `recommendations` table

### Week 6 — Mobile Intelligence — 2026-04-13

- `IntelligenceCard` component — risk score, brief, baselines display
- `useIntelligence` hook — parallel fetching of baselines, patterns, risk, brief
- Loading, insufficient-data, partial-data, not-configured states
- Dev mode banner when `VITE_PATIENT_ID` not set

### Week 5 — Intelligence Layer — 2026-04-11

- **`BaselineEngine`** — rolling 30-day overnight baselines
- **`PatternEngine`** — 3 detectors: late dosing, overnight low clusters, instability
- **`RiskEngine`** — weighted overnight risk with explainable factors and confidence
- **`BriefGenerator`** — daily brief: `what_changed`, `what_matters`, `recommended_attention`
- Intelligence API endpoints wired into patients router
- 33 unit tests passing

---

## [Phase 1] — Foundation — 2026-04-10

### Week 4 — Night Alarm System — 2026-04-10

- State machine: `active → warning_sent → expired → alarmed → escalated → resolved`
- `CoverageAlarmEngine` — 60-second tick monitoring all patients
- Multi-channel notifiers (Telegram, push)
- Deterministic timing rules with clinical justification
- Safety audit passed

### Week 3 — Mobile Shell — 2026-04-03

- React PWA with 5 tabs: Now, Trends, Watch, Actions, Profile
- 4 entry forms: glucose, cornstarch, meal, symptom
- Offline-first with Dexie.js (IndexedDB)
- Vite + Workbox + Tailwind CSS

### Week 2 — Coverage Course Engine — 2026-03-27

- Course model with state machine
- 5.15-hour cornstarch coverage / 2-hour meal coverage
- Course chain linking (previous/next)
- Manual entry APIs (REST)

### Week 1 — Data Models & Event Store — 2026-03-20

- PostgreSQL schema with all core tables
- Immutable event store (append-only)
- Patient/Caregiver models
- Event bus for reactive components
- `EventStore` class for event append/query

---

## [Prior to 2026-03-20]

Project inception. Architecture design, team formation, Phase 1 planning.
