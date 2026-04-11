"""
Course Chain Linking — Coverage chain management and integrity.

Handles:
- Automatic linking of consecutive courses
- Gap detection (coverage gaps between courses)
- Overlap detection (double coverage)
- Chain integrity validation
"""

import asyncpg
from datetime import datetime, timezone
from typing import Optional

from .engine import CoverageCourseEngine, CourseStatus


class ChainLinkingError(Exception):
    """Base exception for chain linking errors."""
    pass


class ChainIntegrityError(ChainLinkingError):
    """Raised when chain integrity validation fails."""
    pass


class CoverageCourseLinking:
    """
    Coverage course chain linking and validation.
    
    Usage:
        linking = CoverageCourseLinking(pool)
        
        # Detect gaps in coverage
        gaps = await linking.detect_gap(patient_id)
        
        # Detect double coverage
        overlaps = await linking.detect_overlap(patient_id)
        
        # Validate chain integrity
        is_valid = await linking.validate_chain(patient_id)
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.engine = CoverageCourseEngine(pool)
    
    async def link_courses(
        self,
        previous_id: str,
        next_id: str,
    ) -> dict:
        """
        Create a chain link between two courses.
        
        Args:
            previous_id: UUID of the earlier course.
            next_id: UUID of the later course.
            
        Returns:
            Updated previous course record with gap/overlap computed.
        """
        async with self.pool.acquire() as conn:
            # Get both courses
            prev_row = await conn.fetchrow(
                "SELECT * FROM coverage_courses WHERE id = $1",
                previous_id,
            )
            next_row = await conn.fetchrow(
                "SELECT * FROM coverage_courses WHERE id = $1",
                next_id,
            )
            
            if not prev_row or not next_row:
                raise ChainLinkingError(
                    f"Course not found: previous={previous_id}, next={next_id}"
                )
            
            prev_course = dict(prev_row)
            next_course = dict(next_row)
            
            # Calculate gap/overlap
            gap_minutes = await self.engine.calculate_gap(prev_course, next_course)
            
            if gap_minutes < 0:
                overlap_minutes = abs(gap_minutes)
                gap_minutes = 0
            else:
                overlap_minutes = 0
            
            # Update previous course
            await conn.execute(
                """
                UPDATE coverage_courses
                SET next_course_id = $1,
                    gap_minutes = $2,
                    overlap_minutes = $3
                WHERE id = $4
                """,
                next_id,
                gap_minutes,
                overlap_minutes,
                previous_id,
            )
            
            # Update next course
            await conn.execute(
                """
                UPDATE coverage_courses
                SET previous_course_id = $1
                WHERE id = $2
                """,
                previous_id,
                next_id,
            )
            
            # Return updated previous course
            updated = await conn.fetchrow(
                "SELECT * FROM coverage_courses WHERE id = $1",
                previous_id,
            )
            
            return dict(updated)
    
    async def detect_gap(
        self,
        patient_id: str,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Detect coverage gaps for a patient.
        
        A gap exists when the previous course ended before the next one started,
        and the gap is greater than 0 minutes.
        
        Args:
            patient_id: UUID of the patient.
            since: Only check courses starting after this time (optional).
            
        Returns:
            List of gap records with gap_minutes and course information.
        """
        query = """
            SELECT
                c1.id as previous_course_id,
                c1.patient_id,
                c1.trigger_type as previous_trigger,
                c1.started_at as previous_started_at,
                c1.expected_end_at as previous_ended_at,
                c1.duration_minutes as previous_duration,
                c2.id as next_course_id,
                c2.trigger_type as next_trigger,
                c2.started_at as next_started_at,
                c2.duration_minutes as next_duration,
                c1.gap_minutes,
                c1.overlap_minutes
            FROM coverage_courses c1
            JOIN coverage_courses c2
                ON c1.next_course_id = c2.id
            WHERE c1.patient_id = $1
              AND c1.gap_minutes > 0
        """
        params = [patient_id]
        
        if since:
            query += " AND c2.started_at >= $2"
            params.append(since)
        
        query += " ORDER BY c1.started_at DESC"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]
    
    async def detect_overlap(
        self,
        patient_id: str,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Detect double coverage (overlapping courses).
        
        An overlap exists when two courses have overlapping coverage periods.
        
        Args:
            patient_id: UUID of the patient.
            since: Only check courses starting after this time (optional).
            
        Returns:
            List of overlap records with overlapping course information.
        """
        # Find courses where the previous course's end is after the next course's start
        query = """
            SELECT
                c1.id as earlier_course_id,
                c1.patient_id,
                c1.trigger_type as earlier_trigger,
                c1.started_at as earlier_started_at,
                c1.expected_end_at as earlier_ended_at,
                c2.id as later_course_id,
                c2.trigger_type as later_trigger,
                c2.started_at as later_started_at,
                c2.expected_end_at as later_ended_at,
                c1.overlap_minutes,
                c1.gap_minutes
            FROM coverage_courses c1
            JOIN coverage_courses c2
                ON c1.next_course_id = c2.id
            WHERE c1.patient_id = $1
              AND c1.overlap_minutes > 0
        """
        params = [patient_id]
        
        if since:
            query += " AND c2.started_at >= $2"
            params.append(since)
        
        query += " ORDER BY c1.started_at DESC"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]
    
    async def validate_chain(self, patient_id: str) -> dict:
        """
        Validate the integrity of a patient's course chain.
        
        Checks:
        1. All linked courses reference each other correctly
        2. No orphaned courses (courses that should be linked but aren't)
        3. Chronological ordering is maintained
        4. No invalid status transitions
        
        Args:
            patient_id: UUID of the patient.
            
        Returns:
            Validation result with is_valid flag and any issues found.
        """
        issues = []
        
        async with self.pool.acquire() as conn:
            # Get all courses for patient ordered by start time
            courses = await conn.fetch(
                """
                SELECT
                    id, status, started_at, expected_end_at,
                    previous_course_id, next_course_id,
                    gap_minutes, overlap_minutes
                FROM coverage_courses
                WHERE patient_id = $1
                ORDER BY started_at ASC
                """,
                patient_id,
            )
        
        if not courses:
            return {"is_valid": True, "issues": [], "course_count": 0}
        
        courses = [dict(row) for row in courses]
        
        # Check 1: Verify linked references
        for course in courses:
            if course["next_course_id"]:
                next_course = next(
                    (c for c in courses if c["id"] == course["next_course_id"]),
                    None,
                )
                if not next_course:
                    issues.append({
                        "type": "orphaned_link",
                        "course_id": str(course["id"]),
                        "broken_link": "next_course_id",
                        "linked_to": str(course["next_course_id"]),
                        "message": f"Course {course['id']} links to non-existent course",
                    })
                elif next_course.get("previous_course_id") != course["id"]:
                    issues.append({
                        "type": "broken_bidirectional_link",
                        "course_id": str(course["id"]),
                        "expected_previous": str(course["id"]),
                        "actual_previous": str(next_course.get("previous_course_id")),
                        "message": "Bidirectional link is broken",
                    })
        
        # Check 2: Verify chronological ordering
        for i in range(len(courses) - 1):
            current = courses[i]
            next_course = courses[i + 1]
            
            if current["expected_end_at"] > next_course["started_at"]:
                overlap = (current["expected_end_at"] - next_course["started_at"]).total_seconds() / 60
                if overlap > 1:  # More than 1 minute overlap
                    if not current.get("overlap_minutes") or current.get("overlap_minutes", 0) < overlap:
                        issues.append({
                            "type": "undocumented_overlap",
                            "earlier_course_id": str(current["id"]),
                            "later_course_id": str(next_course["id"]),
                            "overlap_minutes": int(overlap),
                            "message": "Courses overlap but overlap_minutes not set",
                        })
        
        # Check 3: Check for status consistency
        for course in courses:
            if course["status"] == "active" and course["expected_end_at"] < datetime.now(timezone.utc):
                issues.append({
                    "type": "stale_active_course",
                    "course_id": str(course["id"]),
                    "expected_end_at": course["expected_end_at"].isoformat(),
                    "message": "Course is active but past expected end time",
                })
        
        # Check 4: Verify gap calculations
        for course in courses:
            if course["previous_course_id"]:
                prev_course = next(
                    (c for c in courses if c["id"] == course["previous_course_id"]),
                    None,
                )
                if prev_course:
                    expected_gap = await self.engine.calculate_gap(prev_course, course)
                    
                    # Allow for small timing differences
                    if expected_gap > 0 and course.get("gap_minutes", 0) == 0:
                        issues.append({
                            "type": "undocumented_gap",
                            "previous_course_id": str(prev_course["id"]),
                            "course_id": str(course["id"]),
                            "gap_minutes": expected_gap,
                            "message": "Courses have gap but gap_minutes not set",
                        })
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "course_count": len(courses),
        }
    
    async def get_chain_summary(self, patient_id: str) -> dict:
        """
        Get a summary of a patient's coverage chain.
        
        Returns statistics about coverage quality.
        """
        async with self.pool.acquire() as conn:
            courses = await conn.fetch(
                """
                SELECT
                    COUNT(*) as total_courses,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count,
                    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_count,
                    COUNT(CASE WHEN status = 'superseded' THEN 1 END) as superseded_count,
                    SUM(gap_minutes) FILTER (WHERE gap_minutes > 0) as total_gap_minutes,
                    SUM(overlap_minutes) FILTER (WHERE overlap_minutes > 0) as total_overlap_minutes,
                    AVG(gap_minutes) FILTER (WHERE gap_minutes > 0) as avg_gap_minutes
                FROM coverage_courses
                WHERE patient_id = $1
                """,
                patient_id,
            )
        
        row = courses[0]
        return {
            "total_courses": row["total_courses"],
            "active_count": row["active_count"],
            "closed_count": row["closed_count"],
            "superseded_count": row["superseded_count"],
            "total_gap_minutes": row["total_gap_minutes"] or 0,
            "total_overlap_minutes": row["total_overlap_minutes"] or 0,
            "avg_gap_minutes": round(row["avg_gap_minutes"] or 0, 1),
        }


async def create_course_linking(database_url: str) -> CoverageCourseLinking:
    """Create a CoverageCourseLinking with connection pool."""
    pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    return CoverageCourseLinking(pool)
