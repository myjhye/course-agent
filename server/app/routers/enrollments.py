from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate, EnrollmentResponse
from app.services.enrollment_service import EnrollmentService

router = APIRouter()

# 임시 user_id (나중에 인증 붙이면 교체)
TEMP_USER_ID = 1


@router.post("/", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """수강 신청"""
    return await EnrollmentService.create_enrollment(db, TEMP_USER_ID, data)


@router.get("/", response_model=List[EnrollmentResponse])
async def get_my_enrollments(
    db: AsyncSession = Depends(get_db)
):
    """내 수강 목록 조회"""
    return await EnrollmentService.get_user_enrollments(db, TEMP_USER_ID)


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
async def get_enrollment(
    enrollment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """수강 상세 조회"""
    enrollment = await EnrollmentService.get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        from app.utils.exceptions import EnrollmentNotFoundError
        raise EnrollmentNotFoundError(enrollment_id)
    return enrollment


@router.patch("/{enrollment_id}/status", response_model=EnrollmentResponse)
async def update_enrollment_status(
    enrollment_id: int,
    data: EnrollmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """수강 상태 변경"""
    return await EnrollmentService.update_enrollment_status(db, enrollment_id, data)


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_enrollment(
    enrollment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """수강 취소"""
    await EnrollmentService.delete_enrollment(db, enrollment_id)
