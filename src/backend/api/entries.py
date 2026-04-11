"""
Manual Entry API — Patient data entry endpoints.

Provides REST API for logging:
- Glucose readings
- Cornstarch doses
- Meals
- Symptoms

Cornstarch and meal entries automatically create coverage courses.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from pydantic import ConfigDict

import asyncpg

from ..events.store import EventStore
from ..events.bus import EventTypes
from ..courses.engine import (
    CoverageCourseEngine,
    CORNSTARCH_DURATION_MINUTES,
    MEAL_DURATION_MINUTES,
)
from ..alarms.engine import CoverageAlarmEngine


# ============================================================
# Request/Response Models
# ============================================================

class GlucoseReadingRequest(BaseModel):
    """Request body for logging a glucose reading."""
    value_mg_dl: int = Field(..., ge=20, le=600, description="Glucose value in mg/dL")
    reading_type: str = Field(
        default="fingerstick",
        description="Type of reading: 'fingerstick', 'sensor', 'lab'"
    )
    context: str = Field(
        default="",
        description="Context: 'fasting', 'pre_meal', 'post_meal', 'bedtime', 'other'"
    )
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the reading was taken"
    )


class CornstarchDoseRequest(BaseModel):
    """Request body for logging a cornstarch dose."""
    grams: float = Field(..., gt=0, le=100, description="Grams of cornstarch")
    brand: str = Field(default="unknown", description="Brand of cornstarch")
    is_bedtime_dose: bool = Field(default=False, description="Is this a bedtime dose?")
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the dose was taken"
    )


class MealRequest(BaseModel):
    """Request body for logging a meal."""
    meal_type: str = Field(
        ...,
        description="Meal type: 'breakfast', 'lunch', 'dinner', 'snack'"
    )
    description: str = Field(default="", description="Description of the meal")
    contains_cornstarch: bool = Field(
        default=False,
        description="Does the meal contain cornstarch?"
    )
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the meal was eaten"
    )


class SymptomRequest(BaseModel):
    """Request body for logging a symptom."""
    symptom_type: str = Field(
        ...,
        description="Symptom type: 'hypoglycemia', 'hyperglycemia', 'nausea', 'fatigue', 'other'"
    )
    severity: int = Field(..., ge=1, le=10, description="Severity 1-10")
    context: str = Field(default="", description="Additional context")
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the symptom occurred"
    )


class EventResponse(BaseModel):
    """Response body for event-only endpoints."""
    model_config = ConfigDict(from_attributes=True)
    
    event_id: str
    patient_id: str
    event_type: str
    occurred_at: str


class CornstarchResponse(BaseModel):
    """Response body for cornstarch dose endpoint."""
    model_config = ConfigDict(from_attributes=True)
    
    event_id: str
    course_id: str
    patient_id: str
    trigger_type: str
    duration_minutes: int
    expected_end_at: str
    is_bedtime_dose: bool


class MealResponse(BaseModel):
    """Response body for meal endpoint."""
    model_config = ConfigDict(from_attributes=True)
    
    event_id: str
    course_id: Optional[str]  # None if contains_cornstarch=True
    patient_id: str
    trigger_type: str
    duration_minutes: Optional[int]  # None if contains_cornstarch=True
    expected_end_at: Optional[str]  # None if contains_cornstarch=True
    contains_cornstarch: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response body."""
    error: str
    detail: Optional[str] = None


# ============================================================
# Router Factory
# ============================================================

def create_entries_router(
    pool: asyncpg.Pool,
    event_store: Optional[EventStore] = None,
    course_engine: Optional[CoverageCourseEngine] = None,
    alarm_engine: Optional[CoverageAlarmEngine] = None,
):
    """
    Create FastAPI router with patient entry endpoints.
    
    Args:
        pool: PostgreSQL connection pool.
        event_store: Optional EventStore instance (created if not provided).
        course_engine: Optional CoverageCourseEngine instance (created if not provided).
    """
    router = APIRouter(prefix="/patients", tags=["entries"])
    
    # Initialize services
    if event_store is None:
        event_store = EventStore(pool)
    if course_engine is None:
        course_engine = CoverageCourseEngine(pool)
    
    # ---- Glucose Reading ----
    
    @router.post(
        "/{patient_id}/glucose",
        status_code=status.HTTP_201_CREATED,
        response_model=EventResponse,
    )
    async def log_glucose(
        patient_id: str,
        reading: GlucoseReadingRequest,
    ) -> EventResponse:
        """
        Log a glucose reading.
        
        This endpoint only logs the event - it does NOT create a coverage course.
        Use cornstarch or meal endpoints for coverage tracking.
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
        
        # Create event
        event_id = await event_store.append_event(
            patient_id=patient_id,
            event_type="glucose_reading",
            payload={
                "value_mg_dl": reading.value_mg_dl,
                "reading_type": reading.reading_type,
                "context": reading.context,
            },
            source_type="manual",
            occurred_at=reading.occurred_at,
        )

        if alarm_engine is not None:
            await alarm_engine.resolve_by_event(patient_id, "glucose_reading", event_id)
        
        return EventResponse(
            event_id=event_id,
            patient_id=patient_id,
            event_type="glucose_reading",
            occurred_at=reading.occurred_at.isoformat(),
        )
    
    # ---- Cornstarch Dose ----
    
    @router.post(
        "/{patient_id}/cornstarch",
        status_code=status.HTTP_201_CREATED,
        response_model=CornstarchResponse,
    )
    async def log_cornstarch(
        patient_id: str,
        dose: CornstarchDoseRequest,
    ) -> CornstarchResponse:
        """
        Log a cornstarch dose.
        
        This creates a coverage course with default 5.15 hour duration.
        The course will be automatically linked to any previous active course.
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
        
        # Create event
        event_id = await event_store.append_event(
            patient_id=patient_id,
            event_type="cornstarch_dose",
            payload={
                "grams": dose.grams,
                "brand": dose.brand,
                "is_bedtime_dose": dose.is_bedtime_dose,
            },
            source_type="manual",
            occurred_at=dose.occurred_at,
        )
        
        # Start coverage course
        course_id = await course_engine.start_course(
            patient_id=patient_id,
            trigger_event_id=event_id,
            trigger_type="cornstarch",
            expected_duration=CORNSTARCH_DURATION_MINUTES,
            is_bedtime_dose=dose.is_bedtime_dose,
            occurred_at=dose.occurred_at,
        )
        
        if alarm_engine is not None:
            await alarm_engine.resolve_by_event(patient_id, "cornstarch_dose", event_id)
            await alarm_engine.ensure_alarm_for_course(course_id)

        # Get course details
        course = await course_engine.get_course_by_id(course_id)
        
        return CornstarchResponse(
            event_id=event_id,
            course_id=course_id,
            patient_id=patient_id,
            trigger_type="cornstarch",
            duration_minutes=CORNSTARCH_DURATION_MINUTES,
            expected_end_at=course["expected_end_at"].isoformat(),
            is_bedtime_dose=dose.is_bedtime_dose,
        )
    
    # ---- Meal ----
    
    @router.post(
        "/{patient_id}/meals",
        status_code=status.HTTP_201_CREATED,
        response_model=MealResponse,
    )
    async def log_meal(
        patient_id: str,
        meal: MealRequest,
    ) -> MealResponse:
        """
        Log a meal.
        
        If the meal does NOT contain cornstarch, creates a coverage course
        with default 2 hour duration.
        
        If the meal contains cornstarch, no course is created (the cornstarch
        endpoint should be used instead).
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
        
        # Create event
        event_id = await event_store.append_event(
            patient_id=patient_id,
            event_type="meal",
            payload={
                "meal_type": meal.meal_type,
                "description": meal.description,
                "contains_cornstarch": meal.contains_cornstarch,
            },
            source_type="manual",
            occurred_at=meal.occurred_at,
        )
        
        # Create coverage course if meal does NOT contain cornstarch
        course_id = None
        expected_end_at = None
        duration_minutes = None
        message = ""
        
        if not meal.contains_cornstarch:
            course_id = await course_engine.start_course(
                patient_id=patient_id,
                trigger_event_id=event_id,
                trigger_type="meal",
                expected_duration=MEAL_DURATION_MINUTES,
                occurred_at=meal.occurred_at,
            )
            
            if alarm_engine is not None:
                await alarm_engine.resolve_by_event(patient_id, "meal", event_id)
                await alarm_engine.ensure_alarm_for_course(course_id)

            course = await course_engine.get_course_by_id(course_id)
            expected_end_at = course["expected_end_at"].isoformat()
            duration_minutes = MEAL_DURATION_MINUTES
            message = f"Coverage course created with {MEAL_DURATION_MINUTES} minute duration"
        else:
            message = "No coverage course created - meal contains cornstarch (use /cornstarch endpoint)"
        
        return MealResponse(
            event_id=event_id,
            course_id=course_id,
            patient_id=patient_id,
            trigger_type="meal",
            duration_minutes=duration_minutes,
            expected_end_at=expected_end_at,
            contains_cornstarch=meal.contains_cornstarch,
            message=message,
        )
    
    # ---- Symptom ----
    
    @router.post(
        "/{patient_id}/symptoms",
        status_code=status.HTTP_201_CREATED,
        response_model=EventResponse,
    )
    async def log_symptom(
        patient_id: str,
        symptom: SymptomRequest,
    ) -> EventResponse:
        """
        Log a symptom.
        
        This endpoint only logs the event - it does NOT create a coverage course.
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
        
        # Create event
        event_id = await event_store.append_event(
            patient_id=patient_id,
            event_type="symptom",
            payload={
                "symptom_type": symptom.symptom_type,
                "severity": symptom.severity,
                "context": symptom.context,
            },
            source_type="manual",
            occurred_at=symptom.occurred_at,
        )
        
        return EventResponse(
            event_id=event_id,
            patient_id=patient_id,
            event_type="symptom",
            occurred_at=symptom.occurred_at.isoformat(),
        )
    
    # ---- Get Active Course ----
    
    @router.get("/{patient_id}/active-course")
    async def get_active_course(patient_id: str):
        """
        Get the currently active coverage course for a patient.
        """
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
        
        course = await course_engine.get_active_course(patient_id)
        
        if not course:
            return {"active_course": None, "message": "No active coverage course"}
        
        # Format datetime fields
        course["started_at"] = course["started_at"].isoformat()
        course["expected_end_at"] = course["expected_end_at"].isoformat()
        if course.get("actual_end_at"):
            course["actual_end_at"] = course["actual_end_at"].isoformat()
        
        return {"active_course": course}
    
    # ---- Get Course Chain ----
    
    @router.get("/{patient_id}/courses")
    async def get_course_chain(
        patient_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ):
        """
        Get coverage courses for a patient within a time range.
        """
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
        
        courses = await course_engine.get_course_chain(patient_id, start, end)
        
        # Format datetime fields
        for course in courses:
            course["started_at"] = course["started_at"].isoformat()
            course["expected_end_at"] = course["expected_end_at"].isoformat()
            if course.get("actual_end_at"):
                course["actual_end_at"] = course["actual_end_at"].isoformat()
        
        return {"courses": courses, "count": len(courses)}
    
    return router
