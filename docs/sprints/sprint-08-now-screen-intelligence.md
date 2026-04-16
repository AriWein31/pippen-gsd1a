# Sprint 08: Now Screen Intelligence — MVP Completion

**Sprint Duration:** Week 8 (April 27 – May 3, 2026)
**Goal:** Synthesize all intelligence signals into a demo-ready Now screen with actionable recommendations
**Lead:** Candidate 1 (intelligence + backend), Candidate 3 (mobile)
**Model:** MiniMax 2.7
**Status:** 🟡 In Progress

---

## Context

Weeks 5–7 built the full intelligence + notification stack:

- `BaselineEngine` — overnight baselines (glucose average, variability, low frequency)
- `PatternEngine` — 3 pattern detectors (late dosing, overnight lows, instability)
- `RiskEngine` — weighted risk score with explainable factors + confidence
- `BriefGenerator` — daily brief: what_changed, what_matters, recommended_attention
- `AlertDecisionEngine` + `AlertRouter` — deterministic alert routing with throttle
- `NotificationDispatcher` — ALARM_TRIGGERED → caregiver Telegram messages
- Mobile `useAlerts` hook + `AlertCard` component (written, not yet wired to real data)

**The gap:** The Now screen has all the intelligence data available via API, but:
1. No unified "recommendation" surface — data is shown as raw panels, not synthesized guidance
2. No "what to do now" output
3. The brief's `recommended_attention` isn't being displayed on mobile
4. No change detection ("what changed since yesterday/yesterday-week")
5. No priority ranking ("what matters most right now")

Week 8 closes that gap. Milestone W8: MVP COMPLETE.

---

## Week 8 Tasks

### Task 8.1: RecommendationEngine (8h)
**Owner:** Candidate 1

Take all intelligence signals and produce structured, actionable recommendations.

**Input signals:**
- Today's brief (`BriefGenerator` output): `what_changed`, `what_matters`, `recommended_attention`
- Latest risk score + factors (`RiskEngine`)
- Active patterns + confidence (`PatternEngine`)
- Active alerts (`AlertRouter`)

**Output schema:**
```typescript
interface Recommendation {
  id: string;
  priority: "critical" | "high" | "medium" | "low";
  category: "glucose" | "timing" | "pattern" | "safety" | "general";
  headline: string;          // e.g. "Late bedtime dose 3 nights in a row"
  explanation: string;       // e.g. "Your last 3 doses were 45-90 min late..."
  suggested_action: string;  // e.g. "Move tonight's dose 30 min earlier"
  confidence: number;        // 0.0-1.0
  sources: string[];          // references to underlying data
  created_at: string;
}
```

**Priority rules (deterministic):**
1. Active unacknowledged alerts → `critical`
2. Risk score ≥ 4.0 → `high`
3. Any pattern with confidence ≥ 0.75 → `high`
4. `recommended_attention` items from brief → mapped to priority
5. Everything else → `medium` or `low`

**Deliverable:** `src/backend/intelligence/recommendations.py` — `RecommendationEngine` class + `Recommendation` dataclass.

---

### Task 8.2: "What Changed" Detection (6h)
**Owner:** Candidate 1

Compare current week vs previous week for key metrics. Produce a `changes` array.

**Comparisons:**
- Average glucose (this week vs last week)
- Low frequency (this week vs last week)
- Variability score (this week vs last week)
- Bedtime dose timing (average this week vs last week)

**Output schema:**
```typescript
interface Change {
  metric: string;
  direction: "up" | "down" | "stable";
  delta: number;         // absolute change
  delta_pct: number;     // percentage change
  summary: string;       // e.g. "Avg glucose up 12% from last week"
}
```

**Deliverable:** `src/backend/intelligence/changes.py` — `ChangeDetector` class.

---

### Task 8.3: Priority Scoring (2h)
**Owner:** Candidate 1

Combine all signals into a single ranked list for the Now screen.

**Ranking algorithm:**
```
score = (risk_score * 0.3) + (pattern_confidence * 0.25) + (alert_severity * 0.25) + (brief_priority * 0.2)
```

Sort recommendations by score descending. Return top 5.

**Deliverable:** Add `rank_recommendations()` function to `recommendations.py`.

---

### Task 8.4: Now Screen API Endpoint (2h)
**Owner:** Candidate 1

New endpoint consumed by mobile:

```
GET /patients/{id}/now
```

**Response:**
```typescript
interface NowScreen {
  patient_id: string;
  generated_at: string;
  recommendations: Recommendation[];    // top 5, ranked
  changes: Change[];                    // this week vs last week
  risk: RiskScore;                      // from RiskEngine
  brief: DailyBrief;                    // today's brief
  active_alerts: Alert[];               // unacknowledged
}
```

**Deliverable:** `src/backend/api/now.py` — `create_now_router()` wired into `main.py`.

---

### Task 8.5: Mobile NowPage Full Integration (8h)
**Owner:** Candidate 3

Rewrite/extend the NowPage to use the `/now` endpoint and display recommendations.

**UI requirements:**
- **Recommendation cards** (replaces or augments raw IntelligenceCard)
  - Priority badge (critical=red, high=orange, medium=amber, low=blue)
  - Pulsing dot for critical/high
  - Headline + explanation + suggested action
  - "Dismiss" / "Done" action
- **Changes panel** — "This week vs last week" summary (compact)
- **Brief panel** — show `what_changed` + `what_matters` (already has `IntelligenceCard` component)
- Loading / insufficient-data / error states

**Deliverable:** Updated `NowPage.tsx`, `IntelligenceCard.tsx` with recommendation rendering.

---

### Task 8.6: End-to-End Test (2h)
**Owner:** Candidate 1

Manual test script to verify the full loop:
1. Insert test glucose/cornstarch events for test patient
2. Call `/patients/{id}/now`
3. Verify response has recommendations, changes, risk, brief
4. Trigger a pattern → verify alert fires → verify Telegram message
5. Verify `/now` includes the alert

**Deliverable:** `scripts/e2e_test_now_screen.sh` — runnable test script.

---

## Files to Create/Modify

### Backend
| File | Change |
|------|--------|
| `src/backend/intelligence/recommendations.py` | NEW — RecommendationEngine |
| `src/backend/intelligence/changes.py` | NEW — ChangeDetector |
| `src/backend/api/now.py` | NEW — Now screen endpoint |
| `src/backend/main.py` | ADD — now router registration |

### Mobile
| File | Change |
|------|--------|
| `src/mobile/src/pages/NowPage.tsx` | UPDATE — recommendation cards + changes panel |
| `src/mobile/src/components/IntelligenceCard.tsx` | UPDATE — render Recommendation type |
| `src/mobile/src/api/client.ts` | ADD — `fetchNow()` |
| `src/mobile/src/hooks/useNow.ts` | NEW — `useNow()` hook (replaces/augments useIntelligence) |

### Tests
| File | Change |
|------|--------|
| `tests/unit/test_intelligence_recommendations.py` | NEW — RecommendationEngine unit tests |
| `tests/unit/test_intelligence_changes.py` | NEW — ChangeDetector unit tests |
| `scripts/e2e_test_now_screen.sh` | NEW — end-to-end test script |

---

## Success Criteria

- [ ] `RecommendationEngine` produces ranked recommendations from all signals
- [ ] `ChangeDetector` compares this week vs last week on key metrics
- [ ] `/patients/{id}/now` returns unified response with all sections
- [ ] Mobile NowPage displays recommendation cards with priority indicators
- [ ] Changes panel shows week-over-week comparison
- [ ] Telegram alert fires and reaches caregiver (tested with real events)
- [ ] All unit tests pass
- [ ] Sprint doc updated with completion status

---

## Sprint 08 Team

| Role | Agent | Model | Tasks |
|------|-------|-------|-------|
| Intelligence Engineer | Candidate 1 | MiniMax 2.7 | 8.1, 8.2, 8.3, 8.4, 8.6 |
| Mobile Lead | Candidate 3 | MiniMax 2.7 | 8.5 |
| Safety Auditor | Ezra | MiniMax 2.7 | Post-sprint audit |

---

**Last Updated:** 2026-04-16
