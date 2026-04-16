"""
Patient & Caregiver API endpoints.

Provides REST API for:
- Patient CRUD
- Caregiver management
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ..intelligence.alerts import AlertRouter
from ..intelligence.baseline import BaselineEngine
from ..intelligence.brief import BriefGenerator
from ..intelligence.patterns import PatternEngine
from ..intelligence.risk import RiskEngine


# Request/Response Models

class PatientCreate(BaseModel):
    """Request body for creating a patient."""
    external_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: Optional[str] = None  # ISO date string
    gsd1a_diagnosis_date: Optional[str] = None
    care_protocol: dict = Field(default_factory=dict)
    preferences: dict = Field(default_factory=dict)


class PatientUpdate(BaseModel):
    """Request body for updating a patient."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    date_of_birth: Optional[str] = None
    gsd1a_diagnosis_date: Optional[str] = None
    care_protocol: Optional[dict] = None
    preferences: Optional[dict] = None


class PatientResponse(BaseModel):
    """Response body for patient data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    external_id: Optional[str]
    name: str
    date_of_birth: Optional[str]
    gsd1a_diagnosis_date: Optional[str]
    care_protocol: dict
    preferences: dict
    created_at: str
    updated_at: str


class CaregiverCreate(BaseModel):
    """Request body for creating a caregiver."""
    name: str = Field(..., min_length=1, max_length=255)
    relationship: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    telegram_id: Optional[str] = Field(None, max_length=100)
    escalation_order: int = Field(default=1, ge=1)
    is_primary: bool = Field(default=False)
    notify_warning: bool = Field(default=True)
    notify_alarm: bool = Field(default=True)
    notify_escalation: bool = Field(default=True)


class CaregiverResponse(BaseModel):
    """Response body for caregiver data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    patient_id: str
    name: str
    relationship: str
    phone: Optional[str]
    email: Optional[str]
    telegram_id: Optional[str]
    escalation_order: int
    is_primary: bool
    notify_warning: bool
    notify_alarm: bool
    notify_escalation: bool
    created_at: str
    updated_at: str


class ErrorResponse(BaseModel):
    """Error response body."""
    error: str
    detail: Optional[str] = None


class DailyBriefResponse(BaseModel):
    """Patient-facing daily brief payload."""

    brief_date: str
    patient_id: str
    summary: str
    what_changed: list[str]
    what_matters: list[str]
    recommended_attention: list[str]
    confidence: float
    supporting_events: list[str]
    generated_at: str


class BaselineMetricResponse(BaseModel):
    metric_type: str
    value: Optional[float]
    unit: str
    confidence: float
    sample_count: int
    qualifying_days: int
    computed_at: str
    valid_until: str
    rationale: str
    supporting_event_ids: list[str]
    metadata: dict


class PatternSignalResponse(BaseModel):
    pattern_type: str
    severity: int
    confidence: float
    reason: str
    supporting_event_ids: list[str]
    detected_at: str
    sample_count: int
    metadata: dict


class RiskScoreResponse(BaseModel):
    patient_id: str
    risk_score: float
    risk_level: str
    confidence: float
    factors: list[dict]
    supporting_events: list[str]
    generated_at: str


class AlertResponse(BaseModel):
    """Active alert payload returned to mobile clients."""
    id: str
    patient_id: str
    title: str
    description: str
    rationale: str
    alert_severity: str  # 'low' | 'medium' | 'high' | 'critical'
    source: str  # 'pattern' | 'risk'
    source_id: str
    confidence: float
    triggered_by_event_ids: list[str]
    is_acknowledged: bool
    is_dismissed: bool
    created_at: str
    expires_at: Optional[str] = None


class AlertsListResponse(BaseModel):
    alerts: list[AlertResponse]
    count: int


# Database dependency (would be injected in real app)

async def get_db_pool():
    """Placeholder for database pool injection."""
    # In production, this would be FastAPI dependency
    raise NotImplementedError("Database pool not configured")


# Router factory

def create_patients_router(pool, alert_router: Optional[AlertRouter] = None):
    """Create FastAPI router with patient endpoints.

    Args:
        pool: PostgreSQL connection pool.
        alert_router: Optional AlertRouter instance for Week 7 alert endpoints.
    """

    router = APIRouter(prefix="/patients", tags=["patients"])
    
    @router.post("", status_code=status.HTTP_201_CREATED, response_model=PatientResponse)
    async def create_patient(patient: PatientCreate) -> PatientResponse:
        """
        Create a new patient.
        
        Returns the created patient with generated UUID.
        """
        patient_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO patients (
                    id, external_id, name, date_of_birth, gsd1a_diagnosis_date,
                    care_protocol, preferences, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id, external_id, name, date_of_birth, gsd1a_diagnosis_date,
                          care_protocol, preferences, created_at, updated_at
                """,
                patient_id,
                patient.external_id,
                patient.name,
                patient.date_of_birth,
                patient.gsd1a_diagnosis_date,
                patient.care_protocol,
                patient.preferences,
                now,
                now,
            )
        
        return _row_to_patient_response(row)
    
    @router.get("/{patient_id}", response_model=PatientResponse)
    async def get_patient(patient_id: str) -> PatientResponse:
        """
        Get a patient by ID.
        
        Returns 404 if not found.
        """
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, external_id, name, date_of_birth, gsd1a_diagnosis_date,
                       care_protocol, preferences, created_at, updated_at
                FROM patients WHERE id = $1
                """,
                patient_id,
            )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )
        
        return _row_to_patient_response(row)
    
    @router.put("/{patient_id}", response_model=PatientResponse)
    async def update_patient(patient_id: str, update: PatientUpdate) -> PatientResponse:
        """
        Update a patient.
        
        Only provided fields are updated (partial update supported).
        """
        # Build dynamic update query
        fields = []
        params = []
        param_idx = 1
        
        for field_name, value in update.model_dump(exclude_unset=True).items():
            if value is not None:
                fields.append(f"{field_name} = ${param_idx}")
                params.append(value)
                param_idx += 1
        
        if not fields:
            # No updates, just return current state
            return await get_patient(patient_id)
        
        fields.append(f"updated_at = ${param_idx}")
        params.append(datetime.now(timezone.utc))
        param_idx += 1
        
        params.append(patient_id)
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE patients
                SET {', '.join(fields)}
                WHERE id = ${param_idx}
                RETURNING id, external_id, name, date_of_birth, gsd1a_diagnosis_date,
                          care_protocol, preferences, created_at, updated_at
                """,
                *params,
            )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )
        
        return _row_to_patient_response(row)
    
    async def _require_patient(patient_id: str):
        async with pool.acquire() as conn:
            patient = await conn.fetchrow(
                "SELECT id FROM patients WHERE id = $1",
                patient_id,
            )
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )
        return patient

    @router.get("/{patient_id}/baselines", response_model=list[BaselineMetricResponse])
    async def get_patient_baselines(patient_id: str) -> list[BaselineMetricResponse]:
        """Compute and return current patient baselines."""
        await _require_patient(patient_id)
        engine = BaselineEngine(pool)
        baselines = await engine.compute_baselines(patient_id)
        return [BaselineMetricResponse(**metric.to_record()) for metric in baselines.metrics.values()]

    @router.get("/{patient_id}/patterns", response_model=list[PatternSignalResponse])
    async def get_patient_patterns(patient_id: str) -> list[PatternSignalResponse]:
        """Compute and return active patient patterns."""
        await _require_patient(patient_id)
        engine = PatternEngine(pool)
        patterns = await engine.compute_patterns(patient_id)
        return [PatternSignalResponse(**pattern.to_record()) for pattern in patterns]

    @router.get("/{patient_id}/daily-brief", response_model=DailyBriefResponse)
    async def get_daily_brief(patient_id: str) -> DailyBriefResponse:
        """Get today's daily intelligence brief for a patient."""
        await _require_patient(patient_id)
        generator = BriefGenerator(pool)
        brief = await generator.get_daily_brief(patient_id)
        return DailyBriefResponse(**brief.to_record())

    @router.get("/{patient_id}/risk", response_model=RiskScoreResponse)
    async def get_patient_risk(patient_id: str) -> RiskScoreResponse:
        """Compute and return current overnight risk score."""
        await _require_patient(patient_id)
        engine = RiskEngine(pool)
        risk = await engine.compute_risk(patient_id)
        return RiskScoreResponse(**risk.to_record())

    # ---- Week 7: Active Alerts ----

    @router.get("/{patient_id}/alerts", response_model=AlertsListResponse)
    async def get_patient_alerts(
        patient_id: str,
        limit: int = 10,
    ) -> AlertsListResponse:
        """Fetch unacknowledged, undismissed alerts for a patient."""
        await _require_patient(patient_id)
        if alert_router is None:
            return AlertsListResponse(alerts=[], count=0)
        alerts = await alert_router.get_active_alerts(patient_id, limit=limit)
        return AlertsListResponse(
            alerts=[AlertResponse(
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
            ) for a in alerts],
            count=len(alerts),
        )

    @router.post("/{patient_id}/alerts/{alert_id}/acknowledge", status_code=status.HTTP_204_NO_CONTENT)
    async def acknowledge_alert(patient_id: str, alert_id: str) -> None:
        """Mark an alert as acknowledged."""
        await _require_patient(patient_id)
        if alert_router is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Alert router not configured",
            )
        found = await alert_router.acknowledge_alert(alert_id)
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

    @router.post("/{patient_id}/alerts/{alert_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
    async def dismiss_alert(patient_id: str, alert_id: str) -> None:
        """Mark an alert as dismissed."""
        await _require_patient(patient_id)
        if alert_router is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Alert router not configured",
            )
        found = await alert_router.dismiss_alert(alert_id)
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

    @router.post("/admin/regenerate-briefs", response_model=list[DailyBriefResponse])
    async def regenerate_briefs(patient_ids: list[str] = Body(...)) -> list[DailyBriefResponse]:
        """Backfill today's briefs for the provided patients."""
        generator = BriefGenerator(pool)
        briefs: list[DailyBriefResponse] = []
        for patient_id in patient_ids:
            await _require_patient(patient_id)
            brief = await generator.generate_daily_brief(patient_id)
            briefs.append(DailyBriefResponse(**brief.to_record()))
        return briefs

    @router.post("/{patient_id}/caregivers", status_code=status.HTTP_201_CREATED, response_model=CaregiverResponse)
    async def add_caregiver(patient_id: str, caregiver: CaregiverCreate) -> CaregiverResponse:
        """
        Add a caregiver to a patient.
        
        Validates patient exists before adding.
        """
        # Verify patient exists
        async with pool.acquire() as conn:
            patient = await conn.fetchrow(
                "SELECT id FROM patients WHERE id = $1",
                patient_id,
            )
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )
        
        caregiver_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO caregivers (
                    id, patient_id, name, relationship, phone, email, telegram_id,
                    escalation_order, is_primary, notify_warning, notify_alarm,
                    notify_escalation, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id, patient_id, name, relationship, phone, email, telegram_id,
                          escalation_order, is_primary, notify_warning, notify_alarm,
                          notify_escalation, created_at, updated_at
                """,
                caregiver_id,
                patient_id,
                caregiver.name,
                caregiver.relationship,
                caregiver.phone,
                caregiver.email,
                caregiver.telegram_id,
                caregiver.escalation_order,
                caregiver.is_primary,
                caregiver.notify_warning,
                caregiver.notify_alarm,
                caregiver.notify_escalation,
                now,
                now,
            )
        
        return _row_to_caregiver_response(row)
    
    @router.get("/{patient_id}/caregivers", response_model=list[CaregiverResponse])
    async def list_caregivers(patient_id: str) -> list[CaregiverResponse]:
        """
        List all caregivers for a patient.
        
        Ordered by escalation_order.
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, patient_id, name, relationship, phone, email, telegram_id,
                       escalation_order, is_primary, notify_warning, notify_alarm,
                       notify_escalation, created_at, updated_at
                FROM caregivers
                WHERE patient_id = $1
                ORDER BY escalation_order ASC
                """,
                patient_id,
            )
        
        return [_row_to_caregiver_response(row) for row in rows]
    
    @router.delete("/caregivers/{caregiver_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def remove_caregiver(caregiver_id: str) -> None:
        """
        Remove a caregiver.
        
        Returns 204 on success, 404 if not found.
        """
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM caregivers WHERE id = $1",
                caregiver_id,
            )
        
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Caregiver {caregiver_id} not found",
            )
    
    return router


# Helper functions

def _row_to_patient_response(row) -> PatientResponse:
    """Convert database row to PatientResponse."""
    return PatientResponse(
        id=str(row["id"]),
        external_id=row["external_id"],
        name=row["name"],
        date_of_birth=str(row["date_of_birth"]) if row["date_of_birth"] else None,
        gsd1a_diagnosis_date=str(row["gsd1a_diagnosis_date"]) if row["gsd1a_diagnosis_date"] else None,
        care_protocol=row["care_protocol"],
        preferences=row["preferences"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


def _row_to_caregiver_response(row) -> CaregiverResponse:
    """Convert database row to CaregiverResponse."""
    return CaregiverResponse(
        id=str(row["id"]),
        patient_id=str(row["patient_id"]),
        name=row["name"],
        relationship=row["relationship"],
        phone=row["phone"],
        email=row["email"],
        telegram_id=row["telegram_id"],
        escalation_order=row["escalation_order"],
        is_primary=row["is_primary"],
        notify_warning=row["notify_warning"],
        notify_alarm=row["notify_alarm"],
        notify_escalation=row["notify_escalation"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


# Module-level FastAPI app for direct running
app = FastAPI(title="Pippen Patients API")

# This would be wired up in main.py with actual database pool
__all__ = ["create_patients_router", "app"]