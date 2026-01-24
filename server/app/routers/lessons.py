from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas.lesson import LessonResponse, LessonDetailResponse
from app.schemas.common import PaginatedResponse
from app.services.lesson_service import LessonService

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/", response_model=PaginatedResponse)
async def get_published_lessons(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    sport_type: Optional[str] = None,
    target_audience: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """발행된 강습 목록 (페이징)"""
    result = await LessonService.get_published_lessons_paginated(
        db, page, page_size, sport_type, target_audience, difficulty
    )
    
    # dict 변환 및 datetime ISO 형식 변환
    items = []
    for lesson_data in result["items"]:
        # active_content가 모델 객체인 경우 처리
        if lesson_data.get("active_content") and not isinstance(lesson_data["active_content"], dict) and lesson_data["active_content"]:
            active_content = lesson_data["active_content"]
            lesson_data["active_content"] = {
                "thumbnail_url": active_content.thumbnail_url,
                "introduction": active_content.introduction
            }
        # datetime을 ISO 형식으로 변환
        if "created_at" in lesson_data and hasattr(lesson_data["created_at"], "isoformat"):
            lesson_data["created_at"] = lesson_data["created_at"].isoformat()
        if "updated_at" in lesson_data and hasattr(lesson_data["updated_at"], "isoformat"):
            lesson_data["updated_at"] = lesson_data["updated_at"].isoformat()
        items.append(lesson_data)
    
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"]
    }


@router.get("/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson_detail(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """강습 상세 (수강생용)"""
    lesson = await LessonService.get_published_lesson_detail(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson

