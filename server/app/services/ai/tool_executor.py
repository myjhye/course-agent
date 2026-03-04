from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import Any

from app.models.lesson import Lesson, LessonStatus
from app.models.enrollment import Enrollment
from app.models.faq import FAQ
from app.services.recommendation_service import RecommendationService


class ToolExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """도구 실행"""

        if tool_name == "search_lessons":
            return await self._search_lessons(
                keyword=arguments.get("keyword"),
                sport_type=arguments.get("sport_type"),
                difficulty=arguments.get("difficulty"),
                target_audience=arguments.get("target_audience"),
            )

        elif tool_name == "get_lesson_detail":
            return await self._get_lesson_detail(arguments.get("lesson_id"))

        elif tool_name == "get_my_enrollments":
            return await self._get_my_enrollments(arguments.get("student_name"))

        elif tool_name == "get_recommendations":
            return await self._get_recommendations(arguments.get("student_name"))

        elif tool_name == "search_faq":
            return await self._search_faq(arguments.get("keyword"))

        return {"success": False, "error": "Unknown tool"}

    async def _search_lessons(
        self,
        keyword: str = None,
        sport_type: str = None,
        difficulty: str = None,
        target_audience: str = None,
    ) -> dict:
        """강습 검색"""
        
        query = (
            select(Lesson)
            .options(selectinload(Lesson.instructor), selectinload(Lesson.contents))
            .where(Lesson.status == LessonStatus.PUBLISHED)
        )
        
        if keyword:
            query = query.where(
                or_(
                    Lesson.title.ilike(f"%{keyword}%"),
                    Lesson.sport_type.cast(str).ilike(f"%{keyword}%")
                )
            )
        
        if sport_type:
            query = query.where(Lesson.sport_type == sport_type)
        
        if difficulty:
            query = query.where(Lesson.difficulty == difficulty)
        
        if target_audience:
            query = query.where(Lesson.target_audience == target_audience)
        
        query = query.limit(5)
        result = await self.db.execute(query)
        lessons = list(result.scalars().all())
        
        if not lessons:
            return {
                "success": False, 
                "data": [], 
                "filters": {
                    "sport_type": sport_type,
                    "difficulty": difficulty,
                    "target_audience": target_audience,
                    "keyword": keyword
                }
            }
        
        return {
            "success": True,
            "data": [
                {
                    "id": l.id,
                    "title": l.title,
                    "sport_type": l.sport_type.value,
                    "difficulty": l.difficulty.value,
                    "target_audience": l.target_audience.value,
                    "instructor_name": l.instructor.name if l.instructor else None
                }
                for l in lessons
            ],
            "filters": {
                "sport_type": sport_type,
                "difficulty": difficulty,
                "target_audience": target_audience,
                "keyword": keyword
            }
        }
    
    async def _get_lesson_detail(self, lesson_id: int) -> dict:
        """강습 상세"""
        
        if not lesson_id:
            return {"success": False, "error": "lesson_id required"}
        
        result = await self.db.execute(
            select(Lesson)
            .options(selectinload(Lesson.instructor), selectinload(Lesson.contents))
            .where(Lesson.id == lesson_id, Lesson.status == LessonStatus.PUBLISHED)
        )
        lesson = result.scalar_one_or_none()
        
        if not lesson:
            return {"success": False, "data": None}
        
        active_content = next((c for c in lesson.contents if c.is_active), None)
        
        return {
            "success": True,
            "data": {
                "id": lesson.id,
                "title": lesson.title,
                "sport_type": lesson.sport_type.value,
                "difficulty": lesson.difficulty.value,
                "target_audience": lesson.target_audience.value,
                "instructor_name": lesson.instructor.name if lesson.instructor else None,
                "introduction": active_content.introduction if active_content else None,
                "curriculum": active_content.curriculum if active_content else None
            }
        }
    
    async def _get_my_enrollments(self, student_name: str) -> dict:
        """내 수강 현황"""
        
        if not student_name:
            return {"success": False, "error": "student_name required"}
        
        result = await self.db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.lesson))
            .where(Enrollment.student_name == student_name)
        )
        enrollments = list(result.scalars().all())
        
        if not enrollments:
            return {"success": False, "data": [], "student_name": student_name}
        
        return {
            "success": True,
            "data": [
                {
                    "id": e.id,
                    "lesson_title": e.lesson.title if e.lesson else "알 수 없음",
                    "status": e.status.value,
                    "attendance_rate": e.attendance_rate or 0
                }
                for e in enrollments
            ],
            "student_name": student_name
        }
    
    async def _get_recommendations(self, student_name: str) -> dict:
        """강습 추천"""
        
        if not student_name:
            return {"success": False, "error": "student_name required"}
        
        try:
            recommendations = await RecommendationService.get_recommendations(
                self.db, student_name, limit=3
            )
            
            if not recommendations:
                return {"success": False, "data": [], "student_name": student_name}
            
            return {
                "success": True,
                "data": [
                    {
                        "lesson_title": r["lesson"]["title"],
                        "sport_type": r["lesson"]["sport_type"],
                        "difficulty": r["lesson"]["difficulty"],
                        "reason": r["reason"]
                    }
                    for r in recommendations
                ],
                "student_name": student_name
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _search_faq(self, keyword: str) -> dict:
        """FAQ 검색"""
        
        if not keyword:
            return {"success": False, "data": [], "keyword": ""}

        # RAG 벡터 검색 + ILIKE 폴백
        try:
            from app.services.ai.embedding_service import search_similar

            rag_results = await search_similar(
                db=self.db,
                query=keyword,
                top_k=5,
                similarity_threshold=0.3,
            )

            if rag_results:
                return {
                    "success": True,
                    "data": [
                        {
                            "title": r["title"],
                            "content": r["content"],
                            "source_type": r["source_type"],
                            "similarity": r["similarity"],
                        }
                        for r in rag_results
                    ],
                    "keyword": keyword,
                    "search_method": "vector",
                }

            # 벡터 검색 결과가 없으면 폴백
            return await self._search_faq_fallback(keyword)

        except Exception as e:
            # 임베딩/pgvector 에러 시 안전하게 폴백
            print(f"[RAG] vector search error: {e}")
            return await self._search_faq_fallback(keyword)

    async def _search_faq_fallback(self, keyword: str) -> dict:
        """벡터 검색 실패 시 기존 ILIKE 기반 FAQ 검색."""

        if not keyword:
            return {"success": False, "data": [], "keyword": ""}

        result = await self.db.execute(
            select(FAQ).where(
                or_(
                    FAQ.question.ilike(f"%{keyword}%"),
                    FAQ.answer.ilike(f"%{keyword}%"),
                    FAQ.keywords.ilike(f"%{keyword}%"),
                )
            ).limit(3)
        )
        faqs = list(result.scalars().all())

        if not faqs:
            return {"success": False, "data": [], "keyword": keyword}

        return {
            "success": True,
            "data": [
                {
                    "title": f.question,
                    "content": f.answer,
                }
                for f in faqs
            ],
            "keyword": keyword,
            "search_method": "ilike_fallback",
        }

