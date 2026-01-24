from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.database import get_db
from app.models.lesson import Lesson
from app.schemas.lesson import (
    LessonCreate, LessonUpdate, LessonResponse, LessonDetailResponse,
    LessonContentResponse, UpdateContentRequest
)
from app.schemas.common import PaginatedResponse
from app.services.lesson_service import LessonService
from app.services.ai.content_generator import ContentGenerator

router = APIRouter(prefix="/api/admin/lessons", tags=["admin-lessons"])


@router.post("/", response_model=LessonResponse, status_code=201)
async def create_lesson(data: LessonCreate, db: AsyncSession = Depends(get_db)):
    """강습 등록"""
    return await LessonService.create_lesson(db, data)


@router.get("/", response_model=PaginatedResponse)
async def get_lessons(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """강습 목록 (페이징)"""
    result = await LessonService.get_lessons_paginated(db, page, page_size, status)
    
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
async def get_lesson(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """강습 상세"""
    lesson = await LessonService.get_lesson_detail(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    data: LessonUpdate,
    db: AsyncSession = Depends(get_db)
):
    """강습 수정"""
    lesson = await LessonService.update_lesson(db, lesson_id, data)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.delete("/{lesson_id}")
async def delete_lesson(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """강습 삭제"""
    success = await LessonService.delete_lesson(db, lesson_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return {"message": "Lesson deleted"}


@router.post("/{lesson_id}/generate-content", response_model=LessonContentResponse)
async def generate_content(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """AI 콘텐츠 생성"""
    # instructor를 미리 로드
    result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.instructor))
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    content = await ContentGenerator.generate_full_content(db, lesson)
    
    return {
        "id": content.id,
        "lesson_id": content.lesson_id,
        "introduction": content.introduction,
        "curriculum": content.curriculum,
        "thumbnail_url": content.thumbnail_url,
        "version": content.version,
        "is_active": content.is_active,
        "created_at": content.created_at.isoformat()
    }


@router.get("/{lesson_id}/contents", response_model=List[LessonContentResponse])
async def get_contents(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """콘텐츠 버전 목록"""
    return await LessonService.get_lesson_contents(db, lesson_id)


@router.put("/{lesson_id}/contents/{content_id}", response_model=LessonContentResponse)
async def update_content(
    lesson_id: int,
    content_id: int,
    data: UpdateContentRequest,
    db: AsyncSession = Depends(get_db)
):
    """콘텐츠 수정"""
    content = await LessonService.update_content(db, content_id, data)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/{lesson_id}/contents/{content_id}/activate")
async def activate_content(
    lesson_id: int,
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """콘텐츠 버전 활성화"""
    success = await LessonService.activate_content(db, lesson_id, content_id)
    if not success:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"message": "Content activated"}


@router.post("/{lesson_id}/contents/{content_id}/regenerate-introduction")
async def regenerate_introduction(
    lesson_id: int,
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """소개 문구 재생성"""
    lesson = await LessonService.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    content = await ContentGenerator.regenerate_introduction(db, lesson, content_id)
    return {"message": "소개 문구가 재생성되었습니다.", "introduction": content.introduction}


@router.post("/{lesson_id}/contents/{content_id}/regenerate-curriculum")
async def regenerate_curriculum(
    lesson_id: int,
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """커리큘럼 재생성"""
    lesson = await LessonService.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    content = await ContentGenerator.regenerate_curriculum(db, lesson, content_id)
    return {"message": "커리큘럼이 재생성되었습니다.", "curriculum": content.curriculum}


@router.post("/{lesson_id}/contents/{content_id}/regenerate-thumbnail")
async def regenerate_thumbnail(
    lesson_id: int,
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """썸네일 재생성"""
    lesson = await LessonService.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    content = await ContentGenerator.regenerate_thumbnail(db, lesson, content_id)
    return {"message": "썸네일이 재생성되었습니다.", "thumbnail_url": content.thumbnail_url}


@router.post("/{lesson_id}/publish", response_model=LessonResponse)
async def publish_lesson(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """강습 발행"""
    lesson = await LessonService.publish_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson

