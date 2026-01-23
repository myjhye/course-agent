from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.feedback import Feedback
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate


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
            raise ValueError(f"Already enrolled in lesson {data.lesson_id}")
        
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
            .options(selectinload(Enrollment.lesson))
        )
        enrollments = result.scalars().all()
        
        return [
            {
                **enrollment.__dict__,
                "lesson_title": enrollment.lesson.title,
                "lesson_sport_type": enrollment.lesson.sport_type.value,
                "lesson_difficulty": enrollment.lesson.difficulty.value
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
        query = select(Enrollment).options(selectinload(Enrollment.lesson))
        
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
                **enrollment.__dict__,
                "lesson_title": enrollment.lesson.title,
                "lesson_sport_type": enrollment.lesson.sport_type.value,
                "lesson_difficulty": enrollment.lesson.difficulty.value
            }
            for enrollment in enrollments
        ]
    
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
        
        db.delete(enrollment)
        await db.commit()
        return True
    
    @staticmethod
    async def get_feedback(db: AsyncSession, enrollment_id: int) -> Optional[Feedback]:
        result = await db.execute(
            select(Feedback).where(Feedback.enrollment_id == enrollment_id)
        )
        return result.scalar_one_or_none()
