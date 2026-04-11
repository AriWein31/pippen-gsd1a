# Pippen — GSD1A Intelligence Operating System

**The living intelligence system for Glycogen Storage Disease Type 1a.**

---

## Project Status

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | 🟡 Planned | 0% |
| Phase 2: Intelligence | ⚪ Not Started | 0% |
| Phase 3: Research & Chat | ⚪ Not Started | 0% |
| Phase 4: Safety & Polish | ⚪ Not Started | 0% |

**Last Updated:** 2026-04-11  
**Project Lead:** Ezra (GPT-5.4 Codex)  
**Architecture:** [Opus Technical Architecture](./docs/architecture-v2.md)

---

## Quick Links

- [📋 Project Planning Sheet](./docs/PROJECT_PLAN.md) — Timeline, milestones, deliverables
- [🏗️ Technical Architecture](./docs/architecture-v2.md) — Full system design by Opus
- [🎨 Design System](./docs/design-system.md) — Mobile UI specifications
- [👥 Team Status](./docs/TEAM_STATUS.md) — Sub-agent assignments and daily reports
- [🎯 Current Sprint](./docs/sprints/current-sprint.md) — What we're building now
- [📊 Milestones](./docs/MILESTONES.md) — Deliverables and deadlines

---

## What is Pippen?

Pippen is a **mobile-first intelligence operating system** for patients and caregivers managing GSD1A (Glycogen Storage Disease Type 1a).

### Core Capabilities

1. **Coverage Tracking** — Course-based timing (5.15h cornstarch, 2h meals) with personalization
2. **Night Safety** — Critical alarm system with escalation to emergency contacts
3. **Intelligence Layer** — Pattern detection, risk assessment, daily insights
4. **Research Watch** — Continuous monitoring of trials, papers, community signals
5. **Ask Pippen** — Context-aware chat grounded in patient data + GSD1A knowledge

---

## Repository Structure

```
pippen/
├── README.md                    # This file
├── docs/                        # Documentation
│   ├── PROJECT_PLAN.md          # Master planning sheet
│   ├── architecture-v2.md       # Technical architecture
│   ├── design-system.md         # UI/UX specifications
│   ├── MILESTONES.md            # Milestone tracking
│   ├── TEAM_STATUS.md           # Daily team reports
│   ├── sprints/                 # Sprint documentation
│   │   ├── current-sprint.md
│   │   └── sprint-01-foundation.md
│   └── decisions/               # Architectural Decision Records
├── src/                         # Source code (by phase)
│   ├── mobile/                  # React Native / PWA app
│   ├── backend/                 # API server
│   ├── intelligence/            # Pattern detection engines
│   ├── research/                # Crawlers and claim extraction
│   └── shared/                  # Common types, utilities
├── tests/                       # Test suites
├── infra/                       # Infrastructure as code
└── scripts/                     # Automation scripts
```

---

## Development Team

| Role | Agent | Model | Status |
|------|-------|-------|--------|
| Project Lead / Architect | Ezra | GPT-5.4 Codex | 🟢 Active |
| Backend Lead | Pituach | MiniMax 2.7 | ⚪ Available |
| Mobile Lead | To be assigned | MiniMax 2.7 | ⚪ Available |
| Intelligence Engineer | To be assigned | MiniMax 2.7 | ⚪ Available |
| QA / Safety Auditor | Ezra | GPT-5.4 Codex | 🟢 Active |

---

## Daily Rhythm

1. **09:00 IST** — Watchdog checks all agents, reports status
2. **09:30 IST** — Team standup (sub-agents report progress)
3. **18:00 IST** — End-of-day reports committed to TEAM_STATUS.md
4. **20:00 IST** — Ezra review and next-day planning

---

## Safety First

This system manages a life-critical condition. All code affecting:
- Night alarms
- Emergency escalation
- Glucose threshold logic

**Must pass:**
1. Unit tests (100% coverage)
2. Integration tests
3. GPT-5.4 Codex safety audit
4. Human review (Ari or designated clinician)

---

## License

Proprietary — All rights reserved.

---

**Questions?** Check the [Project Planning Sheet](./docs/PROJECT_PLAN.md) or ask Ezra.
