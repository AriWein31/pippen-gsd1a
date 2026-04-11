# Sprint 05: Patient Intelligence Layer

**Sprint Duration:** Week 5 (May 10-16, 2026)  
**Goal:** Build pattern detection, baselines, and daily brief generation  
**Lead:** Candidate 1 (Intelligence Engineer)  
**Model:** GPT-5.4 Codex  
**Status:** 🟢 In Progress

---

## Context

Phase 1 (Foundation) is complete:
- ✅ Event-sourced data layer
- ✅ Coverage course engine with state machine
- ✅ Night alarm system with escalation
- ✅ Mobile app with offline-first entry

Now we build the **intelligence layer** that turns raw events into actionable insights.

---

## Week 5 Tasks

### Task 5.1: Baseline Computation Engine (8h)
**Owner:** Intelligence Engineer

Compute patient baselines from event history:

**Metrics to compute:**
- [ ] Overnight average glucose (00:00-06:00)
- [ ] Overnight glucose variability (coefficient of variation)
- [ ] Low glucose frequency (< 70 mg/dL)
- [ ] Median bedtime-to-next-event interval
- [ ] Coverage gap frequency

**Requirements:**
- Minimum 7 days data for baseline (return null if insufficient)
- Rolling window (last 30 days)
- Confidence score based on sample size
- Store in `patient_baselines` table

**Interface:**
```python
class BaselineEngine:
    async def compute_baselines(self, patient_id: str) -> PatientBaselines
    async def get_baseline(self, patient_id: str, metric: str) -> Optional[Baseline]
```

---

### Task 5.2: Pattern Detection Engine (10h)
**Owner:** Intelligence Engineer

Detect clinically relevant patterns from events.

**Patterns to detect:**

1. **Late Bedtime Dosing**
   - Trigger: 2+ cornstarch doses after 22:00 in last 7 days
   - Severity: proportion of late doses
   - Confidence: sample size based

2. **Overnight Low Clusters**
   - Trigger: 2+ glucose readings <70 mg/dL within 2 hours
   - Severity: nights affected in last 7 days
   - Confidence: recency weighted

3. **Recent Instability**
   - Trigger: CV increase >30% in last 3 days vs prior week
   - Severity: magnitude of increase
   - Confidence: data density

**Output format:**
```python
@dataclass
class PatternSignal:
    pattern_type: str
    severity: int  # 1-10
    confidence: float  # 0.0-1.0
    reason: str
    supporting_event_ids: list[str]
    detected_at: datetime
```

**Requirements:**
- Deterministic rule-based detection (no ML)
- Every signal has explainable rationale
- Store in `patient_patterns` table
- Event bus integration (publish `pattern_detected`)

---

### Task 5.3: Daily Brief Generator (8h)
**Owner:** Intelligence Engineer

Generate structured daily intelligence brief.

**Output structure:**
```json
{
  "brief_date": "2026-05-10",
  "patient_id": "uuid",
  "summary": "Overnight lows detected on 2 of last 3 nights",
  "what_changed": [
    "3 overnight lows vs baseline of 1",
    "Bedtime dose timing shifted later"
  ],
  "what_matters": [
    "Coverage gap detected 2:30-2:45 AM",
    "Pattern suggests timing adjustment needed"
  ],
  "recommended_attention": [
    "Consider earlier bedtime dose",
    "Monitor overnight glucose closely"
  ],
  "confidence": 0.81,
  "supporting_events": ["evt-003", "evt-008", "evt-012"],
  "generated_at": "2026-05-10T06:00:00Z"
}
```

**Generation rules:**
- Run daily at 06:00 (patient morning)
- Include only high-confidence signals (>0.7)
- Max 3 items per section
- Rationale must reference specific events

**Requirements:**
- Store in `daily_briefs` table
- API endpoint: `GET /patients/{id}/daily-brief`
- Mobile integration ready

---

### Task 5.4: Risk Scoring (6h)
**Owner:** Intelligence Engineer

Compute risk score for overnight instability.

**Risk factors:**
- Recent low cluster (weight: 3.0)
- Late bedtime dosing trend (weight: 2.0)
- High glucose variability (weight: 2.0)
- Coverage gaps (weight: 2.5)

**Scoring:**
```python
risk_score = sum(factor_severity * weight) / sum(weights)
risk_level = low | medium | high | critical
```

**Thresholds:**
- Low: < 3.0
- Medium: 3.0-5.0
- High: 5.0-7.5
- Critical: > 7.5

**Requirements:**
- Deterministic formula
- Confidence based on data quality
- Store risk history for trending
- Trigger smart notifications (Week 7)

---

### Task 5.5: API Integration (4h)
**Owner:** Intelligence Engineer + Pituach (review)

**Endpoints to add:**
- `GET /patients/{id}/baselines` — Current baselines
- `GET /patients/{id}/patterns` — Active patterns
- `GET /patients/{id}/daily-brief` — Today's brief
- `GET /patients/{id}/risk` — Current risk score
- `POST /admin/regenerate-briefs` — Backfill (admin)

**Requirements:**
- Typed request/response models
- Error handling for insufficient data
- Rate limiting consideration
- Tests for all endpoints

---

## Integration Points

### Event Bus Subscriptions
```python
# On cornstarch_dose logged
await event_bus.subscribe(EventTypes.CORNSTARCH_LOGGED, on_dose_logged)

# On glucose_reading logged
await event_bus.subscribe(EventTypes.GLUCOSE_LOGGED, on_glucose_logged)

# On new day (06:00)
await schedule_daily(daily_brief_generator.run)
```

### Database Tables (Existing)
- `patient_baselines` — Baseline values
- `patient_patterns` — Detected patterns
- `daily_briefs` — Generated briefs
- `events` — Source data (immutable)

---

## Quality Standards

- **Deterministic:** No randomness, same inputs = same outputs
- **Explainable:** Every signal has human-readable rationale
- **Tested:** Unit tests for all engines (>70% coverage)
- **Typed:** All functions have type annotations
- **Documented:** Docstrings and README updates

---

## Definition of Done

- [ ] Baseline engine computes all 5 metrics
- [ ] Pattern detection finds all 3 pattern types
- [ ] Daily brief generates structured output
- [ ] Risk scoring produces levels and confidence
- [ ] API endpoints return JSON responses
- [ ] Tests pass (`pytest`)
- [ ] Ezra audit passed (GPT-5.4 Codex)

---

## Deliverable

**Milestone W5:** System learns patient patterns  
**Measure:** Pattern accuracy >70% (manual spot-check)

---

## References

- Candidate 1 test task: https://github.com/AriWein31/pippen-intelligence-candidate-1
- Test task approach: See README in candidate repo
- Database schema: `src/backend/db/migrations/001_initial_schema.sql`
- Event bus: `src/backend/events/bus.py`
