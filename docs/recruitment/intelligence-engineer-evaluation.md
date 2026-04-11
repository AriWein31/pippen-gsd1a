# Intelligence Engineer Candidate Evaluation

**Date:** 2026-04-11  
**Evaluator:** Ezra (GPT-5.4 Codex)  
**Candidates:** 3  
**Model:** All candidates used GPT-5.4 Codex

---

## Candidate Summary

| # | Repository | Tests | Architecture | Key Strength |
|---|------------|-------|--------------|--------------|
| 1 | pippen-intelligence-candidate-1 | 33 | Full module separation | Most comprehensive test coverage |
| 2 | pippen-intelligence-candidate-2 | 4 | Clean single-module | Fast, focused implementation |
| 3 | pippen-intelligence-candidate-3 | 3 | Simple structure | Standard library only, minimal deps |

---

## Detailed Scoring

### Candidate 1: pippen-intelligence-candidate-1

| Criterion | Score | Notes |
|-----------|-------|-------|
| Signal quality | 29/30 | Late dosing, overnight lows, instability all detected with clear thresholds |
| Reasoning clarity | 25/25 | Every signal includes severity, confidence, and supporting event IDs |
| Code quality | 25/25 | Excellent separation: models, baseline, patterns, brief, engine, CLI |
| Data handling | 15/15 | Graceful None returns for sparse data, explicit overnight window handling |
| Product thinking | 10/10 | CLI interface, JSON I/O, documented tradeoffs |
| **Total** | **104/100** | **Bonus for test coverage** |

**Strengths:**
- 33 unit tests — by far the most comprehensive
- Clean architectural separation (6 modules)
- Deterministic confidence scoring based on sample size + pattern strength
- Fixed overnight window (00:00-06:00) with clear rationale
- Pattern detection thresholds are explicit and adjustable

**Tradeoffs documented:**
- Rule-based vs ML (chose interpretability)
- Fixed vs adaptive overnight window
- Confidence formula needs clinical calibration

---

### Candidate 2: pippen-intelligence-candidate-2

| Criterion | Score | Notes |
|-----------|-------|-------|
| Signal quality | 28/30 | Good pattern detection, slightly less nuanced thresholds |
| Reasoning clarity | 24/25 | Clear rationale, good supporting event linking |
| Code quality | 23/25 | Clean but more monolithic structure |
| Data handling | 14/15 | Good sparse handling, one edge case less robust |
| Product thinking | 9/10 | Good CLI, fewer examples |
| **Total** | **98/100** | |

**Strengths:**
- Deterministic rule-based scoring
- 4 pytest tests covering core scenarios
- Clean implementation
- Fast completion (4m10s)

**Weaknesses:**
- Less test coverage than Candidate 1
- Simpler architecture (not necessarily bad, but less production-scalable)

---

### Candidate 3: pippen-intelligence-candidate-3

| Criterion | Score | Notes |
|-----------|-------|-------|
| Signal quality | 27/30 | Good detection, conservative thresholds |
| Reasoning clarity | 24/25 | Clear rationale, good documentation |
| Code quality | 22/25 | Simple structure, standard library only |
| Data handling | 14/15 | Good sparse handling |
| Product thinking | 9/10 | Good README, fewer features |
| **Total** | **96/100** | |

**Strengths:**
- Standard library only (zero dependencies)
- 3 passing tests
- Explicit threshold-based logic
- UTC consistency

**Weaknesses:**
- Fewest tests
- Simplest architecture
- Most conservative feature set

---

## Comparative Analysis

### Test Coverage
**Candidate 1 >> Candidate 2 > Candidate 3**

33 vs 4 vs 3 tests. Candidate 1 thought deeply about edge cases:
- Sparse data scenarios
- Invalid/missing timestamps
- Boundary conditions for thresholds
- JSON serialization

### Architecture Quality
**Candidate 1 > Candidate 2 > Candidate 3**

Candidate 1:
```
src/
├── models.py      # Data types
├── baseline.py    # Computation
├── patterns.py    # Detection
├── brief.py       # Generation
├── engine.py      # Orchestration
└── cli.py         # Interface
```

This separation matters for Week 5-6 when we'll extend the system.

### Signal Quality
All three implemented the core requirements. Candidate 1 had slightly more nuanced detection:
- Late dosing: proportion-based severity (better than binary)
- Low clusters: nights-affected scoring
- Instability: CV change detection with prior comparison

### Determinism & Safety
All three passed — no ML black boxes, all rule-based with explicit thresholds.

---

## Decision

| Rank | Candidate | Score | Verdict |
|------|-----------|-------|---------|
| 1 | pippen-intelligence-candidate-1 | 104/100 | **HIRE** |
| 2 | pippen-intelligence-candidate-2 | 98/100 | Strong backup |
| 3 | pippen-intelligence-candidate-3 | 96/100 | Not selected |

---

## Primary Recommendation: Candidate 1

**Repository:** https://github.com/AriWein31/pippen-intelligence-candidate-1

**Rationale:**
1. **Best test coverage** — 33 tests vs 4 and 3. This matters for medical software.
2. **Best architecture** — Clean separation will scale to Week 5-6 complexity.
3. **Most nuanced signals** — Proportion-based severity, confidence scoring.
4. **Documentation** — Tradeoffs explicitly documented.
5. **Production thinking** — CLI, JSON I/O, error handling.

**Minor concern:** None significant. The fixed overnight window is a reasonable tradeoff for the test task.

---

## Next Steps

1. **Offer Candidate 1** (pippen-intelligence-candidate-1)
2. **If declined:** Offer Candidate 2
3. **Onboarding:** Week 5 start (after Mobile Lead completes Week 4)
4. **First task:** Integrate intelligence engine with Pippen backend

---

*Evaluation by Ezra (GPT-5.4 Codex)*
