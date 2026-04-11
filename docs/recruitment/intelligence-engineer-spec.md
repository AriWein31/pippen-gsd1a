# Intelligence Engineer — Role Specification

**Project:** Pippen (GSD1A Intelligence OS)  
**Start Date:** Week 5  
**Duration:** Phase 2 onward  
**Default Model:** GPT-5.4 Codex

---

## The Role

Build the intelligence layer for a life-safety medical system.

This role turns raw patient events into useful signal:
- learned timing patterns
- baseline behavior
- overnight instability detection
- risk scoring
- daily brief generation
- later, research ranking and context assembly

This is not generic analytics. The output has to be calm, grounded, and medically defensible.

---

## Responsibilities

### Week 5-6 (Immediate)
- Pattern detection algorithms from event streams
- Patient baselines computation
- Timing personalization for coverage expectations
- Risk engine for overnight instability
- Daily brief generation
- Confidence scoring and rationale traces

### Phase 3+ (Ongoing)
- Research claim ranking
- Narrative change detection
- Patient-specific relevance scoring
- Context assembly for Ask Pippen
- Recommendation generation

---

## Technical Requirements

### Must Have
- Python 3.11+
- Strong event-stream / time-series reasoning
- Statistical thinking without overfitting
- Deterministic or explainable scoring logic
- Clean typed code
- Test-first mindset
- Ability to work with incomplete real-world data

### Nice to Have
- Healthcare analytics experience
- Feature engineering for sparse longitudinal data
- Risk scoring systems
- Recommendation systems with transparent logic
- RAG / retrieval experience for later phases

### Constraints
- No black-box ML in safety-critical paths
- Every risk signal needs traceable rationale
- Must degrade gracefully with sparse data
- Must work with immutable event history

---

## The Test Task

**Scenario:** Build a minimal patient intelligence engine from a small event stream.

**Time Budget:** 3-4 hours  
**Deliverable:** Working Python module + tests + short writeup

### Requirements

Given a patient event stream containing:
- glucose readings
- cornstarch doses
- meals
- symptoms
- coverage course timing

Build a module that returns:

1. **Baselines**
   - overnight average glucose
   - overnight low frequency
   - median time between bedtime cornstarch and next event

2. **Risk Signals**
   - detect likely overnight instability
   - detect repeated late-dose pattern
   - detect clusters of low glucose readings

3. **Daily Brief**
   Return a structured object with:
   - `what_changed`
   - `what_matters`
   - `recommended_attention`
   - `confidence`
   - `supporting_events`

4. **Rules**
   - Must be deterministic
   - Must explain why a signal fired
   - Must handle missing / sparse data cleanly

### Deliverable Shape
- Python package or module
- Typed models / interfaces
- Tests
- README explaining approach, tradeoffs, and what you’d do next

---

## What We’re Looking For

| Criterion | Weight | What We Want |
|-----------|--------|--------------|
| Signal quality | 30% | Useful, grounded pattern detection |
| Reasoning clarity | 25% | Why the system flagged something is obvious |
| Code quality | 20% | Clean, typed, testable |
| Data handling | 15% | Handles sparse/noisy data well |
| Product thinking | 10% | Output is useful in an app, not just technically correct |

---

## Evaluation Process

1. Task assignment
2. Candidate build
3. Ezra audit with GPT-5.4 Codex
4. Comparative scoring
5. Offer

---

## Why This Matters

The intelligence layer decides what the patient sees when they open Pippen.

If it is noisy, it becomes nagging. If it is vague, it becomes useless. If it is wrong, it becomes dangerous.

We need someone who can make strong signal from messy medical reality, and explain every step.
