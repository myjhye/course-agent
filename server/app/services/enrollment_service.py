from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.enrollment import Enrollment
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate
from app.utils.exceptions import EnrollmentNotFoundError, AlreadyEnrolledError


class EnrollmentService:
    
    @staticmethod
    async def create_enrollment(db: AsyncSession, user_id: int, data: EnrollmentCreate) -> Enrollment:
        # 중복 수강 체크
        existing = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == data.course_id
            )
        )
        if existing.scalar_one_or_none():
            raise AlreadyEnrolledError(data.course_id)
        
        enrollment = Enrollment(
            user_id=user_id,
            course_id=data.course_id,
            status="enrolled"
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
        return enrollment
    
    @staticmethod
    async def get_user_enrollments(db: AsyncSession, user_id: int) -> list[Enrollment]:
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.user_id == user_id)
            .options(selectinload(Enrollment.course))
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_enrollment_by_id(db: AsyncSession, enrollment_id: int) -> Enrollment | None:
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.id == enrollment_id)
            .options(selectinload(Enrollment.course))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_enrollment_status(db: AsyncSession, enrollment_id: int, data: EnrollmentUpdate) -> Enrollment:
        enrollment = await EnrollmentService.get_enrollment_by_id(db, enrollment_id)
        if not enrollment:
            raise EnrollmentNotFoundError(enrollment_id)
        
        enrollment.status = data.status
        await db.commit()
        await db.refresh(enrollment)
        return enrollment
    
    @staticmethod
    async def delete_enrollment(db: AsyncSession, enrollment_id: int) -> None:
        enrollment = await EnrollmentService.get_enrollment_by_id(db, enrollment_id)
        if not enrollment:
            raise EnrollmentNotFoundError(enrollment_id)
        
        db.delete(enrollment)
        await db.commit()
