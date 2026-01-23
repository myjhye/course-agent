from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas.enrollment import EnrollmentUpdate, EnrollmentDetailResponse
from app.schemas.feedback import FeedbackResponse
from app.services.enrollment_service import EnrollmentService
from app.services.ai.feedback_generator import generate_feedback as generate_feedback_ai

router = APIRouter(prefix="/api/admin/enrollments", tags=["admin-enrollments"])


@router.get("/", response_model=List[EnrollmentDetailResponse])
async def get_all_enrollments(
    status: Optional[str] = None,
    lesson_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """전체 수강 목록"""
    return await EnrollmentService.get_all_enrollments(db, status, lesson_id, skip, limit)


@router.put("/{enrollment_id}", response_model=EnrollmentDetailResponse)
async def update_enrollment(
    enrollment_id: int,
    data: EnrollmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """수강 상태/출석률 수정"""
    enrollment = await EnrollmentService.update_enrollment(db, enrollment_id, data)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


@router.post("/{enrollment_id}/generate-feedback", response_model=FeedbackResponse)
async def generate_feedback_endpoint(enrollment_id: int, db: AsyncSession = Depends(get_db)):
    """피드백 생성"""
    enrollment = await EnrollmentService.get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    if enrollment.status.value != "completed":
        raise HTTPException(status_code=400, detail="Only completed enrollments can have feedback")
    
    feedback = await generate_feedback_ai(db, enrollment)
    return feedback


@router.get("/{enrollment_id}/feedback", response_model=FeedbackResponse)
async def get_feedback_endpoint(enrollment_id: int, db: AsyncSession = Depends(get_db)):
    """피드백 조회"""
    feedback = await EnrollmentService.get_feedback(db, enrollment_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback

