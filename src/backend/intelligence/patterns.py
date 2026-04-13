"""Deterministic pattern detection engine for patient event streams."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from statistics import mean
from typing import Any, Optional

import asyncpg

from ..events.bus import EventTypes, get_event_bus
from ..events.store import Event

LATE_BEDTIME_THRESHOLD = time(22, 0)
LOW_GLUCOSE_THRESHOLD = 70
OVERNIGHT_START_HOUR = 0
OVERNIGHT_END_HOUR = 6
LATE_BEDTIME_WINDOW_DAYS = 7
LOW_CLUSTER_WINDOW_DAYS = 7
LOW_CLUSTER_HOURS = 2
RECENT_WINDOW_DAYS = 3
PRIOR_WINDOW_DAYS = 7
MIN_INSTABILITY_READINGS_PER_WINDOW = 3
MIN_INSTABILITY_NIGHTS_PER_WINDOW = 2


@dataclass
class PatternSignal:
    pattern_type: str
    severity: int
    confidence: float
    reason: str
    supporting_event_ids: list[str]
    detected_at: datetime
    sample_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pattern_key(self) -> str:
        return self.pattern_type

    def to_record(self) -> dict[str, Any]:
        return {
            "pattern_type": self.pattern_type,
            "pattern_key": self.pattern_key,
            "severity": self.severity,
            "confidence": self.confidence,
            "reason": self.reason,
            "supporting_event_ids": self.supporting_event_ids,
            "detected_at": self.detected_at.isoformat(),
            "sample_count": self.sample_count,
            "metadata": self.metadata,
        }


class PatternEngine:
    """Detect, persist, and publish explainable patient patterns."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def compute_patterns(self, patient_id: str, now: Optional[datetime] = None) -> list[PatternSignal]:
        detected_at = now or datetime.now(timezone.utc)
        window_start = detected_at - timedelta(days=PRIOR_WINDOW_DAYS + RECENT_WINDOW_DAYS)
        events = await self._fetch_events(patient_id, window_start, detected_at)

        signals = self.detect_patterns(events, detected_at)
        await self._store_patterns(patient_id, signals)
        await self._publish_patterns(patient_id, signals)
        return signals

    def detect_patterns(self, events: list[Event], detected_at: Optional[datetime] = None) -> list[PatternSignal]:
        when = detected_at or (max((event.occurred_at for event in events), default=datetime.now(timezone.utc)))
        signals: list[PatternSignal] = []

        late_bedtime = self._detect_late_bedtime_dosing(events, when)
        if late_bedtime:
            signals.append(late_bedtime)

        low_clusters = self._detect_overnight_low_clusters(events, when)
        if low_clusters:
            signals.append(low_clusters)

        instability = self._detect_recent_instability(events, when)
        if instability:
            signals.append(instability)

        return signals

    async def _fetch_events(self, patient_id: str, window_start: datetime, window_end: datetime) -> list[Event]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, patient_id, event_type, source_type, payload,
                       occurred_at, recorded_at, amends, amended_by
                FROM events
                WHERE patient_id = $1
                  AND occurred_at >= $2
                  AND occurred_at <= $3
                  AND event_type IN ('glucose_reading', 'cornstarch_dose')
                ORDER BY occurred_at ASC
                """,
                patient_id,
                window_start,
                window_end,
            )
        return [self._row_to_event(row) for row in rows]

    def _detect_late_bedtime_dosing(self, events: list[Event], detected_at: datetime) -> Optional[PatternSignal]:
        window_start = detected_at - timedelta(days=LATE_BEDTIME_WINDOW_DAYS)
        bedtime_doses = [
            event
            for event in events
            if event.event_type == "cornstarch_dose"
            and bool(event.payload.get("is_bedtime_dose", False))
            and window_start <= event.occurred_at <= detected_at
        ]
        late_doses = [event for event in bedtime_doses if event.occurred_at.astimezone(timezone.utc).time() > LATE_BEDTIME_THRESHOLD]

        if len(late_doses) < 2:
            return None

        sample_count = len(bedtime_doses)
        late_count = len(late_doses)
        proportion = late_count / max(1, sample_count)
        severity = max(1, min(10, math.ceil(proportion * 10)))
        confidence = round(min(1.0, sample_count / 7), 2)
        reason = f"{late_count} of {sample_count} bedtime cornstarch doses in the last 7 days were logged after 22:00."

        return PatternSignal(
            pattern_type="late_bedtime_dosing",
            severity=severity,
            confidence=confidence,
            reason=reason,
            supporting_event_ids=[event.id for event in late_doses],
            detected_at=detected_at,
            sample_count=sample_count,
            metadata={
                "window_days": LATE_BEDTIME_WINDOW_DAYS,
                "late_dose_count": late_count,
                "late_dose_proportion": round(proportion, 4),
                "threshold_time": "22:00",
            },
        )

    def _detect_overnight_low_clusters(self, events: list[Event], detected_at: datetime) -> Optional[PatternSignal]:
        window_start = detected_at - timedelta(days=LOW_CLUSTER_WINDOW_DAYS)
        overnight_lows = [
            event
            for event in events
            if event.event_type == "glucose_reading"
            and window_start <= event.occurred_at <= detected_at
            and self._is_overnight(event.occurred_at)
            and float(event.payload.get("value_mg_dl", 999)) < LOW_GLUCOSE_THRESHOLD
        ]
        if len(overnight_lows) < 2:
            return None

        by_night: dict[str, list[Event]] = {}
        for event in overnight_lows:
            by_night.setdefault(self._overnight_night_key(event.occurred_at), []).append(event)

        clustered_nights: list[tuple[str, list[Event]]] = []
        for night_key, night_events in sorted(by_night.items()):
            sorted_events = sorted(night_events, key=lambda event: event.occurred_at)
            cluster = [sorted_events[0]]
            for event in sorted_events[1:]:
                if (event.occurred_at - cluster[0].occurred_at) <= timedelta(hours=LOW_CLUSTER_HOURS):
                    cluster.append(event)
                else:
                    if len(cluster) >= 2:
                        clustered_nights.append((night_key, cluster.copy()))
                        break
                    cluster = [event]
            else:
                if len(cluster) >= 2:
                    clustered_nights.append((night_key, cluster.copy()))

        if not clustered_nights:
            return None

        nights_affected = len(clustered_nights)
        severity = max(1, min(10, nights_affected * 3))
        recency_bonus = 0.0
        supporting_ids: list[str] = []
        for night_key, cluster in clustered_nights:
            night_date = datetime.fromisoformat(night_key).date()
            days_ago = (detected_at.date() - night_date).days
            recency_bonus += max(0.2, 1 - (days_ago / LOW_CLUSTER_WINDOW_DAYS))
            supporting_ids.extend(event.id for event in cluster)

        confidence = round(min(1.0, recency_bonus / nights_affected), 2)
        reason = f"Detected overnight low-glucose clusters on {nights_affected} night(s) in the last 7 days, with at least 2 readings below 70 mg/dL within 2 hours."

        return PatternSignal(
            pattern_type="overnight_low_cluster",
            severity=severity,
            confidence=confidence,
            reason=reason,
            supporting_event_ids=supporting_ids,
            detected_at=detected_at,
            sample_count=len(overnight_lows),
            metadata={
                "window_days": LOW_CLUSTER_WINDOW_DAYS,
                "nights_affected": nights_affected,
                "low_threshold_mg_dl": LOW_GLUCOSE_THRESHOLD,
                "cluster_window_hours": LOW_CLUSTER_HOURS,
            },
        )

    def _detect_recent_instability(self, events: list[Event], detected_at: datetime) -> Optional[PatternSignal]:
        recent_start = detected_at - timedelta(days=RECENT_WINDOW_DAYS)
        prior_start = recent_start - timedelta(days=PRIOR_WINDOW_DAYS)

        recent_events = [
            event for event in events
            if event.event_type == "glucose_reading"
            and recent_start <= event.occurred_at <= detected_at
            and self._is_overnight(event.occurred_at)
        ]
        prior_events = [
            event for event in events
            if event.event_type == "glucose_reading"
            and prior_start <= event.occurred_at < recent_start
            and self._is_overnight(event.occurred_at)
        ]

        recent_values = [float(event.payload.get("value_mg_dl")) for event in recent_events if event.payload.get("value_mg_dl") is not None]
        prior_values = [float(event.payload.get("value_mg_dl")) for event in prior_events if event.payload.get("value_mg_dl") is not None]
        recent_nights = {self._overnight_night_key(event.occurred_at) for event in recent_events}
        prior_nights = {self._overnight_night_key(event.occurred_at) for event in prior_events}

        if (
            len(recent_values) < MIN_INSTABILITY_READINGS_PER_WINDOW
            or len(prior_values) < MIN_INSTABILITY_READINGS_PER_WINDOW
            or len(recent_nights) < MIN_INSTABILITY_NIGHTS_PER_WINDOW
            or len(prior_nights) < MIN_INSTABILITY_NIGHTS_PER_WINDOW
        ):
            return None

        recent_cv = self._coefficient_of_variation(recent_values)
        prior_cv = self._coefficient_of_variation(prior_values)
        if recent_cv is None or prior_cv is None or prior_cv <= 0:
            return None

        increase_ratio = (recent_cv - prior_cv) / prior_cv
        if increase_ratio <= 0.3:
            return None

        magnitude = min(1.0, (increase_ratio - 0.3) / 0.7)
        severity = max(1, min(10, 4 + math.ceil(magnitude * 6)))
        data_density = min(1.0, (len(recent_values) + len(prior_values)) / 20)
        reason = (
            f"Overnight glucose variability increased by {increase_ratio * 100:.0f}% in the last 3 days "
            f"compared with the prior 7 days (CV {recent_cv:.3f} vs {prior_cv:.3f})."
        )

        return PatternSignal(
            pattern_type="recent_instability",
            severity=severity,
            confidence=round(data_density, 2),
            reason=reason,
            supporting_event_ids=[event.id for event in recent_events],
            detected_at=detected_at,
            sample_count=len(recent_values) + len(prior_values),
            metadata={
                "recent_cv": round(recent_cv, 4),
                "prior_cv": round(prior_cv, 4),
                "increase_ratio": round(increase_ratio, 4),
                "recent_window_days": RECENT_WINDOW_DAYS,
                "prior_window_days": PRIOR_WINDOW_DAYS,
                "recent_readings": len(recent_values),
                "prior_readings": len(prior_values),
            },
        )

    async def _store_patterns(self, patient_id: str, signals: list[PatternSignal]) -> None:
        async with self.pool.acquire() as conn:
            for signal in signals:
                await conn.execute(
                    """
                    INSERT INTO patient_patterns (
                        id, patient_id, pattern_type, pattern_key, pattern_value,
                        confidence, sample_count, first_observed_at, last_updated
                    ) VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $7)
                    ON CONFLICT (patient_id, pattern_type, pattern_key)
                    DO UPDATE SET
                        pattern_value = EXCLUDED.pattern_value,
                        confidence = EXCLUDED.confidence,
                        sample_count = EXCLUDED.sample_count,
                        last_updated = EXCLUDED.last_updated
                    """,
                    patient_id,
                    signal.pattern_type,
                    signal.pattern_key,
                    json.dumps(signal.to_record()),
                    signal.confidence,
                    signal.sample_count,
                    signal.detected_at,
                )

    async def _publish_patterns(self, patient_id: str, signals: list[PatternSignal]) -> None:
        bus = get_event_bus()
        for signal in signals:
            await bus.publish(
                EventTypes.PATTERN_DETECTED,
                {
                    "patient_id": patient_id,
                    "pattern_type": signal.pattern_type,
                    "pattern_key": signal.pattern_key,
                    "pattern_value": signal.to_record(),
                    "confidence": signal.confidence,
                    "sample_count": signal.sample_count,
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

    def _overnight_night_key(self, occurred_at: datetime) -> str:
        local_time = occurred_at.astimezone(timezone.utc)
        if local_time.hour < 12:
            return (local_time.date() - timedelta(days=1)).isoformat()
        return local_time.date().isoformat()

    def _coefficient_of_variation(self, values: list[float]) -> Optional[float]:
        if len(values) < 2:
            return None
        avg = mean(values)
        if avg <= 0:
            return None
        variance = sum((value - avg) ** 2 for value in values) / len(values)
        return math.sqrt(variance) / avg
