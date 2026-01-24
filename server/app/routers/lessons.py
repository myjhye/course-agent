from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from app.database import get_db
from app.schemas.lesson import LessonResponse, LessonDetailResponse
from app.schemas.common import PaginatedResponse
from app.services.lesson_service import LessonService
from app.models.lesson_interest import LessonView, LessonLike

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


@router.get("/my/liked")
async def get_liked_lessons(
    student_name: str = Query(..., description="수강생 이름"),
    db: AsyncSession = Depends(get_db)
):
    """내가 찜한 강습 목록"""
    from app.models.lesson import Lesson
    from sqlalchemy.orm import selectinload
    
    # 찜한 강습 ID 조회
    likes_result = await db.execute(
        select(LessonLike.lesson_id).where(LessonLike.student_name == student_name)
    )
    liked_ids = [row[0] for row in likes_result.fetchall()]
    
    if not liked_ids:
        return []
    
    # 강습 정보 조회 (발행된 것만)
    lessons_result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.contents))
        .where(Lesson.id.in_(liked_ids), Lesson.status == "published")
    )
    lessons = lessons_result.scalars().all()
    
    result = []
    for lesson in lessons:
        # 활성화된 콘텐츠 찾기
        active_content = next((c for c in lesson.contents if c.is_active), None)
        result.append({
            "id": lesson.id,
            "title": lesson.title,
            "sport_type": lesson.sport_type.value if hasattr(lesson.sport_type, 'value') else lesson.sport_type,
            "difficulty": lesson.difficulty.value if hasattr(lesson.difficulty, 'value') else lesson.difficulty,
            "target_audience": lesson.target_audience.value if hasattr(lesson.target_audience, 'value') else lesson.target_audience,
            "instructor_name": None,
            "thumbnail_url": active_content.thumbnail_url if active_content else None,
        })
    
    return result


@router.get("/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson_detail(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """강습 상세 (수강생용)"""
    lesson = await LessonService.get_published_lesson_detail(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.post("/{lesson_id}/view")
async def record_view(
    lesson_id: int,
    student_name: str = Query(..., description="수강생 이름"),
    db: AsyncSession = Depends(get_db)
):
    """강습 조회 기록"""
    view = LessonView(student_name=student_name, lesson_id=lesson_id)
    db.add(view)
    await db.commit()
    return {"message": "View recorded"}


@router.post("/{lesson_id}/like")
async def toggle_like(
    lesson_id: int,
    student_name: str = Query(..., description="수강생 이름"),
    db: AsyncSession = Depends(get_db)
):
    """강습 찜 토글"""
    # 기존 찜 확인
    result = await db.execute(
        select(LessonLike).where(
            LessonLike.student_name == student_name,
            LessonLike.lesson_id == lesson_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        return {"liked": False, "message": "찜 해제"}
    else:
        like = LessonLike(student_name=student_name, lesson_id=lesson_id)
        db.add(like)
        await db.commit()
        return {"liked": True, "message": "찜 완료"}


@router.get("/{lesson_id}/like-status")
async def get_like_status(
    lesson_id: int,
    student_name: str = Query(..., description="수강생 이름"),
    db: AsyncSession = Depends(get_db)
):
    """찜 상태 확인"""
    result = await db.execute(
        select(LessonLike).where(
            LessonLike.student_name == student_name,
            LessonLike.lesson_id == lesson_id
        )
    )
    existing = result.scalar_one_or_none()
    return {"liked": existing is not None}
