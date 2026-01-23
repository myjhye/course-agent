from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas.lesson import LessonResponse, LessonDetailResponse
from app.services.lesson_service import LessonService

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/", response_model=List[LessonResponse])
async def get_published_lessons(
    skip: int = 0,
    limit: int = 20,
    sport_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """발행된 강습 목록 (수강생용)"""
    return await LessonService.get_published_lessons(db, skip, limit, sport_type, difficulty)


@router.get("/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson_detail(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """강습 상세 (수강생용)"""
    lesson = await LessonService.get_published_lesson_detail(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson

