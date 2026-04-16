# Pippen — GSD1A Intelligence Operating System

**AI-powered intelligence layer for Glycogen Storage Disease Type 1a management.**

[![Phase 2 Complete](https://img.shields.io/badge/Phase-2%20Complete-brightgreen)](#)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](./LICENSE)

---

## What is Pippen?

Pippen is a **safety-critical intelligence operating system** for patients and caregivers managing **Glycogen Storage Disease Type 1a (GSD1A)** — a rare genetic metabolic disorder requiring precise cornstarch timing to maintain blood glucose.

### The Problem

GSD1A patients face a daily balancing act:
- Cornstarch every **5.15 hours** (even overnight)
- **Hypoglycemia risk** if coverage lapses
- No visibility into patterns until a crisis happens
- caregivers receive late or unclear alerts

### The Solution

Pippen learns each patient's patterns, detects anomalies early, generates actionable daily briefs, and delivers intelligent alerts to caregivers — before a crisis occurs.

---

## Status

**Phase 2 (Intelligence) is complete.** The system learns patient patterns and delivers proactive notifications.

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Foundation | ✅ Complete | Data entry, coverage tracking, night alarms |
| Phase 2: Intelligence | ✅ Complete | Pattern detection, risk scoring, daily briefs, alerts |
| Phase 3: Research & Chat | ⚪ Not Started | Research engine, Ask Pippen chat |
| Phase 4: Production | ⚪ Not Started | Security hardening, compliance, launch |

---

## Features

### Coverage Tracking
- Course-based timing (5.15h cornstarch / 2h meals)
- Automatic chain linking between doses
- Gap/overlap detection

### Night Safety Alarms
- Deterministic state machine: `warning → expired → alarm → escalation`
- Telegram notifications with escalation chain
- 60-second monitoring tick

### Intelligence Layer
- **Baselines** — rolling 30-day overnight averages
- **Pattern Detection** — late dosing, overnight lows, instability
- **Risk Scoring** — weighted overnight risk with explainable factors
- **Daily Briefs** — what changed, what matters, what to do tonight
- **Recommendation Engine** — ranked, actionable guidance for the Now screen
- **Change Detection** — week-over-week comparison of key metrics

### Mobile App
- Offline-first PWA (works without network)
- 5 tabs: Now, Trends, Watch, Actions, Profile
- 4 entry forms: glucose, cornstarch, meal, symptom
- Real-time intelligence display

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         MOBILE (PWA)                         │
│   Now  │  Trends  │  Watch  │  Actions  │  Profile         │
│   Offline-first  ·  Dexie.js  ·  Background sync            │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTPS / REST
┌──────────────────────────▼───────────────────────────────────┐
│                    BACKEND (Python / FastAPI)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Entries API │  │ Course Engine│  │   Alarm Engine     │  │
│  │   (REST)     │  │(State Machine)│  │   (60s tick)      │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Intelligence: Baseline · Pattern · Risk · Brief · Alert│   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐     │
│  │  Event Store │  │   Notifiers  │  │  /now endpoint │     │
│  │  (Immutable) │  │ Telegram/FCM │  │  (unified API) │     │
│  └──────────────┘  └──────────────┘  └────────────────┘     │
└──────────────────────────┬───────────────────────────────────┘
                           │ asyncpg
┌──────────────────────────▼───────────────────────────────────┐
│                      POSTGRESQL                               │
│  events · coverage_courses · patients · caregivers ·          │
│  recommendations · patient_baselines · patient_patterns ·      │
│  daily_briefs · night_alarm_state · notification_log         │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, asyncpg, Pydantic |
| Database | PostgreSQL 16 |
| Mobile | React 18, TypeScript, Vite, Tailwind CSS, Dexie.js |
| Notifications | Telegram Bot API |
| Intelligence | Deterministic rule-based engines (no ML in alarm paths) |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16
- Telegram Bot token (from [@BotFather](https://t.me/BotFather))

### Backend

```bash
# Clone
git clone https://github.com/AriWein31/pippen-gsd1a.git
cd pippen-gsd1a

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL and TELEGRAM_BOT_TOKEN

# Start PostgreSQL
brew services start postgresql@16

# Run migrations
psql -U postgres -d pippen -f src/backend/db/migrations/001_initial_schema.sql
psql -U postgres -d pippen -f src/backend/db/migrations/002_add_coverage_courses_updated_at.sql
psql -U postgres -d pippen -f src/backend/db/migrations/003_add_active_alerts.sql

# Start development server
cd src/backend
python -m uvicorn main:app --reload --port 8000
```

### Mobile

```bash
cd src/mobile
npm install
npm run dev
```

### Run Tests

```bash
# Backend unit tests
cd src/backend
python -m pytest tests/unit/ -v

# Mobile type check
cd src/mobile
npm run build
```

---

## Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /patients/{id}/now` | GET | Unified Now screen — recommendations, changes, risk, brief, alerts |
| `GET /patients/{id}/intelligence/baselines` | GET | Current baselines for all metrics |
| `GET /patients/{id}/intelligence/patterns` | GET | Detected patterns with confidence |
| `GET /patients/{id}/intelligence/risk` | GET | Current risk score and factors |
| `GET /patients/{id}/brief` | GET | Today's daily brief |
| `GET /patients/{id}/alerts` | GET | Active unacknowledged alerts |
| `POST /patients/{id}/glucose` | POST | Log glucose reading |
| `POST /patients/{id}/cornstarch` | POST | Log cornstarch dose |
| `GET /health` | GET | Health check |

---

## Documentation

| Document | Description |
|----------|-------------|
| [CHANGELOG](./CHANGELOG.md) | Version history and release notes |
| [Project Memory](./docs/MEMORY.md) | Technical decisions, setup, commit history |
| [Team Status](./docs/TEAM_STATUS.md) | Sprint status and agent assignments |
| [Project Plan](./docs/PROJECT_PLAN.md) | Full 16-week roadmap |
| [Sprint 07](./docs/sprints/sprint-07-alert-notifications.md) | Smart Notifications — AlertRouter, Telegram sender |
| [Sprint 08](./docs/sprints/sprint-08-now-screen-intelligence.md) | Now Screen Intelligence — Recommendations, /now endpoint |

---

## Safety

This system manages a life-critical condition. Safety is not optional.

- **No ML in alarm paths** — all alarm logic is deterministic and auditable
- **Immutable event history** — full audit trail for clinical review
- **Multi-channel alerts** — Telegram notifications with escalation chain
- **Critical alert bypass** — quiet hours respected except for critical alerts
- **Timezone-aware** — all times computed in patient's local timezone

---

## Contributing

This is a private project. For questions, contact the project lead.

---

## License

Proprietary — All rights reserved.
