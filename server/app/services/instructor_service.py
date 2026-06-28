"""
강사 생성·조회·삭제를 처리한다.

LLM 없이 순수 DB 쿼리만 수행하며, 관리자 기능에서만 사용한다.
수정 기능은 없다. 강사 정보를 바꾸려면 삭제 후 재생성한다.

함수:
- create_instructor()      : 강사를 생성하고 저장한다.
- get_instructors()        : 전체 강사 목록을 반환한다.
- get_instructor_by_id()   : 강사 ID로 단건을 조회한다.
- delete_instructor()      : 강사를 삭제한다. 없으면 False를 반환한다.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.instructor import Instructor
from app.schemas.instructor import InstructorCreate


class InstructorService:
    @staticmethod
    async def create_instructor(db: AsyncSession, data: InstructorCreate) -> Instructor:
        """강사를 생성하고 저장한다."""
        instructor = Instructor(**data.model_dump())
        db.add(instructor)
        await db.commit()
        await db.refresh(instructor)
        return instructor
    
    @staticmethod
    async def get_instructors(db: AsyncSession) -> List[Instructor]:
        """전체 강사 목록을 반환한다."""
        result = await db.execute(select(Instructor))
        return result.scalars().all()
    
    @staticmethod
    async def get_instructor_by_id(db: AsyncSession, instructor_id: int) -> Optional[Instructor]:
        """
        강사 ID로 단건을 조회한다.
        없으면 None을 반환한다.
        delete_instructor에서 대상이 존재하는지 확인하는 용도로도 쓴다.
        """
        result = await db.execute(select(Instructor).where(Instructor.id == instructor_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_instructor(db: AsyncSession, instructor_id: int) -> bool:
        """
        강사를 삭제한다.
        없으면 False를 반환한다.
        """
        instructor = await InstructorService.get_instructor_by_id(db, instructor_id)
        if not instructor:
            return False
        
        await db.delete(instructor)
        await db.commit()
        return True


