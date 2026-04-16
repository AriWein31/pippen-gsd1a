# Pippen GSD1A — Project Memory

_This file is the persistent project memory for `AriWein31/pippen-gsd1a`. It supplements the sprint docs and TEAM_STATUS.md._

---

## Current State (as of 2026-04-16)

**Phase:** Phase 2 complete — MVP done ✅
**Next:** Phase 3 (Research & Chat, Weeks 9-12) — not started

---

## What Was Built

### Phase 1 (Weeks 1-4) — Foundation ✅
- PostgreSQL schema + event store
- Coverage course engine (5.15h cornstarch / 2h meal timing)
- Mobile PWA (React, offline-first, 5 tabs)
- Night alarm system (warning → expired → alarm → escalation)

### Phase 2 (Weeks 5-8) — Intelligence ✅
- **Week 5:** BaselineEngine, PatternEngine (3 detectors), RiskEngine, BriefGenerator
- **Week 6:** Mobile Now screen intelligence integration
- **Week 7:** AlertRouter, NotificationDispatcher, AsyncTelegramNotificationService, quiet hours, FastAPI main.py
- **Week 8:** RecommendationEngine, ChangeDetector, `/patients/{id}/now` endpoint, NowPage rewrite

---

## Key Technical Decisions

### Timezone Handling
Patient preferences store `timezone` as an IANA string (e.g. `"Asia/Jerusalem"`). All backend code converts to patient local time before computing bedtime dose timing. Falls back to UTC if not set.

### Alert Flow
```
PATTERN_DETECTED event
  → AlertDecisionEngine.evaluate()
  → Throttle (1 per pattern_type/hour)
  → INSERT recommendations (alert_severity set)
  → Publish ALARM_TRIGGERED to event bus
  → NotificationDispatcher subscribes
  → Looks up caregiver telegram_ids from DB
  → AsyncTelegramNotificationService.send()
  → Telegram bot (PipenAriLifeBot)
```

### Priority Scoring (rank_recommendations)
```
score = (risk_score * 0.3) + (pattern_confidence * 0.25) + (alert_priority * 0.25) + (brief_priority * 0.2)
```

### Git Repository Rules
- **Our fork:** `AriWein31/pippen-gsd1a`
- **DO NOT commit to upstream** (`matan-boop/pippen-gsd1a`)

---

## Environment Variables

| Variable | Value | Location |
|----------|-------|----------|
| `DATABASE_URL` | `postgresql://postgres@localhost/pippen` | `projects/pippen/.env` |
| `TELEGRAM_BOT_TOKEN` | `8622755295:AAFIUktOng4yk5U4Hn4X3wwYSrrANdN06DA` | macOS Keychain `pippen/telegram_bot_token` |

**Test patient ID:** `00000000-0000-0000-0000-000000000001`
**Test caregiver Telegram:** `321490902` (Ari)

---

## PostgresQL Setup (macOS)

```bash
# Start
brew services start postgresql@16

# Connect
/opt/homebrew/opt/postgresql@16/bin/psql -U postgres -d pippen

# Reset DB
/opt/homebrew/opt/postgresql@16/bin/dropdb -U postgres pippen
/opt/homebrew/opt/postgresql@16/bin/createdb -U postgres pippen
# Then re-run migrations manually (001 is not fully idempotent)
```

**Tables:** patients, caregivers, events, coverage_courses, night_alarm_state, recommendations, patient_baselines, patient_patterns, daily_briefs, notification_log

---

## Sprint Commit History

| Sprint | Commit | What |
|--------|--------|------|
| Week 5 | `49266e8` | Intelligence layer complete |
| Week 6 | `0d5a333` | Mobile Now screen intelligence |
| Week 7 | `f857dd0` | main.py + NotificationDispatcher + AsyncTelegramNotificationService |
| Week 7 | `a2577cc` | httpx client reuse + timezone-aware quiet hours |
| Week 8 | `7b30bb2` | RecommendationEngine + ChangeDetector + /now endpoint |
| Week 8 | `41ee6ee` | Mobile NowPage rewrite + useNow hook |
| Week 8 | `dd53d06` | Audit fixes (asyncio import, MOCK_NOW, timezone) |
| Sprint docs | `74ea8cf` | TEAM_STATUS updated |

---

## Ezra Audit Findings (Week 8)

**Fixed:**
- `asyncio` import at bottom of `recommendations.py` → moved to top
- `MOCK_NOW` had specific patient-like data → replaced with generic placeholders
- `ChangeDetector` assumed naive datetimes were UTC → now uses patient timezone from preferences

**Noted (acceptable for MVP):**
- `handleDismissRecommendation` is a no-op stub — backend dismiss action not wired yet
- `AlertCard onAcknowledge/onDismiss` are empty stubs — fine for MVP phase

---

## Week-by-Week Status

| Week | Status | Key Files |
|------|--------|-----------|
| 1-4 | ✅ Complete | `events/`, `courses/`, `alarms/`, mobile/ |
| 5 | ✅ Complete | `intelligence/baseline.py`, `patterns.py`, `risk.py`, `brief.py` |
| 6 | ✅ Complete | `IntelligenceCard.tsx`, `useIntelligence.ts` |
| 7 | ✅ Complete | `main.py`, `alerts.py`, `notifiers.py` |
| 8 | ✅ Complete | `recommendations.py`, `changes.py`, `api/now.py`, `NowPage.tsx`, `useNow.ts` |
| 9-12 | ⚪ Not Started | Phase 3: Research engine, Watch screen, Ask Pippen |
| 13-16 | ⚪ Not Started | Phase 4: Security, performance, launch |

---

## Contacts

- **Project Lead:** Ari Wein (`i0xAri`)
- **Telegram bot:** `@PippenAriLifeBot`
- **Repo:** `https://github.com/AriWein31/pippen-gsd1a`
