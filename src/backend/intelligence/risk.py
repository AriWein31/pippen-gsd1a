"""Deterministic overnight risk scoring for patient intelligence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg

from .baseline import BaselineEngine, PatientBaselines
from .patterns import PatternEngine, PatternSignal

RISK_WEIGHTS = {
    "overnight_low_cluster": 3.0,
    "late_bedtime_dosing": 2.0,
    "recent_instability": 2.0,
    "coverage_gap_frequency": 2.5,
}


@dataclass
class RiskScore:
    patient_id: str
    risk_score: float
    risk_level: str
    confidence: float
    factors: list[dict[str, Any]] = field(default_factory=list)
    supporting_events: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "factors": self.factors,
            "supporting_events": self.supporting_events,
            "generated_at": self.generated_at,
        }


class RiskEngine:
    """Compute explainable overnight risk from baselines and patterns."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        baseline_engine: Optional[BaselineEngine] = None,
        pattern_engine: Optional[PatternEngine] = None,
    ):
        self.pool = pool
        self.baseline_engine = baseline_engine or BaselineEngine(pool)
        self.pattern_engine = pattern_engine or PatternEngine(pool)

    async def compute_risk(self, patient_id: str, now: Optional[datetime] = None) -> RiskScore:
        current_time = now or datetime.now(timezone.utc)
        baselines = await self.baseline_engine.compute_baselines(patient_id)
        patterns = await self.pattern_engine.compute_patterns(patient_id, now=current_time)
        risk = self._build_risk(patient_id, baselines, patterns, current_time)
        await self._store_risk(risk)
        return risk

    async def get_risk(self, patient_id: str, now: Optional[datetime] = None) -> RiskScore:
        stored = await self._fetch_latest_risk(patient_id)
        if stored is not None:
            return stored
        return await self.compute_risk(patient_id, now=now)

    def _build_risk(
        self,
        patient_id: str,
        baselines: PatientBaselines,
        patterns: list[PatternSignal],
        current_time: datetime,
    ) -> RiskScore:
        pattern_map = {pattern.pattern_type: pattern for pattern in patterns}
        factors: list[dict[str, Any]] = []
        supporting_events: list[str] = []
        weighted_sum = 0.0
        total_weight = 0.0
        confidence_inputs: list[float] = []

        for pattern_type in ("overnight_low_cluster", "late_bedtime_dosing", "recent_instability"):
            pattern = pattern_map.get(pattern_type)
            if not pattern:
                continue
            weight = RISK_WEIGHTS[pattern_type]
            weighted_sum += pattern.severity * weight
            total_weight += weight
            confidence_inputs.append(pattern.confidence)
            supporting_events.extend(pattern.supporting_event_ids)
            factors.append(
                {
                    "factor": pattern_type,
                    "weight": weight,
                    "severity": pattern.severity,
                    "confidence": pattern.confidence,
                    "reason": pattern.reason,
                }
            )

        gap_metric = baselines.get_metric("coverage_gap_frequency")
        if gap_metric and gap_metric.value is not None:
            weight = RISK_WEIGHTS["coverage_gap_frequency"]
            severity = max(1, min(10, round(float(gap_metric.value) * 10)))
            weighted_sum += severity * weight
            total_weight += weight
            confidence_inputs.append(gap_metric.confidence)
            supporting_events.extend(gap_metric.supporting_event_ids)
            factors.append(
                {
                    "factor": "coverage_gap_frequency",
                    "weight": weight,
                    "severity": severity,
                    "confidence": gap_metric.confidence,
                    "reason": gap_metric.rationale,
                }
            )

        risk_score = round(weighted_sum / total_weight, 2) if total_weight else 0.0
        confidence = round(sum(confidence_inputs) / len(confidence_inputs), 2) if confidence_inputs else 0.0

        return RiskScore(
            patient_id=patient_id,
            risk_score=risk_score,
            risk_level=self._risk_level_for_score(risk_score),
            confidence=confidence,
            factors=factors,
            supporting_events=list(dict.fromkeys(supporting_events))[:20],
            generated_at=current_time.isoformat(),
        )

    async def _store_risk(self, risk: RiskScore) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO patient_patterns (
                    id, patient_id, pattern_type, pattern_key, pattern_value,
                    confidence, sample_count, first_observed_at, last_updated
                ) VALUES (gen_random_uuid(), $1, 'overnight_risk', 'current', $2, $3, $4, $5, $5)
                ON CONFLICT (patient_id, pattern_type, pattern_key)
                DO UPDATE SET
                    pattern_value = EXCLUDED.pattern_value,
                    confidence = EXCLUDED.confidence,
                    sample_count = EXCLUDED.sample_count,
                    last_updated = EXCLUDED.last_updated
                """,
                risk.patient_id,
                json.dumps(risk.to_record()),
                risk.confidence,
                len(risk.factors),
                datetime.fromisoformat(risk.generated_at),
            )

    async def _fetch_latest_risk(self, patient_id: str) -> Optional[RiskScore]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT pattern_value
                FROM patient_patterns
                WHERE patient_id = $1 AND pattern_type = 'overnight_risk' AND pattern_key = 'current'
                """,
                patient_id,
            )
        if not row:
            return None
        payload = row["pattern_value"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return RiskScore(
            patient_id=payload["patient_id"],
            risk_score=float(payload["risk_score"]),
            risk_level=payload["risk_level"],
            confidence=float(payload["confidence"]),
            factors=list(payload.get("factors", [])),
            supporting_events=list(payload.get("supporting_events", [])),
            generated_at=payload["generated_at"],
        )

    def _risk_level_for_score(self, risk_score: float) -> str:
        if risk_score > 7.5:
            return "critical"
        if risk_score >= 5.0:
            return "high"
        if risk_score >= 3.0:
            return "medium"
        return "low"
