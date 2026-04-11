# Pippen Project Planning Sheet

**Document Owner:** Ezra (Project Lead)  
**Last Updated:** 2026-04-11  
**Status:** Phase 1 Planning

---

## Executive Summary

| Attribute | Value |
|-----------|-------|
| **Project** | Pippen — GSD1A Intelligence OS |
| **Timeline** | 16 weeks (4 phases × 4 weeks) |
| **Team Size** | 4 sub-agents + 1 lead (Ezra) |
| **Primary Model** | MiniMax 2.7 (dev), GPT-5.4 Codex (audit/oversight) |
| **Target MVP** | Week 8 (Phase 2 complete) |
| **Production Ready** | Week 16 |

---

## Phase Overview

```
Week:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
       |--PHASE 1--|  |--PHASE 2--|  |--PHASE 3--|  |--PHASE 4--|
       Foundation      Intelligence   Research&Chat   Safety&Polish
```

---

## Phase 1: Foundation (Weeks 1-4)

**Goal:** Core data entry, coverage tracking, basic night alarms

### Week 1: Data Models & Event Store

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Database schema (PostgreSQL) | Pituach | 8 | SQL migration files | ⚪ |
| Event store implementation | Pituach | 10 | Event append/query API | ⚪ |
| Patient/Caregiver models | Pituach | 4 | User management API | ⚪ |
| **Milestone W1:** Core data layer functional | Ezra | — | Integration tests passing | ⚪ |

### Week 2: Coverage Course Engine

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Course model & state machine | Pituach | 10 | CoverageCourses table + logic | ⚪ |
| Manual entry APIs (glucose, cornstarch, meals) | Pituach | 8 | REST endpoints | ⚪ |
| Course chain linking | Pituach | 6 | Previous/next course tracking | ⚪ |
| **Milestone W2:** Course tracking working | Ezra | — | End-to-end test | ⚪ |

### Week 3: Mobile App Shell + Entry Forms

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| React Native / PWA setup | Mobile Lead | 8 | Project scaffold | ⚪ |
| Navigation (5 tabs) | Mobile Lead | 4 | Bottom nav working | ⚪ |
| Entry forms (glucose, cornstarch, meal) | Mobile Lead | 10 | Form components | ⚪ |
| Offline-first sync | Mobile Lead | 8 | Local SQLite + sync queue | ⚪ |
| **Milestone W3:** Mobile app functional for entry | Ezra | — | Manual testing | ⚪ |

### Week 4: Night Alarm System (CRITICAL)

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Alarm daemon (dedicated HA process) | Pituach | 12 | Background worker | ⚪ |
| State machine: warning → expired → alarm → escalated | Pituach | 8 | State transitions | ⚪ |
| Telegram integration | Pituach | 6 | Bot API, message sending | ⚪ |
| Escalation chain logic | Pituach | 6 | Multi-contact escalation | ⚪ |
| Push notification setup | Mobile Lead | 6 | APNs/FCM integration | ⚪ |
| **SAFETY AUDIT** | Ezra (GPT-5.4) | 4 | Audit report | ⚪ |
| **Milestone W4:** Night alarm production-ready | Ezra | — | 100% test coverage | ⚪ |

**Phase 1 Deliverable:** Working mobile app with data entry, coverage tracking, and night safety alarms

---

## Phase 2: Intelligence (Weeks 5-8)

**Goal:** Pattern detection, learning layer, daily insights

### Week 5: Patient Learning Layer

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Pattern detection algorithms | Intelligence Eng | 12 | PersonalSignals engine | ⚪ |
| Baseline computation | Intelligence Eng | 6 | PatientBaselines table | ⚪ |
| Timing personalization | Intelligence Eng | 6 | Learned duration algorithm | ⚪ |
| **Milestone W5:** System learns patient patterns | Ezra | — | Pattern accuracy >70% | ⚪ |

### Week 6: Risk Engine & Insights

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Risk scoring matrix | Intelligence Eng | 10 | RiskEngine | ⚪ |
| Anomaly detection | Intelligence Eng | 8 | Overnight instability detection | ⚪ |
| Daily brief generation | Intelligence Eng | 8 | DailyBriefs table + generator | ⚪ |
| **Milestone W6:** Insights appearing in app | Ezra | — | Daily brief accuracy review | ⚪ |

### Week 7: Smart Notifications

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Notification router | Pituach | 8 | Priority-based routing | ⚪ |
| Fatigue prevention | Pituach | 6 | Throttling logic | ⚪ |
| Smart alerts (non-emergency) | Mobile Lead | 8 | In-app notification UI | ⚪ |
| **Milestone W7:** Intelligent notification system | Ezra | — | User notification preferences | ⚪ |

### Week 8: Now Screen Intelligence

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| "What changed" detection | Intelligence Eng | 8 | Change detection algorithm | ⚪ |
| "What matters" ranking | Intelligence Eng | 6 | Priority scoring | ⚪ |
| Now screen API integration | Mobile Lead | 8 | Connect UI to intelligence | ⚪ |
| Recommendation generation | Intelligence Eng | 8 | RecommendationEngine | ⚪ |
| **SAFETY AUDIT** | Ezra (GPT-5.4) | 4 | Audit report | ⚪ |
| **Milestone W8:** MVP COMPLETE | Ezra | — | Demo-ready system | ⚪ |

**Phase 2 Deliverable:** Intelligent app with learning, insights, and recommendations

---

## Phase 3: Research & Chat (Weeks 9-12)

**Goal:** Research engine, claim extraction, Ask Pippen chat

### Week 9-10: Research Engine

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Source registry & crawlers | Intelligence Eng | 16 | 10+ sources configured | ⚪ |
| PubMed API integration | Intelligence Eng | 8 | Paper fetching | ⚪ |
| ClinicalTrials.gov API | Intelligence Eng | 6 | Trial monitoring | ⚪ |
| Web scrapers (advocacy, sponsors) | Intelligence Eng | 12 | Crawler pool | ⚪ |
| Claim extraction (LLM) | Intelligence Eng | 10 | Claim decomposition | ⚪ |
| **Milestone W10:** Research pipeline active | Ezra | — | Daily research updates | ⚪ |

### Week 11: Watch Screen & Research UI

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Watch tab UI | Mobile Lead | 10 | Research briefing screen | ⚪ |
| Narrative change detection | Intelligence Eng | 8 | Shift detection algorithm | ⚪ |
| Claim ranking & relevance | Intelligence Eng | 6 | Patient-specific scoring | ⚪ |
| **Milestone W11:** Research watch in app | Ezra | — | 5+ daily updates | ⚪ |

### Week 12: Ask Pippen Chat

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Chat UI | Mobile Lead | 8 | Message interface | ⚪ |
| Context assembler | Intelligence Eng | 10 | Context retrieval system | ⚪ |
| MiniMax 2.7 integration | Intelligence Eng | 8 | Agent router | ⚪ |
| Safety filter chain | Ezra (GPT-5.4) | 6 | Response validation | ⚪ |
| **SAFETY AUDIT** | Ezra (GPT-5.4) | 4 | Audit report | ⚪ |
| **Milestone W12:** Chat system live | Ezra | — | 10+ test conversations | ⚪ |

**Phase 3 Deliverable:** Full research intelligence + conversational AI

---

## Phase 4: Safety & Production (Weeks 13-16)

**Goal:** Production hardening, safety validation, launch prep

### Week 13-14: Security & Compliance

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| End-to-end encryption | Pituach | 10 | Data encryption at rest/transit | ⚪ |
| Authentication hardening | Pituach | 8 | MFA, session management | ⚪ |
| HIPAA/GDPR compliance review | Ezra (GPT-5.4) | 6 | Compliance checklist | ⚪ |
| Penetration testing | External | — | Security audit report | ⚪ |
| **Milestone W14:** Security production-ready | Ezra | — | Security sign-off | ⚪ |

### Week 15: Performance & Reliability

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Load testing | Pituach | 8 | Performance benchmarks | ⚪ |
| Database optimization | Pituach | 6 | Query optimization | ⚪ |
| Error handling & monitoring | Pituach | 8 | Alerting, dashboards | ⚪ |
| Disaster recovery | Pituach | 6 | Backup/restore procedures | ⚪ |
| **Milestone W15:** System production-ready | Ezra | — | Load test passing | ⚪ |

### Week 16: Final Validation & Launch Prep

| Task | Owner | Est. Hours | Deliverable | Status |
|------|-------|------------|-------------|--------|
| Complete test coverage | All | 12 | >90% coverage | ⚪ |
| Documentation finalization | Ezra | 8 | User guide, API docs | ⚪ |
| Beta testing setup | Ezra | 4 | TestFlight/Play Console | ⚪ |
| Launch checklist | Ezra | 4 | Go-live procedures | ⚪ |
| **FINAL SAFETY AUDIT** | Ezra (GPT-5.4) | 8 | Comprehensive review | ⚪ |
| **Milestone W16:** LAUNCH READY | Ezra | — | Production deployment | ⚪ |

**Phase 4 Deliverable:** Production-ready, safety-validated system

---

## Critical Milestones

| Milestone | Date | Definition of Done | Owner |
|-----------|------|-------------------|-------|
| **M1: Data Layer** | Week 1 | Event store + models working | Pituach |
| **M2: Course Engine** | Week 2 | Coverage tracking functional | Pituach |
| **M3: Mobile Entry** | Week 3 | Offline-first entry forms | Mobile Lead |
| **M4: Night Safety** | Week 4 | Alarm system 100% tested | Pituach + Ezra |
| **M5: Learning Layer** | Week 5 | Pattern detection active | Intelligence Eng |
| **M6: Intelligence** | Week 6 | Daily briefs generating | Intelligence Eng |
| **M7: Smart Notifications** | Week 7 | Fatigue-resistant alerts | Pituach |
| **MVP: Now Screen** | Week 8 | Demo-ready intelligent app | All |
| **M9: Research Pipeline** | Week 10 | Daily research updates | Intelligence Eng |
| **M10: Watch Screen** | Week 11 | Research briefing UI | Mobile Lead |
| **M11: Chat System** | Week 12 | Ask Pippen functional | All |
| **M12: Security** | Week 14 | Compliance & pentest passed | Pituach + Ezra |
| **M13: Performance** | Week 15 | Production benchmarks met | Pituach |
| **LAUNCH** | Week 16 | Deployed to production | Ezra |

---

## Resource Allocation

### Agent Hours by Phase

| Phase | Pituach (Backend) | Mobile Lead | Intelligence Eng | Ezra (Audit/PM) | Total |
|-------|-------------------|-------------|------------------|-----------------|-------|
| Phase 1 | 44h | 32h | — | 8h | 84h |
| Phase 2 | 22h | 16h | 50h | 8h | 96h |
| Phase 3 | — | 18h | 70h | 10h | 98h |
| Phase 4 | 28h | — | — | 18h | 46h |
| **Total** | **94h** | **66h** | **120h** | **44h** | **324h** |

### Model Usage Budget

| Model | Purpose | Est. Tokens/Week |
|-------|---------|-----------------|
| MiniMax 2.7 | Development, implementation | ~500K |
| GPT-5.4 Codex | Audits, reviews, architecture decisions | ~100K |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Night alarm logic error | Low | Critical | 100% test coverage + GPT-5.4 audit + human review |
| Timeline slip | Medium | Medium | Daily standups, weekly milestones, buffer in Phase 4 |
| Integration complexity | Medium | Medium | API-first design, clear contracts, early integration |
| Research source rate limits | Medium | Low | Cached responses, backoff logic, tiered sources |
| Mobile offline sync bugs | Medium | High | Extensive offline testing, conflict resolution |

---

## Daily Rhythm

### 09:00 IST — Watchdog Check
- Verify all agents responsive
- Check overnight commits
- Validate milestone progress
- Escalate blockers

### 09:30 IST — Team Standup
- Each agent reports:
  - What was completed yesterday
  - What is planned today
  - Any blockers
- Update TEAM_STATUS.md

### 18:00 IST — End-of-Day Reports
- Commit all work
- Update task status in this document
- Write progress summary

### 20:00 IST — Ezra Review
- Review all commits
- Run safety audits on critical code
- Plan next day
- Update sprint documentation

---

## Next Actions

1. **Create GitHub repository** — Ezra
2. **Assign Phase 1 team** — Ezra
3. **Kickoff Phase 1, Week 1** — All
4. **First safety audit (template)** — Ezra

---

**Questions? Updates?** Modify this document and commit. This is the single source of truth.
