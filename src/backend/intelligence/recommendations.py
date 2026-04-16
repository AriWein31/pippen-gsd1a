"""Recommendation engine for the Now screen — synthesizes all intelligence signals into ranked, actionable guidance."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg

from .alerts import ActiveAlert, AlertRouter
from .baseline import BaselineEngine
from .brief import BriefGenerator, DailyBrief
from .patterns import PatternEngine, PatternSignal
from .risk import RiskEngine, RiskScore


# ---------------------------------------------------------------------------
# Priority rules
# ---------------------------------------------------------------------------

PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

RISK_HIGH_THRESHOLD = 4.0
PATTERN_HIGH_CONFIDENCE = 0.75

# Scoring weights for ranking
WEIGHT_RISK = 0.3
WEIGHT_PATTERN = 0.25
WEIGHT_ALERT = 0.25
WEIGHT_BRIEF = 0.2


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    id: str
    priority: str  # critical / high / medium / low
    category: str  # glucose / timing / pattern / safety / general
    headline: str
    explanation: str
    suggested_action: str
    confidence: float  # 0.0–1.0
    sources: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "priority": self.priority,
            "category": self.category,
            "headline": self.headline,
            "explanation": self.explanation,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
            "sources": self.sources,
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# RecommendationEngine
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """
    Synthesize all available intelligence signals into a ranked list of
    actionable recommendations for the Now screen.

    Input signals:
    - brief: DailyBrief from BriefGenerator
    - risk_score: RiskScore from RiskEngine
    - active_patterns: list[PatternSignal] from PatternEngine
    - active_alerts: list[ActiveAlert] from AlertRouter

    Output:
    - list[Recommendation] — sorted by composite score, top 5
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        baseline_engine: Optional[BaselineEngine] = None,
        pattern_engine: Optional[PatternEngine] = None,
        risk_engine: Optional[RiskEngine] = None,
        alert_router: Optional[AlertRouter] = None,
    ):
        self.pool = pool
        self.baseline_engine = baseline_engine or BaselineEngine(pool)
        self.pattern_engine = pattern_engine or PatternEngine(pool)
        self.risk_engine = risk_engine or RiskEngine(pool, self.baseline_engine, self.pattern_engine)
        self.alert_router = alert_router
        self.brief_generator = BriefGenerator(pool, self.baseline_engine, self.pattern_engine)

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    async def generate_now_recommendations(
        self,
        patient_id: str,
        pool: Optional[asyncpg.Pool] = None,
    ) -> list[Recommendation]:
        """
        Fetch all intelligence signals for a patient and produce ranked recommendations.
        """
        db_pool = pool or self.pool
        now = datetime.now(timezone.utc)

        # Fetch all signals in parallel
        brief, risk, patterns, alerts = await self._fetch_all_signals(patient_id, now)

        # Build recommendation objects for each signal
        recommendations: list[Recommendation] = []

        # From active alerts → critical recommendations
        recommendations.extend(self._recommendations_from_alerts(alerts))

        # From risk score
        if risk:
            recommendations.append(self._recommendation_from_risk(risk))

        # From high-confidence patterns
        for pattern in patterns:
            if pattern.confidence >= PATTERN_HIGH_CONFIDENCE:
                recommendations.append(self._recommendation_from_pattern(pattern))

        # From brief recommended_attention items
        if brief and brief.recommended_attention:
            for i, attention in enumerate(brief.recommended_attention):
                recommendations.append(self._recommendation_from_brief_item(brief, attention, i))

        # Fallback: general recommendations if nothing fired
        if not recommendations:
            recommendations.append(self._fallback_recommendation(now))

        # Rank and return top 5
        ranked = rank_recommendations(recommendations, risk, patterns, alerts, brief)
        return ranked[:5]

    # ------------------------------------------------------------------
    # Signal fetching
    # ------------------------------------------------------------------

    async def _fetch_all_signals(
        self,
        patient_id: str,
        now: datetime,
    ) -> tuple[
        Optional[DailyBrief],
        Optional[RiskScore],
        list[PatternSignal],
        list[ActiveAlert],
    ]:
        async with self.pool.acquire() as conn:
            brief_row, risk_row, patterns_rows, alerts_rows = await asyncio.gather(
                self._fetch_brief(patient_id, now, conn),
                self._fetch_risk(patient_id, conn),
                self._fetch_patterns(patient_id, now, conn),
                self._fetch_alerts(patient_id, conn),
            )

        brief = self._brief_row_to_brief(brief_row) if brief_row else None
        risk = self._risk_row_to_risk(risk_row) if risk_row else None
        patterns = self._pattern_rows_to_signals(patterns_rows)
        alerts = self._alert_rows_to_alerts(alerts_rows)

        return brief, risk, patterns, alerts

    async def _fetch_brief(
        self,
        patient_id: str,
        now: datetime,
        conn: asyncpg.Connection,
    ) -> Optional[dict]:
        row = await conn.fetchrow(
            """
            SELECT patient_id, brief_date, summary, key_insights, risk_alerts,
                   recommendations, coverage_summary, confidence, created_at
            FROM daily_briefs
            WHERE patient_id = $1
            ORDER BY brief_date DESC
            LIMIT 1
            """,
            patient_id,
        )
        return dict(row) if row else None

    async def _fetch_risk(
        self,
        patient_id: str,
        conn: asyncpg.Connection,
    ) -> Optional[dict]:
        row = await conn.fetchrow(
            """
            SELECT pattern_value
            FROM patient_patterns
            WHERE patient_id = $1 AND pattern_type = 'overnight_risk' AND pattern_key = 'current'
            """,
            patient_id,
        )
        return dict(row) if row else None

    async def _fetch_patterns(
        self,
        patient_id: str,
        now: datetime,
        conn: asyncpg.Connection,
    ) -> list[dict]:
        rows = await conn.fetch(
            """
            SELECT pattern_type, pattern_key, pattern_value, confidence, sample_count,
                   first_observed_at, last_updated
            FROM patient_patterns
            WHERE patient_id = $1
              AND pattern_type IN ('late_bedtime_dosing', 'overnight_low_cluster', 'recent_instability')
              AND pattern_key != 'current'
            ORDER BY last_updated DESC
            """,
            patient_id,
        )
        return [dict(row) for row in rows]

    async def _fetch_alerts(
        self,
        patient_id: str,
        conn: asyncpg.Connection,
    ) -> list[dict]:
        rows = await conn.fetch(
            """
            SELECT
                id, patient_id, title, description, rationale,
                priority AS alert_severity,
                recommendation_type AS source,
                alert_source,
                confidence,
                triggered_by_event_ids,
                is_acknowledged, is_dismissed,
                expires_at, created_at
            FROM recommendations
            WHERE patient_id = $1
              AND alert_severity IS NOT NULL
              AND is_dismissed = FALSE
              AND is_acknowledged = FALSE
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY
                CASE alert_severity
                    WHEN 'critical' THEN 1
                    WHEN 'high'     THEN 2
                    WHEN 'medium'  THEN 3
                    WHEN 'low'     THEN 4
                    ELSE 5
                END,
                created_at DESC
            LIMIT 10
            """,
            patient_id,
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Recommendation builders
    # ------------------------------------------------------------------

    def _recommendations_from_alerts(self, alerts: list[ActiveAlert]) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        for alert in alerts:
            recommendations.append(
                Recommendation(
                    id=str(uuid.uuid4()),
                    priority=PRIORITY_CRITICAL,
                    category=self._category_from_source(alert.source),
                    headline=alert.title,
                    explanation=alert.description,
                    suggested_action=alert.rationale,
                    confidence=alert.confidence,
                    sources=alert.triggered_by_event_ids,
                    created_at=datetime.fromisoformat(alert.created_at) if alert.created_at else datetime.now(timezone.utc),
                )
            )
        return recommendations

    def _recommendation_from_risk(self, risk: RiskScore) -> Recommendation:
        # Determine priority from risk
        if risk.risk_score >= RISK_HIGH_THRESHOLD:
            priority = PRIORITY_HIGH
        else:
            priority = PRIORITY_MEDIUM

        top_factors = ", ".join(f["factor"].replace("_", " ") for f in risk.factors[:2]) if risk.factors else "multiple factors"
        headline = f"Overnight risk is {risk.risk_level.upper()} ({risk.risk_score:.1f})"
        explanation = f"Risk driven by: {top_factors}. Confidence in this assessment: {risk.confidence:.0%}."
        suggested_action = self._suggested_action_from_risk(risk)

        return Recommendation(
            id=str(uuid.uuid4()),
            priority=priority,
            category="safety",
            headline=headline,
            explanation=explanation,
            suggested_action=suggested_action,
            confidence=risk.confidence,
            sources=risk.supporting_events,
            created_at=datetime.fromisoformat(risk.generated_at) if risk.generated_at else datetime.now(timezone.utc),
        )

    def _recommendation_from_pattern(self, pattern: PatternSignal) -> Recommendation:
        category = self._category_from_pattern_type(pattern.pattern_type)
        headline = pattern.reason.split(".")[0] if "." in pattern.reason else pattern.reason
        explanation = pattern.reason
        suggested_action = self._suggested_action_from_pattern(pattern)

        return Recommendation(
            id=str(uuid.uuid4()),
            priority=PRIORITY_HIGH,
            category=category,
            headline=headline,
            explanation=explanation,
            suggested_action=suggested_action,
            confidence=pattern.confidence,
            sources=pattern.supporting_event_ids,
            created_at=pattern.detected_at,
        )

    def _recommendation_from_brief_item(
        self,
        brief: DailyBrief,
        attention: str,
        index: int,
    ) -> Recommendation:
        priority = self._priority_from_brief_attention(attention, index)
        category = self._category_from_brief_attention(attention)

        return Recommendation(
            id=str(uuid.uuid4()),
            priority=priority,
            category=category,
            headline=attention,
            explanation=f"Based on overnight intelligence: {brief.summary}",
            suggested_action=attention,
            confidence=brief.confidence,
            sources=brief.supporting_events,
            created_at=datetime.fromisoformat(brief.generated_at) if brief.generated_at else datetime.now(timezone.utc),
        )

    def _fallback_recommendation(self, now: datetime) -> Recommendation:
        return Recommendation(
            id=str(uuid.uuid4()),
            priority=PRIORITY_LOW,
            category="general",
            headline="Baseline overnight metrics are stable",
            explanation="No high-confidence alerts, patterns, or risk signals detected. Continue with current care plan.",
            suggested_action="Keep logging bedtime doses and overnight glucose readings as usual.",
            confidence=0.5,
            sources=[],
            created_at=now,
        )

    # ------------------------------------------------------------------
    # Category / priority helpers
    # ------------------------------------------------------------------

    def _category_from_source(self, source: str) -> str:
        if source == "pattern":
            return "pattern"
        elif source == "risk":
            return "safety"
        return "general"

    def _category_from_pattern_type(self, pattern_type: str) -> str:
        if pattern_type == "late_bedtime_dosing":
            return "timing"
        elif pattern_type == "overnight_low_cluster":
            return "glucose"
        elif pattern_type == "recent_instability":
            return "glucose"
        return "pattern"

    def _category_from_brief_attention(self, attention: str) -> str:
        lower = attention.lower()
        if any(w in lower for w in ["glucose", "low", "overnight"]):
            return "glucose"
        elif any(w in lower for w in ["dose", "timing", "bedtime"]):
            return "timing"
        elif any(w in lower for w in ["risk", "safety", "alert"]):
            return "safety"
        return "general"

    def _priority_from_brief_attention(self, attention: str, index: int) -> str:
        lower = attention.lower()
        if any(w in lower for w in ["review", "watch", "check"]):
            return PRIORITY_HIGH if index == 0 else PRIORITY_MEDIUM
        return PRIORITY_MEDIUM

    def _suggested_action_from_risk(self, risk: RiskScore) -> str:
        if risk.risk_level in ("critical", "high"):
            return "Review overnight care plan with clinical team. Consider closer monitoring tonight."
        elif risk.risk_level == "medium":
            return "Watch tonight's overnight readings more closely than usual."
        return "Continue with standard overnight routine."

    def _suggested_action_from_pattern(self, pattern: PatternSignal) -> str:
        if pattern.pattern_type == "overnight_low_cluster":
            return "Review bedtime coverage timing and consider whether the overnight plan needs earlier protection."
        elif pattern.pattern_type == "late_bedtime_dosing":
            return "Try to pull bedtime cornstarch back earlier and keep the timing consistent tonight."
        elif pattern.pattern_type == "recent_instability":
            return "Watch tonight's overnight readings more closely because variability has risen above baseline."
        return "Review the supporting events and decide if follow-up is needed."

    # ------------------------------------------------------------------
    # Row converters
    # ------------------------------------------------------------------

    def _brief_row_to_brief(self, row: dict) -> Optional[DailyBrief]:
        import json

        coverage = row.get("coverage_summary") or {}
        if isinstance(coverage, str):
            coverage = json.loads(coverage)
        generated_at = coverage.get("generated_at", row.get("created_at", ""))

        def _load_list(val):
            if isinstance(val, str):
                val = json.loads(val)
            return list(val) if val else []

        return DailyBrief(
            brief_date=str(row.get("brief_date", "")),
            patient_id=str(row.get("patient_id", "")),
            summary=row.get("summary") or "",
            what_changed=_load_list(row.get("key_insights")),
            what_matters=_load_list(row.get("risk_alerts")),
            recommended_attention=_load_list(row.get("recommendations")),
            confidence=float(row.get("confidence", 0.5)),
            supporting_events=list(coverage.get("supporting_events", [])),
            generated_at=generated_at,
        )

    def _risk_row_to_risk(self, row: dict) -> Optional[RiskScore]:
        import json

        pv = row.get("pattern_value") or {}
        if isinstance(pv, str):
            pv = json.loads(pv)
        return RiskScore(
            patient_id=pv.get("patient_id", ""),
            risk_score=float(pv.get("risk_score", 0.0)),
            risk_level=pv.get("risk_level", "low"),
            confidence=float(pv.get("confidence", 0.0)),
            factors=list(pv.get("factors", [])),
            supporting_events=list(pv.get("supporting_events", [])),
            generated_at=pv.get("generated_at", ""),
        )

    def _pattern_rows_to_signals(self, rows: list[dict]) -> list[PatternSignal]:
        import json

        signals: list[PatternSignal] = []
        for row in rows:
            pv = row.get("pattern_value") or {}
            if isinstance(pv, str):
                pv = json.loads(pv)
            signals.append(
                PatternSignal(
                    pattern_type=str(row.get("pattern_type", "")),
                    severity=int(pv.get("severity", 0)),
                    confidence=float(pv.get("confidence", 0.0)),
                    reason=str(pv.get("reason", "")),
                    supporting_event_ids=list(pv.get("supporting_event_ids", [])),
                    detected_at=datetime.fromisoformat(str(pv.get("detected_at", datetime.now(timezone.utc).isoformat()))),
                    sample_count=int(row.get("sample_count", 0)),
                    metadata=dict(pv.get("metadata", {})),
                )
            )
        return signals

    def _alert_rows_to_alerts(self, rows: list[dict]) -> list[ActiveAlert]:
        import json

        alerts: list[ActiveAlert] = []
        for row in rows:
            triggered = row.get("triggered_by_event_ids") or []
            if isinstance(triggered, str):
                triggered = json.loads(triggered)
            alerts.append(
                ActiveAlert(
                    id=str(row["id"]),
                    patient_id=str(row["patient_id"]),
                    title=row.get("title") or "",
                    description=row.get("description") or "",
                    rationale=row.get("rationale") or "",
                    alert_severity=row.get("alert_severity") or "medium",
                    source=row.get("alert_source") or row.get("source") or "pattern",
                    source_id=row.get("source") or "",
                    confidence=float(row.get("confidence") or 0.0),
                    triggered_by_event_ids=list(triggered),
                    is_acknowledged=bool(row.get("is_acknowledged")),
                    is_dismissed=bool(row.get("is_dismissed")),
                    created_at=str(row.get("created_at", "")),
                    expires_at=str(row["expires_at"]) if row.get("expires_at") else None,
                )
            )
        return alerts


# ---------------------------------------------------------------------------
# Ranking function
# ---------------------------------------------------------------------------

def rank_recommendations(
    recommendations: list[Recommendation],
    risk: Optional[RiskScore],
    patterns: list[PatternSignal],
    alerts: list[ActiveAlert],
    brief: Optional[DailyBrief],
) -> list[Recommendation]:
    """
    Sort recommendations by composite score and return ordered list.

    Score formula:
        score = (risk_score * 0.3)
              + (pattern_confidence * 0.25)
              + (alert_severity * 0.25)
              + (brief_priority * 0.2)
    """
    priority_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    alert_severity_score = sum(priority_map.get(a.alert_severity, 1) for a in alerts) / max(len(alerts), 1)
    brief_priority_score = sum(priority_map.get(r.priority, 1) for r in recommendations) / max(len(recommendations), 1)
    max_pattern_confidence = max((p.confidence for p in patterns), default=0.0)
    risk_score = risk.risk_score if risk else 0.0

    scored: list[tuple[float, Recommendation]] = []
    for rec in recommendations:
        score = (
            risk_score * WEIGHT_RISK
            + rec.confidence * WEIGHT_PATTERN
            + priority_map.get(rec.priority, 1) / 4.0 * WEIGHT_ALERT * alert_severity_score
            + priority_map.get(rec.priority, 1) / 4.0 * WEIGHT_BRIEF * brief_priority_score
        )
        # Normalize alert component
        alert_component = priority_map.get(rec.priority, 1) / 4.0
        score = (
            risk_score * WEIGHT_RISK
            + rec.confidence * WEIGHT_PATTERN
            + alert_component * WEIGHT_ALERT
            + (priority_map.get(rec.priority, 1) / 4.0) * WEIGHT_BRIEF
        )
        scored.append((score, rec))

    scored.sort(key=lambda x: -x[0])
    return [rec for _, rec in scored]


# ---------------------------------------------------------------------------
# Compatibility import for asyncio.gather
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402, F401
