from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse, CourseDraftRequest, CourseDraftResponse
from app.services.course_service import CourseService
from app.services.ai.content_generator import generate_course_draft
from app.utils.exceptions import CourseNotFoundError

router = APIRouter()


@router.post("/draft", response_model=CourseDraftResponse)
async def create_course_draft(
    draft_request: CourseDraftRequest
):
    """AI로 강의 초안 생성 (DB 저장 없음)"""
    draft = await generate_course_draft(draft_request.topic)
    return CourseDraftResponse(**draft)


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    db: AsyncSession = Depends(get_db)
):
    """강의 생성"""
    return await CourseService.create_course(db, course_data)


@router.get("/", response_model=List[CourseResponse])
async def get_courses(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """강의 목록 조회"""
    return await CourseService.get_courses(db, skip=skip, limit=limit)


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    """강의 상세 조회"""
    course = await CourseService.get_course_by_id(db, course_id)
    if not course:
        raise CourseNotFoundError(course_id)
    return course


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """강의 수정"""
    try:
        return await CourseService.update_course(db, course_id, course_data)
    except CourseNotFoundError as e:
        raise e


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    """강의 삭제"""
    try:
        await CourseService.delete_course(db, course_id)
    except CourseNotFoundError as e:
        raise e

# 기존 POST /{id}/generate 엔드포인트는 Draft API로 대체됨
# @router.post("/{course_id}/generate", response_model=CourseResponse)
# async def generate_course_ai_content(...):
#     ...

