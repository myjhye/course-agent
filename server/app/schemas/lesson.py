from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.lesson import SportType, TargetAudience, Difficulty, LessonStatus


# 강습 생성 (운영자)
class LessonCreate(BaseModel):
    title: str
    sport_type: SportType
    target_audience: TargetAudience = TargetAudience.ADULT
    difficulty: Difficulty = Difficulty.BEGINNER
    instructor_id: Optional[int] = None


# 강습 수정
class LessonUpdate(BaseModel):
    title: Optional[str] = None
    sport_type: Optional[SportType] = None
    target_audience: Optional[TargetAudience] = None
    difficulty: Optional[Difficulty] = None
    instructor_id: Optional[int] = None
    status: Optional[LessonStatus] = None


# 콘텐츠 응답 (LessonResponse보다 먼저 정의)
class LessonContentResponse(BaseModel):
    id: int
    lesson_id: int
    introduction: Optional[str]
    curriculum: Optional[dict]
    thumbnail_url: Optional[str]
    version: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 강습 응답 (기본)
class LessonResponse(BaseModel):
    id: int
    title: str
    sport_type: SportType
    target_audience: TargetAudience
    difficulty: Difficulty
    instructor_id: Optional[int]
    status: LessonStatus
    created_at: datetime
    updated_at: datetime
    active_content: Optional[LessonContentResponse] = None

    model_config = ConfigDict(from_attributes=True)


# 강습 상세 응답 (콘텐츠 포함)
class LessonDetailResponse(LessonResponse):
    instructor_name: Optional[str] = None
    active_content: Optional[LessonContentResponse] = None


# 콘텐츠 생성 요청
class GenerateContentRequest(BaseModel):
    pass  # lesson 정보만 있으면 됨


# 콘텐츠 수정 요청
class UpdateContentRequest(BaseModel):
    introduction: Optional[str] = None
    curriculum: Optional[dict] = None


# 주차 재생성 요청
class RegenerateWeekRequest(BaseModel):
    week_number: int


# Forward reference 해결을 위한 안전장치
LessonResponse.model_rebuild()
LessonDetailResponse.model_rebuild()
