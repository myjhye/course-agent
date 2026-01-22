from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ChatCreate(BaseModel):
    # TODO: user_id, course_id, message 등 필드 추가 예정
    pass


class ChatResponse(BaseModel):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

