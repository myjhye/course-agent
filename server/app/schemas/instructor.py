from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class InstructorCreate(BaseModel):
    name: str
    specialty: Optional[str] = None
    bio: Optional[str] = None


class InstructorResponse(BaseModel):
    id: int
    name: str
    specialty: Optional[str]
    bio: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

