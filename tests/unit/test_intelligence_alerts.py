"""Unit tests for the AlertDecisionEngine — Week 7 notification decision logic.

Tests are deterministic: same inputs → same outputs regardless of test order.
"""

import json
import sys
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from backend.events.bus import InMemoryEventBus, set_event_bus
from backend.intelligence.alerts import (
    AlertDecisionEngine,
    AlertRouter,
    _severity_from_pattern_severity,
    _summarize_top_factors,
    PATTERN_ALERT_CONFIDENCE_THRESHOLD,
    PATTERN_ALERT_SEVERITY_THRESHOLD,
    RISK_ALERT_SCORE_THRESHOLD,
    RISK_ALERT_CONFIDENCE_THRESHOLD,
    THROTTLE_WINDOW_HOURS,
)
from backend.intelligence.patterns import PatternSignal
from backend.intelligence.risk import RiskScore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    return AlertDecisionEngine()


# ---------------------------------------------------------------------------
# Pattern signal evaluation
# ---------------------------------------------------------------------------

class TestEvaluatePattern:
    """Pattern alerts fire when BOTH confidence >= 0.70 AND severity >= 3."""

    def test_fires_when_confidence_and_severity_meet_thresholds(self, engine):
        signal = PatternSignal(
            pattern_type="overnight_low_cluster",
            severity=8,  # 8+ maps to high
            confidence=0.85,
            reason="Three readings below 70 mg/dL between 2–4am.",
            supporting_event_ids=["evt-1", "evt-2"],
            detected_at=datetime.now(timezone.utc),
            sample_count=12,
            metadata={},
        )
        decision = engine.evaluate_pattern(signal, "patient-abc")

        assert decision.should_alert is True
        assert decision.alert_severity == "high"  # severity 8 → high
        assert decision.source == "pattern"
        assert decision.source_id == "overnight_low_cluster"
        assert decision.is_throttled is False
        assert "confidence 85% >= 70%" in decision.rationale
        assert "severity 8/10 >= 3/10" in decision.rationale

    def test_no_alert_when_confidence_below_threshold(self, engine):
        signal = PatternSignal(
            pattern_type="overnight_low_cluster",
            severity=7,
            confidence=0.55,  # below 0.70
            reason="Three readings below 70 mg/dL.",
            supporting_event_ids=["evt-1"],
            detected_at=datetime.now(timezone.utc),
            sample_count=5,
            metadata={},
        )
        decision = engine.evaluate_pattern(signal, "patient-abc")

        assert decision.should_alert is False
        assert "Confidence 55%" in decision.rationale
        assert "below the 70% threshold" in decision.rationale

    def test_no_alert_when_severity_below_threshold(self, engine):
        signal = PatternSignal(
            pattern_type="late_bedtime_dosing",
            severity=2,  # below 3
            confidence=0.90,
            reason="Dose taken after 11pm.",
            supporting_event_ids=["evt-1"],
            detected_at=datetime.now(timezone.utc),
            sample_count=3,
            metadata={},
        )
        decision = engine.evaluate_pattern(signal, "patient-abc")

        assert decision.should_alert is False
        assert "Severity 2/10" in decision.rationale
        assert "below the 3/10 threshold" in decision.rationale

    def test_severity_high_for_severity_8_plus(self, engine):
        signal = PatternSignal(
            pattern_type="recent_instability",
            severity=9,
            confidence=0.90,
            reason="CV > 30% over 7 days.",
            supporting_event_ids=[],
            detected_at=datetime.now(timezone.utc),
            sample_count=20,
            metadata={},
        )
        decision = engine.evaluate_pattern(signal, "patient-xyz")

        assert decision.should_alert is True
        assert decision.alert_severity == "high"

    def test_severity_medium_for_severity_5_to_7(self, engine):
        signal = PatternSignal(
            pattern_type="late_bedtime_dosing",
            severity=5,
            confidence=0.75,
            reason="Dose after 10pm.",
            supporting_event_ids=[],
            detected_at=datetime.now(timezone.utc),
            sample_count=6,
            metadata={},
        )
        decision = engine.evaluate_pattern(signal, "patient-xyz")

        assert decision.should_alert is True
        assert decision.alert_severity == "medium"

    def test_severity_low_for_severity_3_to_4(self, engine):
        signal = PatternSignal(
            pattern_type="late_bedtime_dosing",
            severity=3,
            confidence=0.80,
            reason="Dose at 9:45pm.",
            supporting_event_ids=[],
            detected_at=datetime.now(timezone.utc),
            sample_count=4,
            metadata={},
        )
        decision = engine.evaluate_pattern(signal, "patient-xyz")

        assert decision.should_alert is True
        assert decision.alert_severity == "low"


# ---------------------------------------------------------------------------
# Risk score evaluation
# ---------------------------------------------------------------------------

class TestEvaluateRisk:
    """Risk alerts fire when risk_score >= 3.0 AND confidence >= 0.70."""

    def test_fires_when_score_and_confidence_meet_thresholds(self, engine):
        risk = RiskScore(
            patient_id="patient-abc",
            risk_score=5.5,
            risk_level="high",
            confidence=0.85,
            factors=[
                {"factor": "overnight_low_risk", "weight": 0.4, "severity": 7, "confidence": 0.9, "reason": "..."},
                {"factor": "late_dose_risk", "weight": 0.3, "severity": 5, "confidence": 0.8, "reason": "..."},
            ],
            supporting_events=["evt-1", "evt-2"],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        decision = engine.evaluate_risk(risk)

        assert decision.should_alert is True
        assert decision.alert_severity == "high"
        assert decision.source == "risk"
        assert "Risk score 5.5" in decision.rationale
        assert "confidence 85%" in decision.rationale

    def test_no_alert_when_score_below_threshold(self, engine):
        risk = RiskScore(
            patient_id="patient-abc",
            risk_score=2.1,  # below 3.0
            risk_level="low",
            confidence=0.90,
            factors=[],
            supporting_events=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        decision = engine.evaluate_risk(risk)

        assert decision.should_alert is False
        assert "Risk score 2.1" in decision.rationale

    def test_no_alert_when_confidence_below_threshold(self, engine):
        risk = RiskScore(
            patient_id="patient-abc",
            risk_score=5.0,
            risk_level="high",
            confidence=0.55,  # below 0.70
            factors=[],
            supporting_events=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        decision = engine.evaluate_risk(risk)

        assert decision.should_alert is False
        assert "Risk confidence 55%" in decision.rationale

    def test_critical_severity_mapping(self, engine):
        risk = RiskScore(
            patient_id="patient-abc",
            risk_score=9.0,
            risk_level="critical",
            confidence=0.95,
            factors=[],
            supporting_events=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        decision = engine.evaluate_risk(risk)

        assert decision.should_alert is True
        assert decision.alert_severity == "critical"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestSeverityFromPatternSeverity:
    def test_8_plus_returns_high(self):
        assert _severity_from_pattern_severity(8) == "high"
        assert _severity_from_pattern_severity(9) == "high"
        assert _severity_from_pattern_severity(10) == "high"

    def test_5_to_7_returns_medium(self):
        assert _severity_from_pattern_severity(5) == "medium"
        assert _severity_from_pattern_severity(6) == "medium"
        assert _severity_from_pattern_severity(7) == "medium"

    def test_3_to_4_returns_low(self):
        assert _severity_from_pattern_severity(3) == "low"
        assert _severity_from_pattern_severity(4) == "low"


class TestSummarizeTopFactors:
    def test_returns_top_two_factors(self):
        factors = [
            {"factor": "overnight_low_risk", "severity": 8},
            {"factor": "late_dose_risk", "severity": 6},
            {"factor": "short_gap_risk", "severity": 3},
        ]
        summary = _summarize_top_factors(factors)
        # Factor names are humanized (underscores → spaces)
        assert "overnight low risk" in summary
        assert "late dose risk" in summary
        assert "short gap risk" not in summary

    def test_empty_factors_returns_default(self):
        assert _summarize_top_factors([]) == "no specific factor"

    def test_single_factor(self):
        factors = [{"factor": "late_dose_risk", "severity": 5}]
        summary = _summarize_top_factors(factors)
        # Factor names are humanized (underscores → spaces)
        assert "late dose risk" in summary


# ---------------------------------------------------------------------------
# Throttle window constant
# ---------------------------------------------------------------------------

class TestThrottleWindow:
    def test_throttle_window_is_one_hour(self):
        assert THROTTLE_WINDOW_HOURS == 1
