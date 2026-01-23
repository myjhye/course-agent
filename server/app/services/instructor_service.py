from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.instructor import Instructor
from app.schemas.instructor import InstructorCreate


class InstructorService:
    @staticmethod
    async def create_instructor(db: AsyncSession, data: InstructorCreate) -> Instructor:
        instructor = Instructor(**data.model_dump())
        db.add(instructor)
        await db.commit()
        await db.refresh(instructor)
        return instructor
    
    @staticmethod
    async def get_instructors(db: AsyncSession) -> List[Instructor]:
        result = await db.execute(select(Instructor))
        return result.scalars().all()
    
    @staticmethod
    async def get_instructor_by_id(db: AsyncSession, instructor_id: int) -> Optional[Instructor]:
        result = await db.execute(select(Instructor).where(Instructor.id == instructor_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_instructor(db: AsyncSession, instructor_id: int) -> bool:
        instructor = await InstructorService.get_instructor_by_id(db, instructor_id)
        if not instructor:
            return False
        
        db.delete(instructor)
        await db.commit()
        return True

