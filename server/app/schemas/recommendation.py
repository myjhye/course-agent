from pydantic import BaseModel, ConfigDict
from typing import Optional


class RecommendedLesson(BaseModel):
    id: int
    title: str
    sport_type: str
    target_audience: str
    difficulty: str
    instructor_name: Optional[str] = None
    thumbnail_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    lesson: RecommendedLesson
    reason: str
    reason_type: str  # next_level, new_sport, popular

