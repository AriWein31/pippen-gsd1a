"""Daily brief generation for patient-facing intelligence summaries."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

import asyncpg

from .baseline import BaselineEngine, PatientBaselines
from .patterns import PatternEngine, PatternSignal

BRIEF_SIGNAL_CONFIDENCE_THRESHOLD = 0.7
BRIEF_SECTION_MAX_ITEMS = 3
BRIEF_GENERATION_HOUR = 6


@dataclass
class DailyBrief:
    brief_date: str
    patient_id: str
    summary: str
    what_changed: list[str]
    what_matters: list[str]
    recommended_attention: list[str]
    confidence: float
    supporting_events: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "brief_date": self.brief_date,
            "patient_id": self.patient_id,
            "summary": self.summary,
            "what_changed": self.what_changed,
            "what_matters": self.what_matters,
            "recommended_attention": self.recommended_attention,
            "confidence": self.confidence,
            "supporting_events": self.supporting_events,
            "generated_at": self.generated_at,
        }


class BriefGenerator:
    """Generate and persist daily briefs from baseline and pattern intelligence."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        baseline_engine: Optional[BaselineEngine] = None,
        pattern_engine: Optional[PatternEngine] = None,
    ):
        self.pool = pool
        self.baseline_engine = baseline_engine or BaselineEngine(pool)
        self.pattern_engine = pattern_engine or PatternEngine(pool)

    async def generate_daily_brief(
        self,
        patient_id: str,
        now: Optional[datetime] = None,
    ) -> DailyBrief:
        current_time = now or datetime.now(timezone.utc)
        brief_date = current_time.date()
        generated_at = self._scheduled_generation_time(brief_date)

        baselines = await self.baseline_engine.compute_baselines(patient_id)
        patterns = await self.pattern_engine.compute_patterns(patient_id, now=current_time)
        brief = self._compose_brief(patient_id, baselines, patterns, brief_date, generated_at)
        await self._store_brief(brief)
        return brief

    async def get_daily_brief(
        self,
        patient_id: str,
        brief_date: Optional[date] = None,
        now: Optional[datetime] = None,
    ) -> DailyBrief:
        target_date = brief_date or (now or datetime.now(timezone.utc)).date()
        stored = await self._fetch_brief(patient_id, target_date)
        if stored is not None:
            return stored
        return await self.generate_daily_brief(patient_id, now=now)

    def _compose_brief(
        self,
        patient_id: str,
        baselines: PatientBaselines,
        patterns: list[PatternSignal],
        brief_date: date,
        generated_at: datetime,
    ) -> DailyBrief:
        high_confidence_patterns = [
            pattern for pattern in patterns if pattern.confidence > BRIEF_SIGNAL_CONFIDENCE_THRESHOLD
        ]
        high_confidence_patterns.sort(key=lambda pattern: (-pattern.confidence, -pattern.severity, pattern.pattern_type))
        selected_patterns = high_confidence_patterns[:BRIEF_SECTION_MAX_ITEMS]

        low_metric = baselines.get_metric("overnight_low_glucose_frequency")
        gap_metric = baselines.get_metric("coverage_gap_frequency")
        interval_metric = baselines.get_metric("median_bedtime_to_next_event_interval_minutes")

        what_changed: list[str] = []
        what_matters: list[str] = []
        recommended_attention: list[str] = []
        supporting_events: list[str] = []

        for pattern in selected_patterns:
            event_refs = ", ".join(pattern.supporting_event_ids[:3])
            what_changed.append(f"{pattern.reason} (events: {event_refs})")
            what_matters.append(self._what_matters_for_pattern(pattern))
            recommended_attention.append(self._recommended_attention_for_pattern(pattern))
            supporting_events.extend(pattern.supporting_event_ids)

        if not what_changed and low_metric and low_metric.value is not None and low_metric.confidence > BRIEF_SIGNAL_CONFIDENCE_THRESHOLD:
            low_count = low_metric.metadata.get("low_count", 0)
            event_refs = ", ".join(low_metric.supporting_event_ids[:3])
            what_changed.append(
                f"{low_count} overnight low readings across baseline history, frequency {low_metric.value:.2f}. (events: {event_refs})"
            )
            supporting_events.extend(low_metric.supporting_event_ids)

        if not what_matters and gap_metric and gap_metric.value is not None and gap_metric.confidence > BRIEF_SIGNAL_CONFIDENCE_THRESHOLD:
            event_refs = ", ".join(gap_metric.supporting_event_ids[:3])
            what_matters.append(
                f"Coverage gaps showed up in {gap_metric.value:.0%} of recent courses. (events: {event_refs})"
            )
            supporting_events.extend(gap_metric.supporting_event_ids)

        if not recommended_attention and interval_metric and interval_metric.value is not None and interval_metric.confidence > BRIEF_SIGNAL_CONFIDENCE_THRESHOLD:
            recommended_attention.append(
                f"Keep bedtime follow-up within about {interval_metric.value:.0f} minutes, which matches the current baseline."
            )

        what_changed = what_changed[:BRIEF_SECTION_MAX_ITEMS]
        what_matters = what_matters[:BRIEF_SECTION_MAX_ITEMS]
        recommended_attention = recommended_attention[:BRIEF_SECTION_MAX_ITEMS]
        supporting_events = list(dict.fromkeys(supporting_events))[:10]

        summary = self._summary_for_brief(selected_patterns, low_metric, gap_metric)
        if not what_changed:
            what_changed = ["No high-confidence change signal cleared the threshold this morning."]
        if not what_matters:
            what_matters = ["Baseline looks steady enough to keep watching rather than reacting."]
        if not recommended_attention:
            recommended_attention = ["Stay on the usual overnight plan and keep logging bedtime doses and overnight readings."]

        confidence_inputs = [pattern.confidence for pattern in selected_patterns]
        if not confidence_inputs and low_metric and low_metric.value is not None:
            confidence_inputs.append(low_metric.confidence)
        confidence = round(max(0.71, min(0.95, sum(confidence_inputs) / len(confidence_inputs))) if confidence_inputs else 0.71, 2)

        return DailyBrief(
            brief_date=brief_date.isoformat(),
            patient_id=patient_id,
            summary=summary,
            what_changed=what_changed,
            what_matters=what_matters,
            recommended_attention=recommended_attention,
            confidence=confidence,
            supporting_events=supporting_events,
            generated_at=generated_at.isoformat(),
        )

    async def _store_brief(self, brief: DailyBrief) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO daily_briefs (
                    patient_id, brief_date, summary, key_insights, risk_alerts,
                    recommendations, coverage_summary, generated_by, confidence, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'brief_generator', $8, $9)
                ON CONFLICT (patient_id, brief_date)
                DO UPDATE SET
                    summary = EXCLUDED.summary,
                    key_insights = EXCLUDED.key_insights,
                    risk_alerts = EXCLUDED.risk_alerts,
                    recommendations = EXCLUDED.recommendations,
                    coverage_summary = EXCLUDED.coverage_summary,
                    generated_by = EXCLUDED.generated_by,
                    confidence = EXCLUDED.confidence,
                    created_at = EXCLUDED.created_at
                """,
                brief.patient_id,
                date.fromisoformat(brief.brief_date),
                brief.summary,
                json.dumps(brief.what_changed),
                json.dumps(brief.what_matters),
                json.dumps(brief.recommended_attention),
                json.dumps({
                    "supporting_events": brief.supporting_events,
                    "generated_at": brief.generated_at,
                }),
                brief.confidence,
                datetime.fromisoformat(brief.generated_at),
            )

    async def _fetch_brief(self, patient_id: str, brief_date: date) -> Optional[DailyBrief]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT patient_id, brief_date, summary, key_insights, risk_alerts,
                       recommendations, coverage_summary, confidence, created_at
                FROM daily_briefs
                WHERE patient_id = $1 AND brief_date = $2
                """,
                patient_id,
                brief_date,
            )
        if not row:
            return None
        return self._row_to_brief(row)

    def _row_to_brief(self, row: Any) -> DailyBrief:
        coverage_summary = row["coverage_summary"] or {}
        if isinstance(coverage_summary, str):
            coverage_summary = json.loads(coverage_summary)

        def _load_list(value: Any) -> list[str]:
            if isinstance(value, str):
                value = json.loads(value)
            return list(value or [])

        return DailyBrief(
            brief_date=row["brief_date"].isoformat(),
            patient_id=str(row["patient_id"]),
            summary=row["summary"] or "",
            what_changed=_load_list(row["key_insights"]),
            what_matters=_load_list(row["risk_alerts"]),
            recommended_attention=_load_list(row["recommendations"]),
            confidence=float(row["confidence"]),
            supporting_events=list(coverage_summary.get("supporting_events", [])),
            generated_at=coverage_summary.get("generated_at", row["created_at"].isoformat()),
        )

    def _scheduled_generation_time(self, brief_date: date) -> datetime:
        return datetime.combine(brief_date, time(hour=BRIEF_GENERATION_HOUR), tzinfo=timezone.utc)

    def _summary_for_brief(self, patterns: list[PatternSignal], low_metric: Any, gap_metric: Any) -> str:
        overnight_low = next((p for p in patterns if p.pattern_type == "overnight_low_cluster"), None)
        recent_instability = next((p for p in patterns if p.pattern_type == "recent_instability"), None)
        late_bedtime = next((p for p in patterns if p.pattern_type == "late_bedtime_dosing"), None)

        if overnight_low:
            nights = overnight_low.metadata.get("nights_affected", 0)
            return f"Overnight low clusters showed up on {nights} recent night(s)."
        if recent_instability:
            return "Overnight readings were more variable than the recent baseline."
        if late_bedtime:
            return "Bedtime dosing drifted later than usual this week."
        if low_metric and low_metric.value is not None and low_metric.metadata.get("low_count", 0) > 0:
            return f"Baseline still shows overnight lows at about {low_metric.value:.0%} of readings."
        if gap_metric and gap_metric.value is not None and gap_metric.value > 0:
            return f"Coverage gaps are part of the recent baseline, around {gap_metric.value:.0%} of courses."
        return "No high-confidence overnight change signal was detected this morning."

    def _what_matters_for_pattern(self, pattern: PatternSignal) -> str:
        event_refs = ", ".join(pattern.supporting_event_ids[:3])
        if pattern.pattern_type == "overnight_low_cluster":
            return f"This points to repeat overnight risk, not a one-off, backed by events {event_refs}."
        if pattern.pattern_type == "recent_instability":
            return f"Higher variability can make the next overnight stretch less predictable, backed by events {event_refs}."
        if pattern.pattern_type == "late_bedtime_dosing":
            return f"Later bedtime dosing can shift overnight coverage and make lows harder to avoid, backed by events {event_refs}."
        return f"This signal is worth review, backed by events {event_refs}."

    def _recommended_attention_for_pattern(self, pattern: PatternSignal) -> str:
        if pattern.pattern_type == "overnight_low_cluster":
            return "Review bedtime coverage timing and consider whether the overnight plan needs earlier protection."
        if pattern.pattern_type == "recent_instability":
            return "Watch tonight’s overnight readings more closely because variability has risen above baseline."
        if pattern.pattern_type == "late_bedtime_dosing":
            return "Try to pull bedtime cornstarch back earlier and keep the timing consistent tonight."
        return "Review the supporting events and decide if follow-up is needed."
