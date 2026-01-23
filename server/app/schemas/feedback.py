from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class FeedbackResponse(BaseModel):
    id: int
    enrollment_id: int
    student_feedback: Optional[str]
    instructor_feedback: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackUpdate(BaseModel):
    student_feedback: Optional[str] = None
    instructor_feedback: Optional[str] = None

