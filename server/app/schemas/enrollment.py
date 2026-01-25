from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.enrollment import EnrollmentStatus


# 수강 신청 (수강생용)
class EnrollmentCreate(BaseModel):
    lesson_id: int
    student_name: str


# 수강 수정 (운영자용)
class EnrollmentUpdate(BaseModel):
    status: Optional[EnrollmentStatus] = None
    attendance_rate: Optional[float] = None


# 수강 응답
class EnrollmentResponse(BaseModel):
    id: int
    student_name: str
    lesson_id: int
    status: EnrollmentStatus
    attendance_rate: Optional[float]
    completion_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 수강 상세 응답 (강습 정보 포함)
class EnrollmentDetailResponse(EnrollmentResponse):
    lesson_title: str
    lesson_sport_type: str
    lesson_difficulty: str
    lesson_thumbnail_url: Optional[str] = None
