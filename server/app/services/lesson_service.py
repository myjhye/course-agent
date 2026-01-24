from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.lesson import Lesson, LessonStatus
from app.models.lesson_content import LessonContent
from app.schemas.lesson import LessonCreate, LessonUpdate, UpdateContentRequest


class LessonService:
    @staticmethod
    async def create_lesson(db: AsyncSession, data: LessonCreate) -> Lesson:
        lesson = Lesson(**data.model_dump())
        db.add(lesson)
        await db.commit()
        await db.refresh(lesson)
        return lesson
    
    @staticmethod
    async def get_lessons(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 20, 
        status: Optional[str] = None
    ) -> List[dict]:
        query = (
            select(Lesson)
            .options(
                selectinload(Lesson.contents),
                selectinload(Lesson.instructor)
            )
        )
        if status:
            query = query.where(Lesson.status == status)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        lessons = result.scalars().all()
        
        # active_content 포함하여 반환
        return [
            {
                **lesson.__dict__,
                "active_content": next((c for c in lesson.contents if c.is_active), None)
            }
            for lesson in lessons
        ]
    
    @staticmethod
    async def get_lessons_paginated(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None
    ) -> dict:
        """강습 목록 (페이징, 최신순)"""
        
        query = select(Lesson).options(
            selectinload(Lesson.instructor),
            selectinload(Lesson.contents)
        )
        
        if status:
            query = query.where(Lesson.status == status)
        
        # 전체 개수
        count_query = select(func.count(Lesson.id))
        if status:
            count_query = count_query.where(Lesson.status == status)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 최신순 정렬 + 페이징
        query = query.order_by(desc(Lesson.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        items = list(result.scalars().all())
        
        # active_content 포함하여 반환
        items_with_content = []
        for lesson in items:
            active_content = next((c for c in lesson.contents if c.is_active), None) if lesson.contents else None
            items_with_content.append({
                "id": lesson.id,
                "title": lesson.title,
                "sport_type": lesson.sport_type.value,
                "target_audience": lesson.target_audience.value,
                "difficulty": lesson.difficulty.value,
                "instructor_id": lesson.instructor_id,
                "status": lesson.status.value,
                "created_at": lesson.created_at,
                "updated_at": lesson.updated_at,
                "instructor_name": lesson.instructor.name if lesson.instructor else None,
                "active_content": active_content
            })
        
        return {
            "items": items_with_content,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    @staticmethod
    async def get_published_lessons(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        sport_type: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> List[dict]:
        query = (
            select(Lesson)
            .options(
                selectinload(Lesson.contents),
                selectinload(Lesson.instructor)
            )
            .where(Lesson.status == LessonStatus.PUBLISHED)
        )
        if sport_type:
            query = query.where(Lesson.sport_type == sport_type)
        if difficulty:
            query = query.where(Lesson.difficulty == difficulty)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        lessons = result.scalars().all()
        
        # active_content 포함하여 반환
        return [
            {
                **lesson.__dict__,
                "active_content": next((c for c in lesson.contents if c.is_active), None)
            }
            for lesson in lessons
        ]
    
    @staticmethod
    async def get_published_lessons_paginated(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 12,
        sport_type: Optional[str] = None,
        target_audience: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> dict:
        """발행된 강습 목록 (페이징, 최신순)"""
        
        query = select(Lesson).options(
            selectinload(Lesson.instructor),
            selectinload(Lesson.contents)
        ).where(Lesson.status == LessonStatus.PUBLISHED)
        
        count_query = select(func.count(Lesson.id)).where(Lesson.status == LessonStatus.PUBLISHED)
        
        if sport_type:
            query = query.where(Lesson.sport_type == sport_type)
            count_query = count_query.where(Lesson.sport_type == sport_type)
        
        if target_audience:
            query = query.where(Lesson.target_audience == target_audience)
            count_query = count_query.where(Lesson.target_audience == target_audience)
        
        if difficulty:
            query = query.where(Lesson.difficulty == difficulty)
            count_query = count_query.where(Lesson.difficulty == difficulty)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(desc(Lesson.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        items = list(result.scalars().all())
        
        # active_content 포함하여 반환
        items_with_content = []
        for lesson in items:
            active_content = next((c for c in lesson.contents if c.is_active), None) if lesson.contents else None
            items_with_content.append({
                "id": lesson.id,
                "title": lesson.title,
                "sport_type": lesson.sport_type.value,
                "target_audience": lesson.target_audience.value,
                "difficulty": lesson.difficulty.value,
                "instructor_id": lesson.instructor_id,
                "status": lesson.status.value,
                "created_at": lesson.created_at,
                "updated_at": lesson.updated_at,
                "instructor_name": lesson.instructor.name if lesson.instructor else None,
                "active_content": active_content
            })
        
        return {
            "items": items_with_content,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    @staticmethod
    async def get_lesson_by_id(db: AsyncSession, lesson_id: int) -> Optional[Lesson]:
        result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_lesson_detail(db: AsyncSession, lesson_id: int) -> Optional[dict]:
        result = await db.execute(
            select(Lesson)
            .where(Lesson.id == lesson_id)
            .options(selectinload(Lesson.instructor), selectinload(Lesson.contents))
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            return None
        
        active_content = next((c for c in lesson.contents if c.is_active), None)
        
        return {
            **lesson.__dict__,
            "instructor_name": lesson.instructor.name if lesson.instructor else None,
            "active_content": active_content
        }
    
    @staticmethod
    async def get_published_lesson_detail(db: AsyncSession, lesson_id: int) -> Optional[dict]:
        result = await db.execute(
            select(Lesson)
            .where(and_(Lesson.id == lesson_id, Lesson.status == LessonStatus.PUBLISHED))
            .options(selectinload(Lesson.instructor), selectinload(Lesson.contents))
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            return None
        
        active_content = next((c for c in lesson.contents if c.is_active), None)
        
        return {
            **lesson.__dict__,
            "instructor_name": lesson.instructor.name if lesson.instructor else None,
            "active_content": active_content
        }
    
    @staticmethod
    async def update_lesson(
        db: AsyncSession,
        lesson_id: int,
        data: LessonUpdate
    ) -> Optional[Lesson]:
        lesson = await LessonService.get_lesson_by_id(db, lesson_id)
        if not lesson:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lesson, field, value)
        
        await db.commit()
        await db.refresh(lesson)
        return lesson
    
    @staticmethod
    async def delete_lesson(db: AsyncSession, lesson_id: int) -> bool:
        lesson = await LessonService.get_lesson_by_id(db, lesson_id)
        if not lesson:
            return False
        
        db.delete(lesson)
        await db.commit()
        return True
    
    @staticmethod
    async def publish_lesson(db: AsyncSession, lesson_id: int) -> Optional[Lesson]:
        lesson = await LessonService.get_lesson_by_id(db, lesson_id)
        if not lesson:
            return None
        
        lesson.status = LessonStatus.PUBLISHED
        await db.commit()
        await db.refresh(lesson)
        return lesson
    
    @staticmethod
    async def get_lesson_contents(db: AsyncSession, lesson_id: int) -> List[LessonContent]:
        result = await db.execute(
            select(LessonContent).where(LessonContent.lesson_id == lesson_id)
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_content(
        db: AsyncSession,
        content_id: int,
        data: UpdateContentRequest
    ) -> Optional[LessonContent]:
        result = await db.execute(
            select(LessonContent).where(LessonContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        if not content:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(content, field, value)
        
        await db.commit()
        await db.refresh(content)
        return content
    
    @staticmethod
    async def activate_content(db: AsyncSession, lesson_id: int, content_id: int) -> bool:
        # 기존 활성 콘텐츠 비활성화
        from sqlalchemy import update
        await db.execute(
            update(LessonContent)
            .where(and_(LessonContent.lesson_id == lesson_id, LessonContent.is_active == True))
            .values(is_active=False)
        )
        
        # 새 콘텐츠 활성화
        result = await db.execute(
            select(LessonContent).where(
                and_(LessonContent.id == content_id, LessonContent.lesson_id == lesson_id)
            )
        )
        content = result.scalar_one_or_none()
        if not content:
            return False
        
        content.is_active = True
        await db.commit()
        return True

