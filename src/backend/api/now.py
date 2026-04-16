"""Now screen API endpoint — unified view of all intelligence signals for a patient."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..intelligence.alerts import AlertRouter
from ..intelligence.baseline import BaselineEngine
from ..intelligence.brief import BriefGenerator
from ..intelligence.changes import Change, ChangeDetector
from ..intelligence.patterns import PatternEngine
from ..intelligence.recommendations import Recommendation, RecommendationEngine
from ..intelligence.risk import RiskEngine, RiskScore


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class RecommendationResponse(BaseModel):
    id: str
    priority: str
    category: str
    headline: str
    explanation: str
    suggested_action: str
    confidence: float
    sources: list[str]
    created_at: str


class ChangeResponse(BaseModel):
    metric: str
    direction: str
    delta: float
    delta_pct: float
    summary: str


class RiskScoreResponse(BaseModel):
    patient_id: str
    risk_score: float
    risk_level: str
    confidence: float
    factors: list[dict[str, Any]]
    supporting_events: list[str]
    generated_at: str


class DailyBriefResponse(BaseModel):
    brief_date: str
    patient_id: str
    summary: str
    what_changed: list[str]
    what_matters: list[str]
    recommended_attention: list[str]
    confidence: float
    supporting_events: list[str]
    generated_at: str


class AlertResponse(BaseModel):
    id: str
    patient_id: str
    title: str
    description: str
    rationale: str
    alert_severity: str
    source: str
    source_id: str
    confidence: float
    triggered_by_event_ids: list[str]
    is_acknowledged: bool
    is_dismissed: bool
    created_at: str
    expires_at: Optional[str] = None


class NowScreenResponse(BaseModel):
    patient_id: str
    generated_at: str
    recommendations: list[RecommendationResponse]
    changes: list[ChangeResponse]
    risk: RiskScoreResponse
    brief: DailyBriefResponse
    active_alerts: list[AlertResponse]


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def create_now_router(pool: asyncpg.Pool, alert_router: Optional[AlertRouter] = None) -> APIRouter:
    """
    Build the Now screen router.

    GET /patients/{patient_id}/now
    """
    router = APIRouter(prefix="/patients", tags=["now"])

    @router.get("/{patient_id}/now", response_model=NowScreenResponse)
    async def get_now_screen(patient_id: str) -> NowScreenResponse:
        """
        Unified Now screen — all intelligence signals synthesized.

        Returns:
        - recommendations: top 5 ranked recommendations
        - changes: week-over-week comparisons
        - risk: current overnight risk score
        - brief: today's daily brief
        - active_alerts: unacknowledged alerts
        """
        await _require_patient(pool, patient_id)

        baseline_engine = BaselineEngine(pool)
        pattern_engine = PatternEngine(pool)
        risk_engine = RiskEngine(pool, baseline_engine, pattern_engine)
        change_detector = ChangeDetector(pool)
        rec_engine = RecommendationEngine(pool, baseline_engine, pattern_engine, risk_engine, alert_router)

        # Fetch all signals concurrently
        recommendations, changes, risk, brief, alerts = await asyncio.gather(
            rec_engine.generate_now_recommendations(patient_id, pool),
            change_detector.compare_weeks(patient_id, pool),
            _get_risk(pool, patient_id, risk_engine),
            _get_brief(pool, patient_id),
            _get_alerts(pool, patient_id, alert_router),
        )

        # Use today's brief if available, else generate a placeholder
        if brief is None:
            brief = _placeholder_brief(patient_id)

        if risk is None:
            risk = _placeholder_risk(patient_id)

        return NowScreenResponse(
            patient_id=patient_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            recommendations=[
                RecommendationResponse(
                    id=r.id,
                    priority=r.priority,
                    category=r.category,
                    headline=r.headline,
                    explanation=r.explanation,
                    suggested_action=r.suggested_action,
                    confidence=r.confidence,
                    sources=r.sources,
                    created_at=r.created_at.isoformat(),
                )
                for r in recommendations
            ],
            changes=[
                ChangeResponse(
                    metric=c.metric,
                    direction=c.direction,
                    delta=c.delta,
                    delta_pct=c.delta_pct,
                    summary=c.summary,
                )
                for c in changes
            ],
            risk=RiskScoreResponse(
                patient_id=risk.patient_id,
                risk_score=risk.risk_score,
                risk_level=risk.risk_level,
                confidence=risk.confidence,
                factors=risk.factors,
                supporting_events=risk.supporting_events,
                generated_at=risk.generated_at,
            ),
            brief=DailyBriefResponse(
                brief_date=brief.brief_date,
                patient_id=brief.patient_id,
                summary=brief.summary,
                what_changed=brief.what_changed,
                what_matters=brief.what_matters,
                recommended_attention=brief.recommended_attention,
                confidence=brief.confidence,
                supporting_events=brief.supporting_events,
                generated_at=brief.generated_at,
            ),
            active_alerts=[
                AlertResponse(
                    id=a.id,
                    patient_id=a.patient_id,
                    title=a.title,
                    description=a.description,
                    rationale=a.rationale,
                    alert_severity=a.alert_severity,
                    source=a.source,
                    source_id=a.source_id,
                    confidence=a.confidence,
                    triggered_by_event_ids=a.triggered_by_event_ids,
                    is_acknowledged=a.is_acknowledged,
                    is_dismissed=a.is_dismissed,
                    created_at=a.created_at,
                    expires_at=a.expires_at,
                )
                for a in alerts
            ],
        )

    return router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _require_patient(pool: asyncpg.Pool, patient_id: str) -> None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM patients WHERE id = $1", patient_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )


async def _get_risk(pool: asyncpg.Pool, patient_id: str, risk_engine: RiskEngine) -> Optional[RiskScore]:
    try:
        return await risk_engine.get_risk(patient_id)
    except Exception:
        return None


async def _get_brief(pool: asyncpg.Pool, patient_id: str) -> Optional[Any]:
    import json

    async with pool.acquire() as conn:
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
    if not row:
        return None

    coverage = row["coverage_summary"] or {}
    if isinstance(coverage, str):
        coverage = json.loads(coverage)
    generated_at = coverage.get("generated_at", str(row["created_at"]) if row["created_at"] else "")

    def _load_list(val):
        if isinstance(val, str):
            val = json.loads(val)
        return list(val) if val else []

    from ..intelligence.brief import DailyBrief

    return DailyBrief(
        brief_date=str(row["brief_date"]),
        patient_id=str(row["patient_id"]),
        summary=row["summary"] or "",
        what_changed=_load_list(row["key_insights"]),
        what_matters=_load_list(row["risk_alerts"]),
        recommended_attention=_load_list(row["recommendations"]),
        confidence=float(row["confidence"] or 0.5),
        supporting_events=list(coverage.get("supporting_events", [])),
        generated_at=generated_at,
    )


async def _get_alerts(pool: asyncpg.Pool, patient_id: str, alert_router: Optional[AlertRouter]) -> list:
    if alert_router is None:
        return []
    return await alert_router.get_active_alerts(patient_id, limit=10)


def _placeholder_brief(patient_id: str) -> Any:
    from ..intelligence.brief import DailyBrief

    now = datetime.now(timezone.utc)
    return DailyBrief(
        brief_date=now.date().isoformat(),
        patient_id=patient_id,
        summary="No brief generated yet. Log some overnight readings to get started.",
        what_changed=["No recent change signal available."],
        what_matters=["Start logging overnight glucose readings to build baseline."],
        recommended_attention=["Keep your bedtime routine consistent and log doses on time."],
        confidence=0.0,
        supporting_events=[],
        generated_at=now.isoformat(),
    )


def _placeholder_risk(patient_id: str) -> RiskScore:
    now = datetime.now(timezone.utc)
    return RiskScore(
        patient_id=patient_id,
        risk_score=0.0,
        risk_level="low",
        confidence=0.0,
        factors=[],
        supporting_events=[],
        generated_at=now.isoformat(),
    )
