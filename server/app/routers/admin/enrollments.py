from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas.enrollment import EnrollmentUpdate, EnrollmentDetailResponse
from app.schemas.feedback import FeedbackResponse
from app.schemas.common import PaginatedResponse
from app.services.enrollment_service import EnrollmentService
from app.services.ai.feedback_generator import generate_feedback as generate_feedback_ai

router = APIRouter(prefix="/api/admin/enrollments", tags=["admin-enrollments"])


@router.get("/", response_model=PaginatedResponse)
async def get_all_enrollments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[str] = None,
    lesson_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """전체 수강 목록 (페이징)"""
    result = await EnrollmentService.get_all_enrollments_paginated(
        db, page, page_size, status, lesson_id
    )
    
    # dict 변환 및 datetime ISO 형식 변환
    items = []
    for enrollment_data in result["items"]:
        # datetime을 ISO 형식으로 변환
        if "completion_date" in enrollment_data and enrollment_data["completion_date"] and hasattr(enrollment_data["completion_date"], "isoformat"):
            enrollment_data["completion_date"] = enrollment_data["completion_date"].isoformat()
        if "created_at" in enrollment_data and hasattr(enrollment_data["created_at"], "isoformat"):
            enrollment_data["created_at"] = enrollment_data["created_at"].isoformat()
        if "updated_at" in enrollment_data and hasattr(enrollment_data["updated_at"], "isoformat"):
            enrollment_data["updated_at"] = enrollment_data["updated_at"].isoformat()
        items.append(enrollment_data)
    
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"]
    }


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

