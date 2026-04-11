"""
Coverage Course Module.

Exports:
- engine: CoverageCourseEngine and related classes
- linking: CoverageCourseLinking for chain management
"""

from .engine import (
    CoverageCourseEngine,
    CourseStatus,
    CourseEngineError,
    InvalidStateTransitionError,
    CourseNotFoundError,
    CORNSTARCH_DURATION_MINUTES,
    MEAL_DURATION_MINUTES,
    create_course_engine,
)

from .linking import (
    CoverageCourseLinking,
    ChainLinkingError,
    ChainIntegrityError,
    create_course_linking,
)

__all__ = [
    # Engine
    "CoverageCourseEngine",
    "CourseStatus",
    "CourseEngineError",
    "InvalidStateTransitionError",
    "CourseNotFoundError",
    "CORNSTARCH_DURATION_MINUTES",
    "MEAL_DURATION_MINUTES",
    "create_course_engine",
    # Linking
    "CoverageCourseLinking",
    "ChainLinkingError",
    "ChainIntegrityError",
    "create_course_linking",
]
