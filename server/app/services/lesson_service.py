"""
강습 생성·조회·수정·삭제·발행과 콘텐츠 관리를 처리한다.

LLM 없이 순수 DB 쿼리만 수행하며, AI 콘텐츠 생성은 content_generator.py에서 담당한다.
조회 함수는 강사 정보와 활성 콘텐츠(썸네일·소개·커리큘럼)를 함께 패키징해 반환해
프론트가 추가 요청 없이 한 번에 화면을 구성할 수 있게 한다.

함수:
- create_lesson()                    : 강습을 생성하고 저장한다.
- get_lessons()                      : 전체 강습 목록을 반환한다. (간단 조회용)
- get_lessons_paginated()            : 전체 강습 목록을 페이지네이션으로 반환한다. (관리자용)
- get_published_lessons()            : 발행된 강습 목록을 반환한다. (간단 조회용)
- get_published_lessons_paginated()  : 발행된 강습 목록을 페이지네이션으로 반환한다. (수강생용)
- get_lesson_by_id()                 : 강습 ID로 단건을 조회한다.
- get_lesson_detail()                : 강습 상세를 강사·콘텐츠 포함해 반환한다.
- get_published_lesson_detail()      : 발행된 강습 상세를 반환한다.
- update_lesson()                    : 강습 정보를 수정한다.
- delete_lesson()                    : 강습을 삭제한다.
- publish_lesson()                   : 강습 상태를 발행으로 변경한다.
- get_lesson_contents()              : 강습의 전체 콘텐츠 버전 목록을 반환한다.
- update_content()                   : 콘텐츠를 수정하고 AI 로그에 수정 여부를 기록한다.
- activate_content()                 : 특정 콘텐츠 버전을 활성화한다.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.lesson import Lesson, LessonStatus
from app.models.lesson_content import LessonContent
from app.models.ai_log import AILog
from app.schemas.lesson import LessonCreate, LessonUpdate, UpdateContentRequest


class LessonService:
    @staticmethod
    async def create_lesson(db: AsyncSession, data: LessonCreate) -> Lesson:
        """강습을 생성하고 저장한다."""
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
        """
        전체 강습 목록을 반환한다. 간단 조회용.
        활성 콘텐츠를 포함해 dict로 패키징해서 반환한다.
        페이지네이션이 필요하면 get_lessons_paginated를 사용한다.
        """
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
        """
        전체 강습 목록을 페이지네이션으로 반환한다. 관리자용.
        최신순 정렬. total·total_pages를 함께 반환해 프론트가 페이지 UI를 구성할 수 있게 한다.
        """
        query = select(Lesson).options(
            selectinload(Lesson.instructor),
            selectinload(Lesson.contents)
        )
        
        if status:
            query = query.where(Lesson.status == status)
        
        # 페이지네이션 메타 계산을 위해 전체 수를 먼저 센다
        count_query = select(func.count(Lesson.id))
        if status:
            count_query = count_query.where(Lesson.status == status)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(desc(Lesson.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        items = list(result.scalars().all())
        
        items_with_content = []
        for lesson in items:
            # 콘텐츠 버전이 여러 개일 수 있어서 활성 버전만 꺼낸다
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
        """
        발행된 강습 목록을 반환한다. 간단 조회용.
        페이지네이션이 필요하면 get_published_lessons_paginated를 사용한다.
        """
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
        difficulty: Optional[str] = None,
        search: Optional[str] = None
    ) -> dict:
        """
        발행된 강습 목록을 페이지네이션으로 반환한다. 수강생용.
        종목·대상·난이도·검색어 필터를 조합할 수 있다.
        """
        query = select(Lesson).options(
            selectinload(Lesson.instructor),
            selectinload(Lesson.contents)
        ).where(Lesson.status == LessonStatus.PUBLISHED)
        
        count_query = select(func.count(Lesson.id)).where(Lesson.status == LessonStatus.PUBLISHED)
        
        # 검색어는 제목에 ILIKE로 느슨하게 매칭
        if search:
            search_pattern = f"%{search}%"
            query = query.where(Lesson.title.ilike(search_pattern))
            count_query = count_query.where(Lesson.title.ilike(search_pattern))
        
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
        """
        강습 ID로 단건을 조회한다.
        update_lesson·delete_lesson·publish_lesson에서 대상이 존재하는지 확인하는 용도로도 쓴다.
        없으면 None을 반환한다.
        """
        result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_lesson_detail(db: AsyncSession, lesson_id: int) -> Optional[dict]:
        """
        강습 상세를 강사·콘텐츠 포함해 반환한다. 관리자용.
        발행 여부 관계없이 모든 강습을 조회한다.
        """
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
        """
        발행된 강습 상세를 반환한다. 수강생용.
        발행되지 않은 강습은 None을 반환한다.
        """
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
        """
        강습 정보를 수정한다.
        exclude_unset=True로 파싱해서 전달하지 않은 필드는 기존 값을 유지한다.
        없으면 None을 반환한다.
        """
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
        """
        강습을 삭제한다.
        없으면 False를 반환한다.
        """
        lesson = await LessonService.get_lesson_by_id(db, lesson_id)
        if not lesson:
            return False
        
        await db.delete(lesson)
        await db.commit()
        return True
    
    @staticmethod
    async def publish_lesson(db: AsyncSession, lesson_id: int) -> Optional[Lesson]:
        """
        강습 상태를 PUBLISHED로 변경한다.
        없으면 None을 반환한다.
        """
        lesson = await LessonService.get_lesson_by_id(db, lesson_id)
        if not lesson:
            return None
        
        lesson.status = LessonStatus.PUBLISHED
        await db.commit()
        await db.refresh(lesson)
        return lesson
    
    @staticmethod
    async def get_lesson_contents(db: AsyncSession, lesson_id: int) -> List[LessonContent]:
        """강습의 전체 콘텐츠 버전 목록을 반환한다. 관리자가 버전 이력을 확인할 때 사용한다."""
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
        """
        콘텐츠를 수정하고 AI 로그에 수정 여부를 기록한다.
        관리자가 AI 생성 콘텐츠를 고치면 was_edited=True로 기록해서
        대시보드의 수정률(edit_rate) 집계에 반영된다.
        없으면 None을 반환한다.
        """
        result = await db.execute(
            select(LessonContent).where(LessonContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        if not content:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(content, field, value)
        
        # 가장 최근 AI 콘텐츠 로그에 was_edited=True 기록
        # 대시보드 수정률 집계에 사용됨
        latest_log_result = await db.execute(
            select(AILog.id)
            .where(
                and_(
                    AILog.lesson_id == content.lesson_id,
                    AILog.feature_type == "content"
                )
            )
            .order_by(desc(AILog.created_at))
            .limit(1)
        )
        latest_log_id = latest_log_result.scalar_one_or_none()
        if latest_log_id:
            await db.execute(
                update(AILog)
                .where(AILog.id == latest_log_id)
                .values(was_edited=True)
            )
        
        await db.commit()
        await db.refresh(content)
        return content
    
    @staticmethod
    async def activate_content(db: AsyncSession, lesson_id: int, content_id: int) -> bool:
        """
        특정 콘텐츠 버전을 활성화한다.
        기존 활성 버전을 먼저 비활성화하고 새 버전을 활성화한다.
        활성 버전은 항상 하나만 유지된다.
        없으면 False를 반환한다.
        """
        from sqlalchemy import update

        # 기존 활성 콘텐츠 전부 비활성화
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


