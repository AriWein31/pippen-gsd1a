# Pippen Milestones

**Tracking document for all project deliverables.**

---

## Phase 1: Foundation (Weeks 1-4)

### Milestone 1: Data Layer (End of Week 1)
**Owner:** Pituach  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] PostgreSQL schema created (`src/backend/db/migrations/`)
- [ ] Event store implementation (`src/backend/events/`)
- [ ] Patient/Caregiver models (`src/backend/models/`)
- [ ] API endpoints for basic CRUD (`src/backend/api/`)
- [ ] Integration tests passing (`tests/integration/`)

#### Definition of Done
- Database migrations run successfully
- Event append/query API tested
- 100% test coverage on data layer
- Ezra (GPT-5.4) code review passed

---

### Milestone 2: Coverage Course Engine (End of Week 2)
**Owner:** Pituach  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] Coverage course state machine
- [ ] Course chain linking logic
- [ ] Manual entry APIs (glucose, cornstarch, meals)
- [ ] Basic coverage timeline calculation
- [ ] End-to-end test: log dose → track coverage

#### Definition of Done
- Course tracking works for 5.15h cornstarch
- Course tracking works for 2h meals
- Chain linking handles overlapping courses
- API documentation complete

---

### Milestone 3: Mobile Entry (End of Week 3)
**Owner:** Mobile Lead  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] React Native / PWA project scaffold
- [ ] Bottom navigation (5 tabs)
- [ ] Entry forms: glucose, cornstarch, meal
- [ ] Offline-first SQLite storage
- [ ] Sync queue implementation

#### Definition of Done
- App installs and runs on iPhone
- Forms work offline
- Data syncs when online
- UI matches design system

---

### Milestone 4: Night Safety (End of Week 4) ⭐ CRITICAL
**Owner:** Pituach + Ezra  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] Alarm daemon (dedicated process)
- [ ] State machine: warning → expired → alarm → escalated
- [ ] Telegram bot integration
- [ ] Escalation chain logic
- [ ] Push notification integration
- [ ] **SAFETY AUDIT REPORT** (Ezra)

#### Definition of Done
- 100% test coverage on alarm logic
- All state transitions tested
- Escalation chain tested end-to-end
- GPT-5.4 Codex safety audit passed
- No critical or high-severity issues

---

## Phase 2: Intelligence (Weeks 5-8)

### Milestone 5: Learning Layer (End of Week 5)
**Owner:** Intelligence Engineer  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] Pattern detection algorithms
- [ ] Baseline computation system
- [ ] Timing personalization (25th percentile)
- [ ] PatientPatterns table population

#### Definition of Done
- Patterns detected from 7+ days of data
- Baseline accuracy >70%
- Timing personalized to patient

---

### Milestone 6: Intelligence Engine (End of Week 6)
**Owner:** Intelligence Engineer  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] Risk scoring matrix
- [ ] Anomaly detection (overnight lows)
- [ ] Daily brief generator
- [ ] Confidence scoring for all insights

#### Definition of Done
- Daily briefs generating automatically
- Risk scores correlate with actual events
- Confidence levels reasonable

---

### Milestone 7: Smart Notifications (End of Week 7)
**Owner:** Pituach + Mobile Lead  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] Notification router
- [ ] Fatigue prevention (throttling)
- [ ] Priority-based routing
- [ ] In-app notification UI

#### Definition of Done
- Notifications respect user preferences
- No notification spam
- Quiet hours respected

---

### Milestone MVP: Now Screen Intelligence (End of Week 8) ⭐ MVP
**Owner:** All  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] "What changed" detection
- [ ] "What matters" ranking
- [ ] "What to do" recommendations
- [ ] Now screen fully integrated
- [ ] **SAFETY AUDIT REPORT** (Ezra)

#### Definition of Done
- Demo can be shown to users
- All 5 screens functional
- Intelligence visible in app
- No critical bugs

---

## Phase 3: Research & Chat (Weeks 9-12)

### Milestone 9: Research Pipeline (End of Week 10)
**Owner:** Intelligence Engineer  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] 10+ research sources configured
- [ ] PubMed API integration
- [ ] ClinicalTrials.gov integration
- [ ] Web scrapers for advocacy/sponsors
- [ ] Claim extraction pipeline

#### Definition of Done
- Daily research updates flowing
- Claims extracted and stored
- Sources ranked by trust tier

---

### Milestone 10: Watch Screen (End of Week 11)
**Owner:** Mobile Lead + Intelligence Engineer  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] Watch tab UI
- [ ] Research briefing cards
- [ ] Narrative change detection
- [ ] Tracked trials list

#### Definition of Done
- 5+ daily research updates visible
- Change detection working
- UI matches design spec

---

### Milestone 11: Ask Pippen Chat (End of Week 12)
**Owner:** All  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] Chat UI
- [ ] Context assembler
- [ ] MiniMax 2.7 integration
- [ ] Safety filter chain
- [ ] **SAFETY AUDIT REPORT** (Ezra)

#### Definition of Done
- 10+ test conversations successful
- Answers grounded in patient data
- No medical misinformation
- Safety filters working

---

## Phase 4: Production (Weeks 13-16)

### Milestone 12: Security (End of Week 14)
**Owner:** Pituach + Ezra  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] End-to-end encryption
- [ ] Authentication hardening
- [ ] HIPAA/GDPR compliance
- [ ] Penetration test report

#### Definition of Done
- Security audit passed
- Compliance checklist complete
- No critical vulnerabilities

---

### Milestone 13: Performance (End of Week 15)
**Owner:** Pituach  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] Load testing results
- [ ] Database optimization
- [ ] Monitoring dashboards
- [ ] Disaster recovery procedures

#### Definition of Done
- Handles 1000+ concurrent users
- <200ms API response time
- 99.9% uptime target

---

### Milestone LAUNCH: Production Ready (End of Week 16) ⭐ FINAL
**Owner:** Ezra  
**Status:** ⚪ Not Started

#### Deliverables
- [ ] >90% test coverage
- [ ] User documentation
- [ ] API documentation
- [ ] Beta testing setup
- [ ] **FINAL SAFETY AUDIT** (Ezra)
- [ ] Launch checklist complete

#### Definition of Done
- Production deployment successful
- All safety audits passed
- Beta users onboarded
- System monitoring active

---

## Progress Summary

| Phase | Milestones | Completed | Progress |
|-------|------------|-----------|----------|
| Phase 1 | 4 | 0 | 0% |
| Phase 2 | 4 | 0 | 0% |
| Phase 3 | 3 | 0 | 0% |
| Phase 4 | 3 | 0 | 0% |
| **Total** | **14** | **0** | **0%** |

---

**Last Updated:** 2026-04-11
