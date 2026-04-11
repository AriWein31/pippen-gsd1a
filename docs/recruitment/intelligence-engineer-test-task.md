# Intelligence Engineer — Technical Test Task

**Project:** Pippen (GSD1A Intelligence OS)  
**Role:** Intelligence Engineer  
**Time Budget:** 3-4 hours  
**Due:** 48 hours from receiving this task

---

## The Challenge

Build a minimal patient intelligence engine from an event stream for GSD1A care.

This is a simplified version of Pippen Weeks 5-6.

---

## Input Data

You will receive a JSON file of patient events with records like:
- `glucose_reading`
- `cornstarch_dose`
- `meal`
- `symptom`
- `coverage_course_started`
- `coverage_course_closed`

Each record includes timestamps and structured payloads.

---

## Requirements

### 1. Baseline Computation
Return a baseline object with at least:
- overnight average glucose
- overnight glucose variability
- count of low glucose readings (`< 70`)
- median interval from bedtime cornstarch to next relevant event

### 2. Pattern Detection
Detect and return structured signals for:
- repeated late bedtime dosing
- repeated overnight low glucose clusters
- increased overnight instability in the last 3 days versus prior baseline

Each signal must include:
- `type`
- `severity`
- `confidence`
- `reason`
- `supporting_event_ids`

### 3. Daily Brief Generator
Generate a structured daily brief:

```json
{
  "what_changed": ["..."],
  "what_matters": ["..."],
  "recommended_attention": ["..."],
  "confidence": 0.0,
  "supporting_events": ["..."]
}
```

### 4. Constraints
- deterministic logic only
- no external APIs
- no black-box ML
- graceful handling of sparse data
- typed Python
- tests required

---

## Technical Stack

- Python 3.11+
- Standard library preferred
- `pydantic` optional
- `pytest` optional but recommended

---

## Deliverables

1. GitHub repo with:
   - source code
   - tests
   - README
   - sample input data
   - sample output

2. README must include:
   - how to run it
   - how scoring works
   - tradeoffs made
   - what you’d improve with more time

---

## Evaluation Criteria

| Criterion | Weight | What We Look For |
|-----------|--------|------------------|
| Signal quality | 30% | Signals are useful, not noisy |
| Reasoning clarity | 25% | Easy to understand why each signal fired |
| Code quality | 20% | Clean, typed, modular |
| Data handling | 15% | Sparse/noisy data handled well |
| Product thinking | 10% | Output feels app-ready |

---

## Sample Direction

A great solution will probably include:
- event normalization
- windowed aggregations
- simple but strong rule-based scoring
- explicit rationale strings
- confidence based on recency + sample size

It should feel like something a patient intelligence product could actually build on.

---

## Submission

Push repo, include sample outputs, and share the link.

Good luck. Make it useful, not clever.
