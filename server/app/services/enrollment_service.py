from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.lesson import Lesson
from app.models.feedback import Feedback
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate


def _get_active_thumbnail(lesson) -> Optional[str]:
    """강습의 활성 콘텐츠에서 썸네일 URL 추출"""
    if not lesson or not lesson.contents:
        return None
    for content in lesson.contents:
        if content.is_active and content.thumbnail_url:
            return content.thumbnail_url
    return None


class EnrollmentService:
    
    @staticmethod
    async def create_enrollment(db: AsyncSession, data: EnrollmentCreate) -> Enrollment:
        # 중복 수강 체크
        existing = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_name == data.student_name,
                    Enrollment.lesson_id == data.lesson_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("DUPLICATE_ENROLLMENT")
        
        enrollment = Enrollment(
            student_name=data.student_name,
            lesson_id=data.lesson_id,
            status=EnrollmentStatus.ENROLLED
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
        return enrollment
    
    @staticmethod
    async def get_enrollments_by_student(db: AsyncSession, student_name: str) -> List[dict]:
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.student_name == student_name)
            .options(
                selectinload(Enrollment.lesson).selectinload(Lesson.contents)
            )
            .order_by(desc(Enrollment.created_at))
        )
        enrollments = result.scalars().all()
        
        return [
            {
                "id": enrollment.id,
                "student_name": enrollment.student_name,
                "lesson_id": enrollment.lesson_id,
                "status": enrollment.status.value,
                "attendance_rate": enrollment.attendance_rate,
                "completion_date": enrollment.completion_date,
                "created_at": enrollment.created_at,
                "updated_at": enrollment.updated_at,
                "lesson_title": enrollment.lesson.title if enrollment.lesson else None,
                "lesson_sport_type": enrollment.lesson.sport_type.value if enrollment.lesson else None,
                "lesson_difficulty": enrollment.lesson.difficulty.value if enrollment.lesson else None,
                "lesson_thumbnail_url": _get_active_thumbnail(enrollment.lesson)
            }
            for enrollment in enrollments
        ]
    
    @staticmethod
    async def get_all_enrollments(
        db: AsyncSession,
        status: Optional[str] = None,
        lesson_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[dict]:
        query = select(Enrollment).options(
            selectinload(Enrollment.lesson).selectinload(Lesson.contents)
        )
        
        conditions = []
        if status:
            conditions.append(Enrollment.status == status)
        if lesson_id:
            conditions.append(Enrollment.lesson_id == lesson_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        enrollments = result.scalars().all()
        
        return [
            {
                "id": enrollment.id,
                "student_name": enrollment.student_name,
                "lesson_id": enrollment.lesson_id,
                "status": enrollment.status.value,
                "attendance_rate": enrollment.attendance_rate,
                "completion_date": enrollment.completion_date,
                "created_at": enrollment.created_at,
                "updated_at": enrollment.updated_at,
                "lesson_title": enrollment.lesson.title if enrollment.lesson else None,
                "lesson_sport_type": enrollment.lesson.sport_type.value if enrollment.lesson else None,
                "lesson_difficulty": enrollment.lesson.difficulty.value if enrollment.lesson else None,
                "lesson_thumbnail_url": _get_active_thumbnail(enrollment.lesson)
            }
            for enrollment in enrollments
        ]
    
    @staticmethod
    async def get_all_enrollments_paginated(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        lesson_id: Optional[int] = None
    ) -> dict:
        """전체 수강 목록 (페이징, 최신순)"""
        
        query = select(Enrollment).options(
            selectinload(Enrollment.lesson).selectinload(Lesson.contents)
        )
        count_query = select(func.count(Enrollment.id))
        
        conditions = []
        if status:
            conditions.append(Enrollment.status == status)
        if lesson_id:
            conditions.append(Enrollment.lesson_id == lesson_id)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(desc(Enrollment.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        items = list(result.scalars().all())
        
        items_with_lesson = []
        for enrollment in items:
            items_with_lesson.append({
                "id": enrollment.id,
                "student_name": enrollment.student_name,
                "lesson_id": enrollment.lesson_id,
                "status": enrollment.status.value,
                "attendance_rate": enrollment.attendance_rate,
                "completion_date": enrollment.completion_date,
                "created_at": enrollment.created_at,
                "updated_at": enrollment.updated_at,
                "lesson_title": enrollment.lesson.title if enrollment.lesson else None,
                "lesson_sport_type": enrollment.lesson.sport_type.value if enrollment.lesson else None,
                "lesson_difficulty": enrollment.lesson.difficulty.value if enrollment.lesson else None,
                "lesson_thumbnail_url": _get_active_thumbnail(enrollment.lesson)
            })
        
        return {
            "items": items_with_lesson,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    @staticmethod
    async def get_enrollment_by_id(db: AsyncSession, enrollment_id: int) -> Optional[Enrollment]:
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.id == enrollment_id)
            .options(selectinload(Enrollment.lesson))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_enrollment(
        db: AsyncSession,
        enrollment_id: int,
        data: EnrollmentUpdate
    ) -> Optional[dict]:
        enrollment = await EnrollmentService.get_enrollment_by_id(db, enrollment_id)
        if not enrollment:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(enrollment, field, value)
        
        await db.commit()
        await db.refresh(enrollment)
        
        return {
            **enrollment.__dict__,
            "lesson_title": enrollment.lesson.title,
            "lesson_sport_type": enrollment.lesson.sport_type.value,
            "lesson_difficulty": enrollment.lesson.difficulty.value
        }
    
    @staticmethod
    async def cancel_enrollment(db: AsyncSession, enrollment_id: int) -> bool:
        enrollment = await EnrollmentService.get_enrollment_by_id(db, enrollment_id)
        if not enrollment:
            return False
        
        await db.delete(enrollment)
        await db.commit()
        return True
    
    @staticmethod
    async def get_feedback(db: AsyncSession, enrollment_id: int) -> Optional[Feedback]:
        result = await db.execute(
            select(Feedback).where(Feedback.enrollment_id == enrollment_id)
        )
        return result.scalar_one_or_none()
