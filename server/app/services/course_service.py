from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate
from app.utils.exceptions import CourseNotFoundError


class CourseService:
    @staticmethod
    async def create_course(db: AsyncSession, course_data: CourseCreate) -> Course:
        course = Course(**course_data.model_dump())
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course
    
    @staticmethod
    async def get_courses(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Course]:
        result = await db.execute(select(Course).offset(skip).limit(limit))
        return result.scalars().all()
    
    @staticmethod
    async def get_course_by_id(db: AsyncSession, course_id: int) -> Optional[Course]:
        result = await db.execute(select(Course).where(Course.id == course_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_course(
        db: AsyncSession, 
        course_id: int, 
        course_data: CourseUpdate
    ) -> Course:
        course = await CourseService.get_course_by_id(db, course_id)
        if not course:
            raise CourseNotFoundError(course_id)
        
        update_data = course_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(course, field, value)
        
        await db.commit()
        await db.refresh(course)
        return course
    
    @staticmethod
    async def delete_course(db: AsyncSession, course_id: int) -> None:
        course = await CourseService.get_course_by_id(db, course_id)
        if not course:
            raise CourseNotFoundError(course_id)
        
        db.delete(course)
        await db.commit()

