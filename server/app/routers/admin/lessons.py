from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas.lesson import (
    LessonCreate, LessonUpdate, LessonResponse, LessonDetailResponse,
    LessonContentResponse, UpdateContentRequest
)
from app.services.lesson_service import LessonService
from app.services.ai.content_generator import generate_lesson_content

router = APIRouter(prefix="/api/admin/lessons", tags=["admin-lessons"])


@router.post("/", response_model=LessonResponse, status_code=201)
async def create_lesson(data: LessonCreate, db: AsyncSession = Depends(get_db)):
    """강습 등록"""
    return await LessonService.create_lesson(db, data)


@router.get("/", response_model=List[LessonResponse])
async def get_lessons(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """강습 목록 (운영자용 - 전체)"""
    return await LessonService.get_lessons(db, skip, limit, status)


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
    lesson = await LessonService.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    content = await generate_lesson_content(db, lesson)
    return content


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


@router.post("/{lesson_id}/publish", response_model=LessonResponse)
async def publish_lesson(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """강습 발행"""
    lesson = await LessonService.publish_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson

