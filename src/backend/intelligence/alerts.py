"""Alert decision engine for Week 7 — notification-ready intelligence delivery.

Deterministic rules only. Given the same inputs, the same alert decisions are made.

Responsibilities:
- Decide whether a PatternSignal or RiskScore warrants creating an alert.
- Assign priority (low / medium / high / critical).
- Enforce per-patient per-pattern-type throttling (1 alert per hour per pattern type).
- Persist alerts to the recommendations table.
- Publish ALERT_TRIGGERED events to the event bus.

This module does NOT send notifications — it makes the decision and stores
the result. The AlertRouter (or a separate notification daemon) consumes
ALERT_TRIGGERED events and dispatches to Telegram/push/etc.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import asyncpg

from ..events.bus import EventTypes, get_event_bus
from .patterns import PatternSignal
from .risk import RiskScore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Minimum confidence to create an alert from a PatternSignal.
PATTERN_ALERT_CONFIDENCE_THRESHOLD = 0.70

# Minimum severity (1-10) to create an alert from a PatternSignal.
PATTERN_ALERT_SEVERITY_THRESHOLD = 3

# Minimum risk_score to trigger a risk-level alert.
RISK_ALERT_SCORE_THRESHOLD = 3.0  # medium or higher

# Minimum risk_confidence to create a risk-level alert.
RISK_ALERT_CONFIDENCE_THRESHOLD = 0.70

# How long to wait before the same pattern_type can fire another alert for
# the same patient (prevents notification spam).
THROTTLE_WINDOW_HOURS = 1

# Map risk_level strings to alert_severity strings.
RISK_LEVEL_TO_SEVERITY = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
}

# Map PatternSignal.pattern_type to a human-readable alert title.
PATTERN_TYPE_TITLES = {
    "overnight_low_cluster": "Overnight Low Cluster Detected",
    "late_bedtime_dosing": "Late Bedtime Dosing Pattern",
    "recent_instability": "Glucose Variability Increased",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AlertDecision:
    """Result of an alert decision."""

    patient_id: str
    should_alert: bool
    alert_severity: str  # "low" | "medium" | "high" | "critical" | ""
    title: str
    description: str
    rationale: str
    source: str  # "pattern" | "risk" | "brief"
    source_id: str  # pattern_type or "risk_score"
    triggered_by_event_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    is_throttled: bool = False

    @property
    def should_create(self) -> bool:
        return self.should_alert and not self.is_throttled


@dataclass
class ActiveAlert:
    """A stored, active alert retrieved from the database."""

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
    expires_at: Optional[str]


# ---------------------------------------------------------------------------
# AlertDecisionEngine
# ---------------------------------------------------------------------------

class AlertDecisionEngine:
    """
    Deterministic alert decision logic for intelligence signals.

    Takes a PatternSignal or RiskScore and returns an AlertDecision
    explaining whether to alert and why.
    """

    def evaluate_pattern(self, signal: PatternSignal, patient_id: str) -> AlertDecision:
        """
        Evaluate a PatternSignal and return an alert decision.

        Alert fires when ALL of:
        - signal.confidence >= PATTERN_ALERT_CONFIDENCE_THRESHOLD (0.70)
        - signal.severity >= PATTERN_ALERT_SEVERITY_THRESHOLD (3)
        """
        if signal.confidence < PATTERN_ALERT_CONFIDENCE_THRESHOLD:
            return AlertDecision(
                patient_id=patient_id,
                should_alert=False,
                alert_severity="",
                title="",
                description="",
                rationale=(
                    f"Confidence {signal.confidence:.0%} is below the "
                    f"{PATTERN_ALERT_CONFIDENCE_THRESHOLD:.0%} threshold."
                ),
                source="pattern",
                source_id=signal.pattern_type,
                confidence=signal.confidence,
            )

        if signal.severity < PATTERN_ALERT_SEVERITY_THRESHOLD:
            return AlertDecision(
                patient_id=patient_id,
                should_alert=False,
                alert_severity="",
                title="",
                description="",
                rationale=(
                    f"Severity {signal.severity}/10 is below the "
                    f"{PATTERN_ALERT_SEVERITY_THRESHOLD}/10 threshold."
                ),
                source="pattern",
                source_id=signal.pattern_type,
                confidence=signal.confidence,
            )

        severity_str = _severity_from_pattern_severity(signal.severity)
        title = PATTERN_TYPE_TITLES.get(
            signal.pattern_type,
            f"Pattern: {signal.pattern_type}",
        )

        return AlertDecision(
            patient_id=patient_id,
            should_alert=True,
            alert_severity=severity_str,
            title=title,
            description=signal.reason,
            rationale=(
                f"Pattern '{signal.pattern_type}' cleared thresholds: "
                f"confidence {signal.confidence:.0%} >= {PATTERN_ALERT_CONFIDENCE_THRESHOLD:.0%}, "
                f"severity {signal.severity}/10 >= {PATTERN_ALERT_SEVERITY_THRESHOLD}/10."
            ),
            source="pattern",
            source_id=signal.pattern_type,
            triggered_by_event_ids=signal.supporting_event_ids,
            confidence=signal.confidence,
        )

    def evaluate_risk(self, risk: RiskScore) -> AlertDecision:
        """
        Evaluate a RiskScore and return an alert decision.

        Alert fires when BOTH of:
        - risk.risk_score >= RISK_ALERT_SCORE_THRESHOLD (3.0 — medium or higher)
        - risk.confidence >= RISK_ALERT_CONFIDENCE_THRESHOLD (0.70)
        """
        if risk.risk_score < RISK_ALERT_SCORE_THRESHOLD:
            return AlertDecision(
                patient_id=risk.patient_id,
                should_alert=False,
                alert_severity="",
                title="",
                description="",
                rationale=(
                    f"Risk score {risk.risk_score:.1f} is below the "
                    f"{RISK_ALERT_SCORE_THRESHOLD:.1f} threshold."
                ),
                source="risk",
                source_id="risk_score",
                confidence=risk.confidence,
            )

        if risk.confidence < RISK_ALERT_CONFIDENCE_THRESHOLD:
            return AlertDecision(
                patient_id=risk.patient_id,
                should_alert=False,
                alert_severity="",
                title="",
                description="",
                rationale=(
                    f"Risk confidence {risk.confidence:.0%} is below the "
                    f"{RISK_ALERT_CONFIDENCE_THRESHOLD:.0%} threshold."
                ),
                source="risk",
                source_id="risk_score",
                confidence=risk.confidence,
            )

        severity_str = RISK_LEVEL_TO_SEVERITY.get(
            risk.risk_level, "medium"
        )
        top_factors = _summarize_top_factors(risk.factors)

        return AlertDecision(
            patient_id=risk.patient_id,
            should_alert=True,
            alert_severity=severity_str,
            title=f"Night Risk: {risk.risk_level.capitalize()}",
            description=(
                f"Overnight risk score is {risk.risk_score:.1f} ({risk.risk_level}). "
                f"Top factors: {top_factors}"
            ),
            rationale=(
                f"Risk score {risk.risk_score:.1f} ({risk.risk_level}) cleared thresholds: "
                f"score >= {RISK_ALERT_SCORE_THRESHOLD}, "
                f"confidence {risk.confidence:.0%} >= {RISK_ALERT_CONFIDENCE_THRESHOLD:.0%}."
            ),
            source="risk",
            source_id="risk_score",
            triggered_by_event_ids=risk.supporting_events,
            confidence=risk.confidence,
        )


# ---------------------------------------------------------------------------
# AlertRouter — subscribes to event bus, evaluates, persists, re-publishes
# ---------------------------------------------------------------------------

class AlertRouter:
    """
    Subscribes to intelligence events on the event bus and routes
    alert-worthy signals to the notification pipeline.

    Flow:
        PATTERN_DETECTED / BASELINE_UPDATED / [risk compute] events arrive
            → AlertDecisionEngine evaluates
            → throttler checks recent alerts
            → stores in recommendations table (is_dismissed=FALSE)
            → publishes ALERT_TRIGGERED to event bus
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        decision_engine: Optional[AlertDecisionEngine] = None,
    ):
        self.pool = pool
        self._decision = decision_engine or AlertDecisionEngine()
        self._event_types = EventTypes
        self._bus = get_event_bus()
        # Track last-alert times in-memory (per-process; reset on restart is fine)
        self._last_alert_at: dict[tuple[str, str], datetime] = {}

    async def start(self) -> None:
        """Register event bus subscriptions. Call once at startup."""
        self._bus.subscribe(
            self._event_types.PATTERN_DETECTED,
            self._on_pattern_detected,
        )
        logger.info("AlertRouter started — subscribed to %s", self._event_types.PATTERN_DETECTED)

    async def stop(self) -> None:
        """Unregister event bus subscriptions. Call at shutdown."""
        self._bus.unsubscribe(
            self._event_types.PATTERN_DETECTED,
            self._on_pattern_detected,
        )
        logger.info("AlertRouter stopped")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_pattern_detected(self, event: dict) -> None:
        """
        Handle PATTERN_DETECTED events from the event bus.

        Event shape (from patterns.py _publish_patterns):
            {
                "patient_id": str,
                "pattern_type": str,
                "pattern_key": str,
                "pattern_value": PatternSignal.to_record(),
                "confidence": float,
                "sample_count": int,
            }
        """
        data = event.get("data", event)
        try:
            await self._handle_pattern_event(data)
        except Exception as exc:
            logger.error("AlertRouter failed to handle PATTERN_DETECTED: %s", exc)

    async def _handle_pattern_event(self, data: dict) -> None:
        patient_id = data["patient_id"]
        pattern_type = data["pattern_type"]
        pv = data.get("pattern_value", {})

        signal = PatternSignal(
            pattern_type=str(pattern_type),
            severity=int(pv.get("severity", 0)),
            confidence=float(pv.get("confidence", 0.0)),
            reason=str(pv.get("reason", "")),
            supporting_event_ids=list(pv.get("supporting_event_ids", [])),
            detected_at=datetime.fromisoformat(str(pv.get("detected_at", datetime.now(timezone.utc).isoformat()))),
            sample_count=int(pv.get("sample_count", 0)),
            metadata=dict(pv.get("metadata", {})),
        )

        decision = self._decision.evaluate_pattern(signal, patient_id)

        if not decision.should_alert:
            logger.debug(
                "Pattern %s for patient %s: no alert (confidence=%.0%%, severity=%d)",
                pattern_type, patient_id, signal.confidence * 100, signal.severity,
            )
            return

        # Check throttle
        if self._is_throttled(patient_id, pattern_type):
            logger.info(
                "Pattern %s for patient %s: THROTTLED (recent alert within %dh)",
                pattern_type, patient_id, THROTTLE_WINDOW_HOURS,
            )
            return

        alert_id = await self._store_alert(decision)
        self._record_alert_time(patient_id, pattern_type)

        self._bus.publish(
            self._event_types.ALARM_TRIGGERED,  # Re-use existing event type for notification dispatch
            {
                "alert_id": alert_id,
                "patient_id": patient_id,
                "alert_severity": decision.alert_severity,
                "title": decision.title,
                "description": decision.description,
                "source": decision.source,
                "source_id": decision.source_id,
                "confidence": decision.confidence,
                "triggered_by_event_ids": decision.triggered_by_event_ids,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info(
            "AlertRouter: alert '%s' triggered for patient %s [severity=%s]",
            decision.title, patient_id, decision.alert_severity,
        )

    # ------------------------------------------------------------------
    # Throttle helpers
    # ------------------------------------------------------------------

    def _is_throttled(self, patient_id: str, pattern_type: str) -> bool:
        key = (patient_id, pattern_type)
        last_at = self._last_alert_at.get(key)
        if last_at is None:
            return False
        elapsed = datetime.now(timezone.utc) - last_at
        return elapsed < timedelta(hours=THROTTLE_WINDOW_HOURS)

    def _record_alert_time(self, patient_id: str, pattern_type: str) -> None:
        self._last_alert_at[(patient_id, pattern_type)] = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _store_alert(self, decision: AlertDecision) -> str:
        alert_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        # Alerts expire at the end of the next calendar day (so they at most span ~36h)
        expires_at = datetime.combine(
            now.date() + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO recommendations (
                    id, patient_id, recommendation_type, priority,
                    title, description, rationale,
                    confidence, based_on_events,
                    alert_source, alert_severity, triggered_by_event_ids,
                    is_acknowledged, is_dismissed,
                    expires_at, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, FALSE, FALSE, $13, $14)
                """,
                alert_id,
                decision.patient_id,
                decision.source,  # recommendation_type
                decision.alert_severity,  # priority
                decision.title,
                decision.description,
                decision.rationale,
                decision.confidence,
                json.dumps(decision.triggered_by_event_ids),
                decision.source,  # alert_source
                decision.alert_severity,
                json.dumps(decision.triggered_by_event_ids),
                expires_at,
                now,
            )

        return alert_id

    # ------------------------------------------------------------------
    # Query active alerts
    # ------------------------------------------------------------------

    async def get_active_alerts(
        self,
        patient_id: str,
        limit: int = 10,
    ) -> list[ActiveAlert]:
        """
        Fetch the most recent unacknowledged, undismissed alerts for a patient.
        Ordered by severity (critical first) then by creation time (newest first).
        """
        async with self.pool.acquire() as conn:
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
                LIMIT $2
                """,
                patient_id,
                limit,
            )

        return [self._row_to_alert(row) for row in rows]

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged. Returns True if found and updated."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE recommendations
                SET is_acknowledged = TRUE, acknowledged_at = NOW()
                WHERE id = $1 AND alert_severity IS NOT NULL
                """,
                uuid.UUID(alert_id),
            )
        return result != "UPDATE 0"

    async def dismiss_alert(self, alert_id: str) -> bool:
        """Mark an alert as dismissed. Returns True if found and updated."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE recommendations
                SET is_dismissed = TRUE, dismissed_at = NOW()
                WHERE id = $1 AND alert_severity IS NOT NULL
                """,
                uuid.UUID(alert_id),
            )
        return result != "UPDATE 0"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_alert(self, row) -> ActiveAlert:
        triggered_ids = row["triggered_by_event_ids"]
        if isinstance(triggered_ids, str):
            triggered_ids = json.loads(triggered_ids)

        return ActiveAlert(
            id=str(row["id"]),
            patient_id=str(row["patient_id"]),
            title=row["title"] or "",
            description=row["description"] or "",
            rationale=row["rationale"] or "",
            alert_severity=row["alert_severity"] or "medium",
            source=row.get("alert_source") or row.get("source") or "pattern",
            source_id=row["source"] or "",
            confidence=float(row["confidence"] or 0.0),
            triggered_by_event_ids=list(triggered_ids or []),
            is_acknowledged=bool(row["is_acknowledged"]),
            is_dismissed=bool(row["is_dismissed"]),
            created_at=row["created_at"].isoformat() if row["created_at"] else "",
            expires_at=row["expires_at"].isoformat() if row["expires_at"] else None,
        )


# ---------------------------------------------------------------------------
# Pure helper functions (no I/O — easy to test)
# ---------------------------------------------------------------------------

def _severity_from_pattern_severity(severity: int) -> str:
    """Map PatternSignal severity (1-10) to alert severity string."""
    if severity >= 8:
        return "high"
    if severity >= 5:
        return "medium"
    return "low"


def _summarize_top_factors(factors: list[dict[str, Any]]) -> str:
    """Return a one-line summary of the top 2 risk factors."""
    if not factors:
        return "no specific factor"
    sorted_factors = sorted(factors, key=lambda f: -f.get("severity", 0))
    summaries = [
        f['factor'].replace("_", " ") + f" (severity {f.get('severity', 0)})"
        for f in sorted_factors[:2]
    ]
    return "; ".join(summaries)
