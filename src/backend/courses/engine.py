"""
Coverage Course State Machine — Core GSD1A timing engine.

State transitions:
    active → warning_sent → expired → alarmed → escalated
       ↓           ↓           ↓
  superseded  closed      closed

This is the safety-critical core of Pippen's coverage tracking.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from enum import Enum

import asyncpg

from ..events.bus import get_event_bus, EventTypes


class CourseStatus(str, Enum):
    """Coverage course status values."""
    ACTIVE = "active"
    WARNING_SENT = "warning_sent"
    EXPIRED = "expired"
    ALARMED = "alarmed"
    ESCALATED = "escalated"
    CLOSED = "closed"
    SUPERSEDED = "superseded"


# Default durations in minutes
CORNSTARCH_DURATION_MINUTES = int(5.15 * 60)  # 5.15 hours = 309 minutes
MEAL_DURATION_MINUTES = 2 * 60  # 2 hours = 120 minutes


class CourseEngineError(Exception):
    """Base exception for course engine errors."""
    pass


class InvalidStateTransitionError(CourseEngineError):
    """Raised when an invalid state transition is attempted."""
    pass


class CourseNotFoundError(CourseEngineError):
    """Raised when a course is not found."""
    pass


# Valid state transitions
VALID_TRANSITIONS = {
    CourseStatus.ACTIVE: {
        CourseStatus.WARNING_SENT,
        CourseStatus.EXPIRED,
        CourseStatus.SUPERSEDED,
    },
    CourseStatus.WARNING_SENT: {
        CourseStatus.EXPIRED,
        CourseStatus.CLOSED,
    },
    CourseStatus.EXPIRED: {
        CourseStatus.ALARMED,
        CourseStatus.CLOSED,
    },
    CourseStatus.ALARMED: {
        CourseStatus.ESCALATED,
        CourseStatus.CLOSED,
    },
    CourseStatus.ESCALATED: {
        CourseStatus.CLOSED,
    },
    CourseStatus.CLOSED: set(),
    CourseStatus.SUPERSEDED: set(),
}


def validate_transition(current: CourseStatus, new: CourseStatus) -> bool:
    """Check if a state transition is valid."""
    return new in VALID_TRANSITIONS.get(current, set())


class CoverageCourseEngine:
    """
    Coverage course state machine for GSD1A patient tracking.
    
    Usage:
        engine = CoverageCourseEngine(pool)
        
        # Start a new coverage course
        course_id = await engine.start_course(
            patient_id="...",
            trigger_event_id="event-uuid",
            trigger_type="cornstarch",
            expected_duration=309,  # 5.15 hours
        )
        
        # Get currently active course
        course = await engine.get_active_course(patient_id)
        
        # Update status with validation
        await engine.update_course_status(course_id, CourseStatus.WARNING_SENT, "15 min warning")
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def start_course(
        self,
        patient_id: str,
        trigger_event_id: str,
        trigger_type: str,
        expected_duration: int,
        is_bedtime_dose: bool = False,
        notes: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> str:
        """
        Start a new coverage course for a patient.
        
        Automatically links to the previous active course if one exists.
        
        Args:
            patient_id: UUID of the patient.
            trigger_event_id: UUID of the event that triggered this course.
            trigger_type: Type of trigger ('cornstarch', 'meal', 'manual', 'sensor').
            expected_duration: Expected coverage duration in minutes.
            is_bedtime_dose: Whether this is a bedtime dose.
            notes: Optional notes.
            occurred_at: When the triggering event occurred (defaults to now).
            
        Returns:
            UUID of the created coverage course.
        """
        now = datetime.now(timezone.utc)
        started_at = occurred_at or now
        expected_end_at = started_at + timedelta(minutes=expected_duration)
        
        async with self.pool.acquire() as conn:
            # Find and supersede the previous active course
            previous_course = await conn.fetchrow(
                """
                SELECT id, status FROM coverage_courses
                WHERE patient_id = $1 AND status IN ('active', 'warning_sent')
                ORDER BY started_at DESC
                LIMIT 1
                FOR UPDATE
                """,
                patient_id,
            )
            
            previous_course_id = None
            if previous_course:
                previous_course_id = previous_course["id"]
            
            # Create new course FIRST (so we have the ID for the superseded event)
            course_id = str(uuid.uuid4())
            
            await conn.execute(
                """
                INSERT INTO coverage_courses (
                    id, patient_id, trigger_event_id, trigger_type, status,
                    started_at, expected_end_at, previous_course_id,
                    duration_minutes, is_bedtime_dose, notes, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                course_id,
                patient_id,
                trigger_event_id,
                trigger_type,
                CourseStatus.ACTIVE.value,
                started_at,
                expected_end_at,
                previous_course_id,
                expected_duration,
                is_bedtime_dose,
                notes,
                now,
            )
            
            # Update next_course_id on previous course and mark as superseded
            if previous_course_id:
                await conn.execute(
                    """
                    UPDATE coverage_courses
                    SET next_course_id = $1, status = 'superseded', updated_at = $2
                    WHERE id = $3
                    """,
                    course_id,
                    now,
                    previous_course_id,
                )
                
                # Calculate and record gap/overlap with previous course
                await self._record_gap_or_overlap(
                    conn, previous_course_id, course_id, started_at
                )
        
        # Publish course started event
        bus = get_event_bus()
        await bus.publish(
            EventTypes.COVERAGE_COURSE_STARTED,
            {
                "course_id": course_id,
                "patient_id": patient_id,
                "trigger_type": trigger_type,
                "trigger_event_id": trigger_event_id,
                "started_at": started_at.isoformat(),
                "expected_end_at": expected_end_at.isoformat(),
                "duration_minutes": expected_duration,
                "is_bedtime_dose": is_bedtime_dose,
            }
        )
        
        # Publish superseded event (AFTER course is created, with correct new course_id)
        if previous_course_id:
            await bus.publish(
                EventTypes.COVERAGE_COURSE_CLOSED,
                {
                    "course_id": str(previous_course_id),
                    "patient_id": patient_id,
                    "reason": "superseded",
                    "superseded_by": str(course_id),  # FIXED: Now points to new course
                }
            )
        
        return course_id
        
        return course_id
    
    async def get_active_course(self, patient_id: str) -> Optional[dict]:
        """
        Get the currently active coverage course for a patient.
        
        Args:
            patient_id: UUID of the patient.
            
        Returns:
            Course record as dict, or None if no active course.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, patient_id, trigger_event_id, trigger_type, status,
                       started_at, expected_end_at, actual_end_at,
                       previous_course_id, next_course_id,
                       duration_minutes, is_bedtime_dose, notes,
                       gap_minutes, overlap_minutes, created_at
                FROM coverage_courses
                WHERE patient_id = $1 AND status IN ('active', 'warning_sent', 'expired', 'alarmed')
                ORDER BY started_at DESC
                LIMIT 1
                """,
                patient_id,
            )
        
        if not row:
            return None
        
        return dict(row)
    
    async def get_course_chain(
        self,
        patient_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Get a chain of coverage courses for a patient within a time range.
        
        Args:
            patient_id: UUID of the patient.
            start: Start of time range (optional).
            end: End of time range (optional).
            
        Returns:
            List of course records in chronological order.
        """
        query = """
            SELECT id, patient_id, trigger_event_id, trigger_type, status,
                   started_at, expected_end_at, actual_end_at,
                   previous_course_id, next_course_id,
                   duration_minutes, is_bedtime_dose, notes,
                   gap_minutes, overlap_minutes, created_at
            FROM coverage_courses
            WHERE patient_id = $1
        """
        params = [patient_id]
        param_idx = 2
        
        if start:
            query += f" AND started_at >= ${param_idx}"
            params.append(start)
            param_idx += 1
        
        if end:
            query += f" AND started_at <= ${param_idx}"
            params.append(end)
            param_idx += 1
        
        query += " ORDER BY started_at ASC"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]
    
    async def calculate_gap(
        self,
        previous_course: dict,
        new_course: dict,
    ) -> int:
        """
        Calculate the gap in minutes between two courses.
        
        Args:
            previous_course: The earlier course record.
            new_course: The later course record.
            
        Returns:
            Gap in minutes (positive if gap, negative if overlap).
        """
        prev_end = previous_course.get("expected_end_at") or previous_course.get("actual_end_at")
        new_start = new_course.get("started_at")
        
        if not prev_end or not new_start:
            return 0
        
        # Handle timezone-aware datetimes
        if prev_end.tzinfo is None:
            prev_end = prev_end.replace(tzinfo=timezone.utc)
        if new_start.tzinfo is None:
            new_start = new_start.replace(tzinfo=timezone.utc)
        
        gap = new_start - prev_end
        return int(gap.total_seconds() / 60)
    
    async def _record_gap_or_overlap(
        self,
        conn,
        previous_course_id: str,
        new_course_id: str,
        new_course_started_at: datetime,
    ) -> None:
        """
        Record gap or overlap between consecutive courses.
        
        Called automatically when a new course supersedes a previous one.
        Positive gap = coverage lapse.
        Negative gap = double coverage (overlap).
        
        Args:
            conn: Database connection (within transaction).
            previous_course_id: ID of the course being superseded.
            new_course_id: ID of the new course.
            new_course_started_at: Start time of the new course.
        """
        # Get the previous course's expected end time
        row = await conn.fetchrow(
            """
            SELECT expected_end_at, status
            FROM coverage_courses
            WHERE id = $1
            """,
            previous_course_id,
        )
        
        if not row:
            return
        
        prev_end = row["expected_end_at"]
        
        # Calculate gap (positive = gap, negative = overlap)
        gap_minutes = int((new_course_started_at - prev_end).total_seconds() / 60)
        
        # Record the gap/overlap on the previous course
        if gap_minutes > 0:
            # Coverage gap
            await conn.execute(
                """
                UPDATE coverage_courses
                SET 
                    next_course_id = $1,
                    gap_minutes = $2,
                    overlap_minutes = NULL
                WHERE id = $3
                """,
                new_course_id,
                gap_minutes,
                previous_course_id,
            )
        elif gap_minutes < 0:
            # Coverage overlap (negative gap)
            await conn.execute(
                """
                UPDATE coverage_courses
                SET 
                    next_course_id = $1,
                    gap_minutes = NULL,
                    overlap_minutes = $2
                WHERE id = $3
                """,
                new_course_id,
                abs(gap_minutes),  # Store as positive number
                previous_course_id,
            )
        else:
            # Perfect handoff (no gap, no overlap)
            await conn.execute(
                """
                UPDATE coverage_courses
                SET next_course_id = $1
                WHERE id = $2
                """,
                new_course_id,
                previous_course_id,
            )
    
    async def update_course_status(
        self,
        course_id: str,
        new_status: CourseStatus,
        reason: Optional[str] = None,
        resolved_at: Optional[datetime] = None,
    ) -> dict:
        """
        Update a course's status with validation.
        
        Args:
            course_id: UUID of the course to update.
            new_status: New status value.
            reason: Reason for the transition.
            resolved_at: When the course was resolved (for closed courses).
            
        Returns:
            Updated course record.
            
        Raises:
            CourseNotFoundError: If course doesn't exist.
            InvalidStateTransitionError: If transition is not allowed.
        """
        now = datetime.now(timezone.utc)
        
        async with self.pool.acquire() as conn:
            # Get current course
            row = await conn.fetchrow(
                """
                SELECT id, patient_id, status FROM coverage_courses
                WHERE id = $1
                FOR UPDATE
                """,
                course_id,
            )
            
            if not row:
                raise CourseNotFoundError(f"Course {course_id} not found")
            
            current_status = CourseStatus(row["status"])
            
            # Validate transition
            if not validate_transition(current_status, new_status):
                raise InvalidStateTransitionError(
                    f"Cannot transition from {current_status.value} to {new_status.value}"
                )
            
            # Build update fields
            update_fields = ["status = $2", "updated_at = $3"]
            params = [course_id, new_status.value, now]
            param_idx = 4
            
            if new_status == CourseStatus.CLOSED and resolved_at:
                update_fields.append(f"actual_end_at = ${param_idx}")
                params.append(resolved_at)
                param_idx += 1
            
            # Execute update
            await conn.execute(
                f"""
                UPDATE coverage_courses
                SET {', '.join(update_fields)}
                WHERE id = $1
                """,
                *params,
            )
            
            # Fetch updated record
            updated = await conn.fetchrow(
                """
                SELECT id, patient_id, trigger_event_id, trigger_type, status,
                       started_at, expected_end_at, actual_end_at,
                       previous_course_id, next_course_id,
                       duration_minutes, is_bedtime_dose, notes,
                       gap_minutes, overlap_minutes, created_at
                FROM coverage_courses WHERE id = $1
                """,
                course_id,
            )
        
        # Publish appropriate event
        bus = get_event_bus()
        event_type = self._get_event_type_for_status(new_status)
        
        event_data = {
            "course_id": course_id,
            "patient_id": str(row["patient_id"]),
            "previous_status": current_status.value,
            "new_status": new_status.value,
            "reason": reason,
        }
        
        await bus.publish(event_type, event_data)
        
        return dict(updated)
    
    def _get_event_type_for_status(self, status: CourseStatus) -> str:
        """Map course status to event type."""
        mapping = {
            CourseStatus.WARNING_SENT: EventTypes.COVERAGE_COURSE_WARNING,
            CourseStatus.EXPIRED: EventTypes.COVERAGE_COURSE_EXPIRED,
            CourseStatus.CLOSED: EventTypes.COVERAGE_COURSE_CLOSED,
        }
        return mapping.get(status, EventTypes.COVERAGE_COURSE_CLOSED)
    
    async def get_course_by_id(self, course_id: str) -> Optional[dict]:
        """
        Get a single course by ID.
        
        Args:
            course_id: UUID of the course.
            
        Returns:
            Course record as dict, or None if not found.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, patient_id, trigger_event_id, trigger_type, status,
                       started_at, expected_end_at, actual_end_at,
                       previous_course_id, next_course_id,
                       duration_minutes, is_bedtime_dose, notes,
                       gap_minutes, overlap_minutes, created_at
                FROM coverage_courses WHERE id = $1
                """,
                course_id,
            )
        
        if not row:
            return None
        
        return dict(row)
    
    async def get_patient_courses_count(self, patient_id: str) -> int:
        """Get total course count for a patient."""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM coverage_courses WHERE patient_id = $1",
                patient_id,
            )
        return count


# Convenience functions

async def create_course_engine(database_url: str) -> CoverageCourseEngine:
    """Create a CoverageCourseEngine with connection pool."""
    pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    return CoverageCourseEngine(pool)
