"""Baseline computation engine for patient overnight intelligence metrics."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import mean, median
from typing import Any, Optional

import asyncpg

from ..events.bus import EventTypes, get_event_bus
from ..events.store import Event


ROLLING_WINDOW_DAYS = 30
MINIMUM_BASELINE_DAYS = 7
OVERNIGHT_START_HOUR = 0
OVERNIGHT_END_HOUR = 6
LOW_GLUCOSE_THRESHOLD = 70
MAX_INTERVAL_LOOKAHEAD_HOURS = 12


@dataclass
class BaselineMetricResult:
    """Single baseline metric with explainable metadata."""

    metric_type: str
    value: Optional[float]
    unit: str
    confidence: float
    sample_count: int
    qualifying_days: int
    computed_at: datetime
    valid_until: datetime
    rationale: str
    supporting_event_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        """Convert to JSON-serializable record for persistence/API use."""
        return {
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "sample_count": self.sample_count,
            "qualifying_days": self.qualifying_days,
            "computed_at": self.computed_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "rationale": self.rationale,
            "supporting_event_ids": self.supporting_event_ids,
            "metadata": self.metadata,
        }


@dataclass
class PatientBaselines:
    """Collection of baseline metrics for a patient."""

    patient_id: str
    computed_at: datetime
    window_start: datetime
    window_end: datetime
    metrics: dict[str, BaselineMetricResult]

    def get_metric(self, metric_type: str) -> Optional[BaselineMetricResult]:
        """Return a specific baseline metric if available."""
        return self.metrics.get(metric_type)


class BaselineEngine:
    """Compute and store 30-day patient baseline metrics."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def compute_baselines(self, patient_id: str) -> PatientBaselines:
        """Compute and persist all baseline metrics for a patient."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=ROLLING_WINDOW_DAYS)

        events = await self._fetch_events(patient_id, window_start, now)
        courses = await self._fetch_courses(patient_id, window_start, now)

        metrics = self._build_metrics(events, courses, now)
        await self._store_metrics(patient_id, metrics)
        await self._publish_updates(patient_id, metrics)

        return PatientBaselines(
            patient_id=patient_id,
            computed_at=now,
            window_start=window_start,
            window_end=now,
            metrics=metrics,
        )

    async def get_baseline(self, patient_id: str, metric: str) -> Optional[BaselineMetricResult]:
        """Fetch a stored baseline metric for a patient."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT metric_type, metric_value, sample_count, computed_at, valid_until
                FROM patient_baselines
                WHERE patient_id = $1 AND metric_type = $2
                """,
                patient_id,
                metric,
            )

        if not row:
            return None

        metric_value = row["metric_value"]
        if isinstance(metric_value, str):
            metric_value = json.loads(metric_value)

        return BaselineMetricResult(
            metric_type=row["metric_type"],
            value=metric_value.get("value"),
            unit=metric_value.get("unit", "count"),
            confidence=float(metric_value.get("confidence", 0.0)),
            sample_count=int(row["sample_count"]),
            qualifying_days=int(metric_value.get("qualifying_days", 0)),
            computed_at=row["computed_at"],
            valid_until=row["valid_until"],
            rationale=metric_value.get("rationale", ""),
            supporting_event_ids=list(metric_value.get("supporting_event_ids", [])),
            metadata=dict(metric_value.get("metadata", {})),
        )

    async def _fetch_events(
        self,
        patient_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Event]:
        """Load relevant events in chronological order."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, patient_id, event_type, source_type, payload,
                       occurred_at, recorded_at, amends, amended_by
                FROM events
                WHERE patient_id = $1
                  AND occurred_at >= $2
                  AND occurred_at <= $3
                  AND event_type IN ('glucose_reading', 'cornstarch_dose', 'meal', 'symptom')
                ORDER BY occurred_at ASC
                """,
                patient_id,
                window_start,
                window_end,
            )

        return [self._row_to_event(row) for row in rows]

    async def _fetch_courses(
        self,
        patient_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[dict[str, Any]]:
        """Load coverage courses for gap-frequency computation."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, patient_id, started_at, expected_end_at, actual_end_at,
                       gap_minutes, overlap_minutes, trigger_type, is_bedtime_dose
                FROM coverage_courses
                WHERE patient_id = $1
                  AND started_at >= $2
                  AND started_at <= $3
                ORDER BY started_at ASC
                """,
                patient_id,
                window_start,
                window_end,
            )

        return [dict(row) for row in rows]

    def _build_metrics(
        self,
        events: list[Event],
        courses: list[dict[str, Any]],
        computed_at: datetime,
    ) -> dict[str, BaselineMetricResult]:
        overnight_glucose = [
            event for event in events
            if event.event_type == "glucose_reading" and self._is_overnight(event.occurred_at)
        ]
        overnight_values = [float(event.payload["value_mg_dl"]) for event in overnight_glucose]
        overnight_days = {self._local_day_key(event.occurred_at) for event in overnight_glucose}

        bedtime_intervals = self._compute_bedtime_intervals(events)
        bedtime_days = {interval["day_key"] for interval in bedtime_intervals}

        gap_courses = [course for course in courses if course.get("gap_minutes") is not None]
        gap_days = {self._local_day_key(course["started_at"]) for course in gap_courses}

        return {
            "overnight_average_glucose": self._metric_from_values(
                metric_type="overnight_average_glucose",
                values=overnight_values,
                unit="mg/dL",
                computed_at=computed_at,
                qualifying_days=len(overnight_days),
                supporting_event_ids=[event.id for event in overnight_glucose],
                rationale_template="Computed mean from {sample_count} overnight glucose readings across {qualifying_days} nights.",
            ),
            "overnight_glucose_variability_cv": self._metric_from_variability(
                overnight_values,
                computed_at,
                len(overnight_days),
                [event.id for event in overnight_glucose],
            ),
            "overnight_low_glucose_frequency": self._metric_from_low_frequency(
                overnight_values,
                computed_at,
                len(overnight_days),
                [event.id for event in overnight_glucose],
            ),
            "median_bedtime_to_next_event_interval_minutes": self._metric_from_bedtime_intervals(
                bedtime_intervals,
                computed_at,
                len(bedtime_days),
            ),
            "coverage_gap_frequency": self._metric_from_gap_frequency(
                gap_courses,
                computed_at,
                len(gap_days),
            ),
        }

    def _metric_from_values(
        self,
        metric_type: str,
        values: list[float],
        unit: str,
        computed_at: datetime,
        qualifying_days: int,
        supporting_event_ids: list[str],
        rationale_template: str,
    ) -> BaselineMetricResult:
        sample_count = len(values)
        if qualifying_days < MINIMUM_BASELINE_DAYS or sample_count == 0:
            return self._insufficient_metric(metric_type, unit, computed_at, sample_count, qualifying_days)

        metric_value = round(mean(values), 2)
        confidence = self._confidence_from_days(qualifying_days)
        return BaselineMetricResult(
            metric_type=metric_type,
            value=metric_value,
            unit=unit,
            confidence=confidence,
            sample_count=sample_count,
            qualifying_days=qualifying_days,
            computed_at=computed_at,
            valid_until=computed_at + timedelta(days=1),
            rationale=rationale_template.format(sample_count=sample_count, qualifying_days=qualifying_days),
            supporting_event_ids=supporting_event_ids,
            metadata={"window_days": ROLLING_WINDOW_DAYS},
        )

    def _metric_from_variability(
        self,
        values: list[float],
        computed_at: datetime,
        qualifying_days: int,
        supporting_event_ids: list[str],
    ) -> BaselineMetricResult:
        sample_count = len(values)
        if qualifying_days < MINIMUM_BASELINE_DAYS or sample_count < 2:
            return self._insufficient_metric(
                "overnight_glucose_variability_cv",
                "ratio",
                computed_at,
                sample_count,
                qualifying_days,
            )

        avg = mean(values)
        if avg <= 0:
            return self._insufficient_metric(
                "overnight_glucose_variability_cv",
                "ratio",
                computed_at,
                sample_count,
                qualifying_days,
            )

        variance = sum((value - avg) ** 2 for value in values) / sample_count
        cv = round(math.sqrt(variance) / avg, 4)
        return BaselineMetricResult(
            metric_type="overnight_glucose_variability_cv",
            value=cv,
            unit="ratio",
            confidence=self._confidence_from_days(qualifying_days),
            sample_count=sample_count,
            qualifying_days=qualifying_days,
            computed_at=computed_at,
            valid_until=computed_at + timedelta(days=1),
            rationale=f"Computed coefficient of variation from {sample_count} overnight glucose readings across {qualifying_days} nights.",
            supporting_event_ids=supporting_event_ids,
            metadata={"window_days": ROLLING_WINDOW_DAYS, "mean_glucose": round(avg, 2)},
        )

    def _metric_from_low_frequency(
        self,
        values: list[float],
        computed_at: datetime,
        qualifying_days: int,
        supporting_event_ids: list[str],
    ) -> BaselineMetricResult:
        sample_count = len(values)
        if qualifying_days < MINIMUM_BASELINE_DAYS or sample_count == 0:
            return self._insufficient_metric(
                "overnight_low_glucose_frequency",
                "ratio",
                computed_at,
                sample_count,
                qualifying_days,
            )

        low_count = sum(1 for value in values if value < LOW_GLUCOSE_THRESHOLD)
        frequency = round(low_count / sample_count, 4)
        return BaselineMetricResult(
            metric_type="overnight_low_glucose_frequency",
            value=frequency,
            unit="ratio",
            confidence=self._confidence_from_days(qualifying_days),
            sample_count=sample_count,
            qualifying_days=qualifying_days,
            computed_at=computed_at,
            valid_until=computed_at + timedelta(days=1),
            rationale=f"Detected {low_count} low overnight glucose readings out of {sample_count} readings across {qualifying_days} nights.",
            supporting_event_ids=supporting_event_ids,
            metadata={"window_days": ROLLING_WINDOW_DAYS, "low_threshold_mg_dl": LOW_GLUCOSE_THRESHOLD, "low_count": low_count},
        )

    def _metric_from_bedtime_intervals(
        self,
        intervals: list[dict[str, Any]],
        computed_at: datetime,
        qualifying_days: int,
    ) -> BaselineMetricResult:
        sample_count = len(intervals)
        if qualifying_days < MINIMUM_BASELINE_DAYS or sample_count == 0:
            return self._insufficient_metric(
                "median_bedtime_to_next_event_interval_minutes",
                "minutes",
                computed_at,
                sample_count,
                qualifying_days,
            )

        minutes = [float(interval["minutes"]) for interval in intervals]
        supporting_ids = [event_id for interval in intervals for event_id in interval["supporting_event_ids"]]
        return BaselineMetricResult(
            metric_type="median_bedtime_to_next_event_interval_minutes",
            value=round(median(minutes), 2),
            unit="minutes",
            confidence=self._confidence_from_days(qualifying_days),
            sample_count=sample_count,
            qualifying_days=qualifying_days,
            computed_at=computed_at,
            valid_until=computed_at + timedelta(days=1),
            rationale=f"Computed median time from bedtime cornstarch dose to next patient event using {sample_count} bedtime doses across {qualifying_days} nights.",
            supporting_event_ids=supporting_ids,
            metadata={"window_days": ROLLING_WINDOW_DAYS},
        )

    def _metric_from_gap_frequency(
        self,
        courses: list[dict[str, Any]],
        computed_at: datetime,
        qualifying_days: int,
    ) -> BaselineMetricResult:
        sample_count = len(courses)
        if qualifying_days < MINIMUM_BASELINE_DAYS or sample_count == 0:
            return self._insufficient_metric(
                "coverage_gap_frequency",
                "ratio",
                computed_at,
                sample_count,
                qualifying_days,
            )

        gap_count = sum(1 for course in courses if (course.get("gap_minutes") or 0) > 0)
        supporting_course_ids = [str(course["id"]) for course in courses]
        return BaselineMetricResult(
            metric_type="coverage_gap_frequency",
            value=round(gap_count / sample_count, 4),
            unit="ratio",
            confidence=self._confidence_from_days(qualifying_days),
            sample_count=sample_count,
            qualifying_days=qualifying_days,
            computed_at=computed_at,
            valid_until=computed_at + timedelta(days=1),
            rationale=f"Computed coverage gap frequency from {gap_count} gap-bearing courses out of {sample_count} linked courses across {qualifying_days} days.",
            supporting_event_ids=supporting_course_ids,
            metadata={"window_days": ROLLING_WINDOW_DAYS, "gap_count": gap_count},
        )

    def _insufficient_metric(
        self,
        metric_type: str,
        unit: str,
        computed_at: datetime,
        sample_count: int,
        qualifying_days: int,
    ) -> BaselineMetricResult:
        return BaselineMetricResult(
            metric_type=metric_type,
            value=None,
            unit=unit,
            confidence=0.0,
            sample_count=sample_count,
            qualifying_days=qualifying_days,
            computed_at=computed_at,
            valid_until=computed_at + timedelta(days=1),
            rationale=(
                f"Insufficient data for baseline. Need at least {MINIMUM_BASELINE_DAYS} qualifying days "
                f"in the last {ROLLING_WINDOW_DAYS} days, found {qualifying_days}."
            ),
            metadata={"window_days": ROLLING_WINDOW_DAYS, "minimum_days_required": MINIMUM_BASELINE_DAYS},
        )

    def _compute_bedtime_intervals(self, events: list[Event]) -> list[dict[str, Any]]:
        intervals: list[dict[str, Any]] = []
        for index, event in enumerate(events):
            if event.event_type != "cornstarch_dose":
                continue
            if not bool(event.payload.get("is_bedtime_dose", False)):
                continue

            next_event = None
            for candidate in events[index + 1:]:
                if candidate.occurred_at <= event.occurred_at:
                    continue
                if candidate.occurred_at - event.occurred_at > timedelta(hours=MAX_INTERVAL_LOOKAHEAD_HOURS):
                    break
                next_event = candidate
                break

            if next_event is None:
                continue

            delta_minutes = (next_event.occurred_at - event.occurred_at).total_seconds() / 60
            intervals.append(
                {
                    "minutes": round(delta_minutes, 2),
                    "day_key": self._local_day_key(event.occurred_at),
                    "supporting_event_ids": [event.id, next_event.id],
                }
            )
        return intervals

    async def _store_metrics(self, patient_id: str, metrics: dict[str, BaselineMetricResult]) -> None:
        async with self.pool.acquire() as conn:
            for metric in metrics.values():
                await conn.execute(
                    """
                    INSERT INTO patient_baselines (
                        id, patient_id, metric_type, metric_value,
                        computed_from_events, sample_count, computed_at, valid_until
                    ) VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (patient_id, metric_type)
                    DO UPDATE SET
                        metric_value = EXCLUDED.metric_value,
                        computed_from_events = EXCLUDED.computed_from_events,
                        sample_count = EXCLUDED.sample_count,
                        computed_at = EXCLUDED.computed_at,
                        valid_until = EXCLUDED.valid_until
                    """,
                    patient_id,
                    metric.metric_type,
                    json.dumps(metric.to_record()),
                    json.dumps(metric.supporting_event_ids),
                    metric.sample_count,
                    metric.computed_at,
                    metric.valid_until,
                )

    async def _publish_updates(self, patient_id: str, metrics: dict[str, BaselineMetricResult]) -> None:
        bus = get_event_bus()
        for metric in metrics.values():
            await bus.publish(
                EventTypes.BASELINE_UPDATED,
                {
                    "patient_id": patient_id,
                    "metric_type": metric.metric_type,
                    "baseline": metric.to_record(),
                    "sample_count": metric.sample_count,
                    "computed_from": metric.supporting_event_ids,
                },
            )

    def _row_to_event(self, row: Any) -> Event:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return Event(
            id=str(row["id"]),
            patient_id=str(row["patient_id"]),
            event_type=row["event_type"],
            source_type=row["source_type"],
            payload=payload,
            occurred_at=row["occurred_at"],
            recorded_at=row["recorded_at"],
            amends=row.get("amends") if hasattr(row, "get") else row["amends"],
            amended_by=row.get("amended_by") if hasattr(row, "get") else row["amended_by"],
        )

    def _is_overnight(self, occurred_at: datetime) -> bool:
        local_time = occurred_at.astimezone(timezone.utc)
        return OVERNIGHT_START_HOUR <= local_time.hour < OVERNIGHT_END_HOUR

    def _local_day_key(self, occurred_at: datetime) -> str:
        return occurred_at.astimezone(timezone.utc).date().isoformat()

    def _confidence_from_days(self, qualifying_days: int) -> float:
        return round(min(1.0, qualifying_days / 14), 2)
