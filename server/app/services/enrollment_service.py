from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.models.enrollment import Enrollment
from app.schemas.enrollment import EnrollmentCreate


class EnrollmentService:
    @staticmethod
    async def create_enrollment(db: AsyncSession, enrollment_data: EnrollmentCreate) -> Enrollment:
        # TODO: 구현 예정
        pass
    
    @staticmethod
    async def get_enrollments(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Enrollment]:
        # TODO: 구현 예정
        pass

