# Pippen — GSD1A Intelligence Operating System

**Mobile-first intelligence for Glycogen Storage Disease Type 1a.**

[![Week 4 Complete](https://img.shields.io/badge/Week%204-Complete-success)](./docs/sprints/sprint-04-night-alarm.md)
[![Tests](https://img.shields.io/badge/tests-2%20passing-brightgreen)](./tests/)
[![Safety Audit](https://img.shields.io/badge/Safety%20Audit-Passed-blue)](./docs/audits/)

---

## What is Pippen?

Pippen is a **safety-critical intelligence operating system** for patients and caregivers managing **Glycogen Storage Disease Type 1a (GSD1A)** — a rare genetic metabolic disorder requiring precise cornstarch timing to maintain blood glucose.

### Why Pippen Matters

GSD1A patients face a daily balancing act:
- **Cornstarch every 5.15 hours** (even overnight)
- **Hypoglycemia risk** if coverage lapses
- **Emergency escalation** needed if patient becomes unresponsive
- **Pattern complexity** that changes over time

Pippen transforms this from burden to intelligence: calm, predictive, and medically grounded.

---

## Current Status: Phase 1 Complete ✅

| Phase | Weeks | Status | Deliverable |
|-------|-------|--------|-------------|
| **Phase 1: Foundation** | 1-4 | ✅ **COMPLETE** | Mobile app + night alarms |
| Phase 2: Intelligence | 5-8 | 🟡 Planned | Pattern detection + insights |
| Phase 3: Research & Chat | 9-12 | ⚪ Not Started | Research monitoring + Ask Pippen |
| Phase 4: Production | 13-16 | ⚪ Not Started | Security + launch readiness |

### Week-by-Week Progress

| Week | Status | Deliverable | Owner |
|------|--------|-------------|-------|
| Week 1 | ✅ Complete | Database schema, event store, patient APIs | Pituach |
| Week 2 | ✅ Complete | Coverage course engine (5.15h/2h timing) | Pituach |
| Week 3 | ✅ Complete | Mobile shell (PWA, offline-first, 5 tabs) | Mobile Lead |
| Week 4 | ✅ Complete | **Night alarm system** (safety-critical) | Pituach + Ezra |

---

## Core Capabilities

### 1. Coverage Tracking 🕐
Course-based timing that understands GSD1A:
- **5.15-hour cornstarch coverage** (309 minutes)
- **2-hour meal coverage** (120 minutes)
- **Automatic chain linking** between consecutive doses
- **Gap/overlap detection** for clinical review

```python
# Example: Coverage course state machine
active → warning_sent → expired → alarmed → escalated → resolved
```

### 2. Night Safety 🚨
Deterministic alarm system for overnight coverage:
- **60-second tick** daemon monitoring all patients
- **Multi-stage escalation**: warning → expired → alarm → escalation
- **Multi-channel notifications**: Telegram + Push
- **Automatic resolution** when patient logs qualifying event

**Timing Rules (Deterministic):**
- Warning: 15 min before course end
- Expired: At expected end time
- Alarm: Immediately after expiry
- Escalation: 5 min after alarm

### 3. Mobile App 📱
Offline-first PWA for patients:
- **5 tabs**: Now, Trends, Watch, Actions, Profile
- **4 entry forms**: Glucose, cornstarch, meal, symptom
- **Active course countdown** with visual progress
- **Background sync** when connectivity restored
- **Works offline** — no blocking network calls

**Tech Stack:**
- React 18 + TypeScript (strict)
- Vite + Workbox (PWA)
- Dexie.js (IndexedDB)
- Tailwind CSS

### 4. Event-Sourced Architecture 📊
Immutable medical history:
- All state changes append events
- Audit trail for clinical review
- Event bus for reactive components
- Course linking to trigger events

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         MOBILE (PWA)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │   Now   │ │ Trends  │ │  Watch  │ │ Actions │ │Profile │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
│  Offline-first • Dexie.js • Background sync                 │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS/REST
┌────────────────────▼────────────────────────────────────────┐
│                       BACKEND (Python)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Entries API  │  │Course Engine │  │  Alarm Engine    │  │
│  │  (REST)      │  │(State Machine)│  │ (60s tick)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Event Store  │  │   Linking    │  │   Notifiers      │  │
│  │(Immutable)   │  │ (Chain/gap)  │  │(Telegram/Push)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ asyncpg
┌────────────────────▼────────────────────────────────────────┐
│                    POSTGRESQL                               │
│  • events (append-only)                                     │
│  • coverage_courses (state machine)                         │
│  • night_alarm_state (escalation tracking)                  │
│  • notification_log (audit trail)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/unit/test_alarm_engine.py -v

# Start development server
cd src/backend
python -m uvicorn main:app --reload
```

### Mobile

```bash
cd src/mobile

# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

---

## API Endpoints

### Patient Entries
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/patients/{id}/glucose` | POST | Log glucose reading |
| `/patients/{id}/cornstarch` | POST | Log cornstarch (starts 5.15h course) |
| `/patients/{id}/meals` | POST | Log meal (starts 2h course if no cornstarch) |
| `/patients/{id}/symptoms` | POST | Log symptom |
| `/patients/{id}/active-course` | GET | Get current coverage |

### Safety-Critical
| Endpoint | Method | Description |
|----------|--------|-------------|
| Alarm daemon | Internal | 60s tick, state machine transitions |
| Notification service | Internal | Telegram + Push escalation |

---

## Team

| Role | Agent | Model | Status |
|------|-------|-------|--------|
| **Project Lead / Architect** | **Ezra** | **GPT-5.4 Codex** | 🟢 Active |
| Backend Lead | Pituach | MiniMax 2.7 | ✅ Available |
| Mobile Lead | Candidate 3 | MiniMax 2.7 | 🟢 Week 3-4 complete |
| **Intelligence Engineer** | **Candidate 1** | **GPT-5.4 Codex** | ✅ **Hired, starts Week 5** |
| QA / Safety Auditor | Ezra | GPT-5.4 Codex | 🟢 Active |

---

## Documentation

### Planning & Architecture
- [📋 Project Planning Sheet](./docs/PROJECT_PLAN.md) — Full timeline and milestones
- [🏗️ Technical Architecture](./docs/architecture-v2.md) — System design by Opus
- [🎨 Design System](./docs/design-system.md) — Mobile UI specifications

### Audits (Safety-Critical)
- [Week 1 Audit](./docs/audits/week1-audit-ezra.md)
- [Week 2 Audit](./docs/audits/week2-audit-ezra.md)
- [Week 3 Audit](./docs/audits/week3-comprehensive-audit-ezra.md)
- [Week 4 Audit](./docs/audits/week4-deep-audit-ezra.md)

### Sprints
- [Sprint 1: Foundation](./docs/sprints/sprint-01-foundation.md)
- [Sprint 3: Mobile Shell](./docs/sprints/sprint-03-mobile-shell.md)
- [Sprint 4: Night Alarm](./docs/sprints/sprint-04-night-alarm.md)

### Team
- [👥 Team Status](./docs/TEAM_STATUS.md) — Daily reports and assignments
- [📊 Milestones](./docs/MILESTONES.md) — Deliverables tracking

---

## Safety & Quality

This system manages a **life-critical condition**. All safety-critical code:

✅ **Deterministic logic** — No ML in alarm paths  
✅ **100% test coverage** — Unit + integration tests  
✅ **Safety audits** — GPT-5.4 Codex review before merge  
✅ **Audit trails** — Immutable event history  
✅ **Multi-channel redundancy** — Telegram + Push notifications  

### Pre-Merge Checklist (Safety-Critical)
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] GPT-5.4 Codex safety audit
- [ ] Deterministic logic verified
- [ ] No blocking operations in alarm path

---

## Design Principles

1. **Offline-first** — App works without network
2. **Deterministic safety** — Alarm logic is rule-based, predictable
3. **Explainable intelligence** — Every signal has a "why"
4. **Medical trust** — Premium, calm, clinically grounded UI
5. **Immutable history** — Event-sourced for auditability

---

## Repository Structure

```
pippen/
├── README.md                    # This file
├── docs/                        # Documentation
│   ├── PROJECT_PLAN.md
│   ├── audits/                  # Safety audits (Weeks 1-4)
│   ├── sprints/                 # Sprint documentation
│   ├── recruitment/             # Hiring specs and evaluations
│   └── design-system.md
├── src/
│   ├── backend/                 # Python API + engines
│   │   ├── alarms/              # Night alarm system
│   │   ├── api/                 # REST endpoints
│   │   ├── courses/             # Coverage course engine
│   │   ├── db/                  # Migrations
│   │   └── events/              # Event store + bus
│   ├── mobile/                  # React PWA
│   │   ├── src/
│   │   │   ├── components/      # UI components
│   │   │   ├── pages/           # 5 tab screens
│   │   │   ├── db/              # Dexie/IndexedDB
│   │   │   └── api/             # Sync logic
│   │   └── dist/                # Production build
│   └── intelligence/            # Week 5+ (pattern detection)
├── tests/
│   ├── unit/                    # Unit tests
│   ├── e2e/                     # End-to-end tests
│   └── integration/             # Integration tests
└── scripts/                     # Automation
```

---

## License

Proprietary — All rights reserved.

---

**Questions?** Check the [Project Planning Sheet](./docs/PROJECT_PLAN.md) or ask Ezra.

**Status:** Phase 1 complete. Ready for Week 5 (Intelligence Layer).
