"""Change detection for the Now screen — compares this week vs last week on key overnight metrics."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Optional

import asyncpg

from ..events.store import Event


STABLE_THRESHOLD_PCT = 10.0  # |delta_pct| < 10% → stable
DIRECTION_UP = "up"
DIRECTION_DOWN = "down"
DIRECTION_STABLE = "stable"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Change:
    """Single metric comparison between two periods."""

    metric: str
    direction: str  # up / down / stable
    delta: float  # absolute change
    delta_pct: float  # percentage change
    summary: str  # human-readable summary string

    def to_record(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "direction": self.direction,
            "delta": self.delta,
            "delta_pct": self.delta_pct,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# ChangeDetector
# ---------------------------------------------------------------------------

class ChangeDetector:
    """
    Compare current-week metrics vs prior-week to produce a `changes` array
    for the Now screen.

    Metrics compared:
    - average glucose (overnight readings)
    - low glucose frequency
    - glucose variability (CV)
    - bedtime dose timing
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def compare_weeks(self, patient_id: str, pool: Optional[asyncpg.Pool] = None) -> list[Change]:
        """
        Compare last 7 days vs days 8-14 and return list of Change objects.
        """
        db_pool = pool or self.pool
        now = datetime.now(timezone.utc)
        week_end = now
        week_start = now - timedelta(days=7)
        prior_end = week_start
        prior_start = week_start - timedelta(days=7)

        async with db_pool.acquire() as conn:
            current_rows = await conn.fetch(
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
                week_start,
                week_end,
            )
            prior_rows = await conn.fetch(
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
                prior_start,
                prior_end,
            )

        current_events = [self._row_to_event(r) for r in current_rows]
        prior_events = [self._row_to_event(r) for r in prior_rows]

        changes: list[Change] = []

        # Average glucose
        current_glucose = [float(e.payload["value_mg_dl"]) for e in current_events if e.event_type == "glucose_reading"]
        prior_glucose = [float(e.payload["value_mg_dl"]) for e in prior_events if e.event_type == "glucose_reading"]
        if current_glucose and prior_glucose:
            changes.append(self._compare_avg_glucose(current_glucose, prior_glucose))

        # Low frequency
        changes.append(self._compare_low_frequency(current_glucose, prior_glucose))

        # Variability
        changes.append(self._compare_variability(current_glucose, prior_glucose))

        # Bedtime dose timing
        current_timing = self._compute_bedtime_timing(current_events)
        prior_timing = self._compute_bedtime_timing(prior_events)
        if current_timing is not None and prior_timing is not None:
            changes.append(self._compare_bedtime_timing(current_timing, prior_timing))

        return [c for c in changes if c is not None]

    # ------------------------------------------------------------------
    # Metric comparators
    # ------------------------------------------------------------------

    def _compare_avg_glucose(
        self,
        current: list[float],
        prior: list[float],
    ) -> Change:
        current_avg = mean(current)
        prior_avg = mean(prior)
        delta = current_avg - prior_avg
        delta_pct = (delta / prior_avg * 100) if prior_avg != 0 else 0.0
        direction = self._direction_from_delta(delta_pct)
        summary = f"Avg glucose {direction} {abs(delta_pct):.0f}% from last week ({prior_avg:.0f} → {current_avg:.0f} mg/dL)"
        return Change(metric="avg_glucose", direction=direction, delta=round(delta, 1), delta_pct=round(delta_pct, 1), summary=summary)

    def _compare_low_frequency(
        self,
        current: list[float],
        prior: list[float],
    ) -> Change:
        LOW_THRESHOLD = 70
        current_low = sum(1 for v in current if v < LOW_THRESHOLD) / max(len(current), 1)
        prior_low = sum(1 for v in prior if v < LOW_THRESHOLD) / max(len(prior), 1)
        delta = current_low - prior_low
        delta_pct = (delta / prior_low * 100) if prior_low != 0 else 0.0
        direction = self._direction_from_delta(delta_pct)
        summary = f"Low glucose frequency {direction} {abs(delta_pct):.0f}% from last week ({prior_low:.0%} → {current_low:.0%})"
        return Change(metric="low_glucose_frequency", direction=direction, delta=round(delta, 4), delta_pct=round(delta_pct, 1), summary=summary)

    def _compare_variability(
        self,
        current: list[float],
        prior: list[float],
    ) -> Change:
        current_cv = self._cv(current)
        prior_cv = self._cv(prior)
        if current_cv is None or prior_cv is None or prior_cv <= 0:
            return Change(metric="glucose_variability", direction="stable", delta=0.0, delta_pct=0.0, summary="Not enough data to compare variability")
        delta = current_cv - prior_cv
        delta_pct = (delta / prior_cv * 100)
        direction = self._direction_from_delta(delta_pct)
        summary = f"Glucose variability {direction} {abs(delta_pct):.0f}% from last week (CV {prior_cv:.3f} → {current_cv:.3f})"
        return Change(metric="glucose_variability", direction=direction, delta=round(delta, 4), delta_pct=round(delta_pct, 1), summary=summary)

    def _compare_bedtime_timing(
        self,
        current_avg: float,
        prior_avg: float,
    ) -> Change:
        delta = current_avg - prior_avg
        delta_pct = (delta / prior_avg * 100) if prior_avg != 0 else 0.0
        direction = self._direction_from_delta(delta_pct)
        summary = f"Avg bedtime dose timing {direction} {abs(delta_pct):.0f}% from last week ({prior_avg:.0f} → {current_avg:.0f} min)"
        return Change(metric="bedtime_dose_timing", direction=direction, delta=round(delta, 1), delta_pct=round(delta_pct, 1), summary=summary)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _direction_from_delta(self, delta_pct: float) -> str:
        if delta_pct > STABLE_THRESHOLD_PCT:
            return DIRECTION_UP
        elif delta_pct < -STABLE_THRESHOLD_PCT:
            return DIRECTION_DOWN
        return DIRECTION_STABLE

    def _cv(self, values: list[float]) -> Optional[float]:
        if len(values) < 2:
            return None
        avg = mean(values)
        if avg <= 0:
            return None
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return math.sqrt(variance) / avg

    def _compute_bedtime_timing(self, events: list[Event]) -> Optional[float]:
        """Compute average bedtime dose timing (minutes after 20:00) for events."""
        bedtime_doses = [
            e for e in events
            if e.event_type == "cornstarch_dose"
            and bool(e.payload.get("is_bedtime_dose", False))
        ]
        if not bedtime_doses:
            return None
        # Bedtime = after 20:00, so compute minutes past 20:00
        timings = []
        for event in bedtime_doses:
            local_time = event.occurred_at.astimezone(timezone.utc)
            # If before 06:00, treat as late night (same calendar day bedtime)
            if local_time.hour < 6:
                # Same day's bedtime dose (before midnight or after midnight before 6am)
                pass
            elif local_time.hour >= 20:
                minutes_past = (local_time.hour - 20) * 60 + local_time.minute
            else:
                continue
            timings.append(minutes_past)
        if not timings:
            return None
        return mean(timings)

    def _row_to_event(self, row) -> Event:
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
            amends=row.get("amends"),
            amended_by=row.get("amended_by"),
        )
