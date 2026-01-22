from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class CourseBase(BaseModel):
    title: str
    category: str
    description: Optional[str] = None
    curriculum: Optional[str] = None
    thumbnail_url: Optional[str] = None  # 썸네일 추가


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    curriculum: Optional[str] = None
    thumbnail_url: Optional[str] = None  # 썸네일 추가


class CourseResponse(CourseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

