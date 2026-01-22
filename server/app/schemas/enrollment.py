from pydantic import BaseModel, ConfigDict
from datetime import datetime


class EnrollmentCreate(BaseModel):
    # TODO: user_id, course_id 추가 예정
    pass


class EnrollmentResponse(BaseModel):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

