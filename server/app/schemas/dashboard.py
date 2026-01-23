from pydantic import BaseModel, ConfigDict
from typing import Dict, Optional, List, Any
from datetime import datetime


class PeriodInfo(BaseModel):
    start_date: str
    end_date: str


class LessonStats(BaseModel):
    total: int
    published: int
    draft: int
    archived: int
    by_sport: Dict[str, int]


class EnrollmentStats(BaseModel):
    total: int
    new_in_period: int
    completed_in_period: int
    enrolled: int
    in_progress: int
    completed: int
    cancelled: int
    avg_attendance_rate: float


class InstructorStats(BaseModel):
    total: int


class AIUsageStats(BaseModel):
    total_calls: int
    by_feature: Dict[str, int]
    total_tokens: int
    avg_latency_ms: float
    edit_rate: float


class DashboardResponse(BaseModel):
    period: PeriodInfo
    lessons: LessonStats
    enrollments: EnrollmentStats
    instructors: InstructorStats
    ai_usage: AIUsageStats


class AILogResponse(BaseModel):
    id: int
    feature_type: str
    lesson_id: Optional[int]
    enrollment_id: Optional[int]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    tokens_used: Optional[int]
    latency_ms: Optional[float]
    was_edited: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

