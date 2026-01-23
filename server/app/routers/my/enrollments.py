from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas.enrollment import EnrollmentCreate, EnrollmentDetailResponse
from app.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/api/my/enrollments", tags=["my-enrollments"])


@router.post("/", response_model=EnrollmentDetailResponse, status_code=201)
async def create_enrollment(data: EnrollmentCreate, db: AsyncSession = Depends(get_db)):
    """수강 신청"""
    try:
        enrollment = await EnrollmentService.create_enrollment(db, data)
        # 상세 정보 조회
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from app.models.enrollment import Enrollment
        
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.id == enrollment.id)
            .options(selectinload(Enrollment.lesson))
        )
        enrollment_detail = result.scalar_one_or_none()
        if not enrollment_detail:
            raise HTTPException(status_code=404, detail="Enrollment not found")
        
        return {
            **enrollment_detail.__dict__,
            "lesson_title": enrollment_detail.lesson.title,
            "lesson_sport_type": enrollment_detail.lesson.sport_type.value,
            "lesson_difficulty": enrollment_detail.lesson.difficulty.value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[EnrollmentDetailResponse])
async def get_my_enrollments(
    student_name: str,  # 쿼리 파라미터로 받음 (인증 없으니까)
    db: AsyncSession = Depends(get_db)
):
    """내 수강 목록"""
    return await EnrollmentService.get_enrollments_by_student(db, student_name)


@router.delete("/{enrollment_id}")
async def cancel_enrollment(enrollment_id: int, db: AsyncSession = Depends(get_db)):
    """수강 취소"""
    success = await EnrollmentService.cancel_enrollment(db, enrollment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return {"message": "Enrollment cancelled"}

