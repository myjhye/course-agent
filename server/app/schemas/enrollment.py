from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.schemas.course import CourseResponse


class EnrollmentBase(BaseModel):
    course_id: int


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentUpdate(BaseModel):
    status: str  # enrolled, in_progress, completed


class EnrollmentResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    course: Optional[CourseResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
