from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import Optional

from app.models.lesson import Lesson, LessonStatus
from app.models.enrollment import Enrollment
from app.models.faq import FAQ
from app.services.recommendation_service import RecommendationService



class ToolExecutor:
    """
    에이전트가 DB/RAG를 조회할 때 쓰는 실행기.

    에이전트는 tool_name만 넘기면 되고, 실제 쿼리가 어떻게 생겼는지 몰라도 된다.
    DB 쿼리가 바뀌어도 에이전트 코드는 건드릴 필요 없다.

    - _search_lessons()      → 강습 DB 검색
    - _get_lesson_detail()   → 강습 상세 DB 조회
    - _get_my_enrollments()  → 수강 현황 DB 조회
    - _search_faq()          → RAG 벡터 검색 + ILIKE 폴백
    - _get_recommendations() → 맞춤 추천 (RecommendationService에 위임)
    """

    def __init__(self, db: AsyncSession, trace_id: Optional[str] = None):
        self.db = db  # 요청 범위 DB 세션. 요청 끝나면 자동으로 닫힘
        self.trace_id = trace_id  # Langfuse trace ID. RAG 검색 시 같은 trace에 묶이도록 전달

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """
        tool_name을 보고 해당 메서드로 라우팅한다.
        반환 형식은 {"success", "data", ...}로 통일.
        """
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
        """
        강습 DB 검색. _extract_search_args가 파싱한 조건으로 Lesson 목록을 조회한다.
        결과 없으면 success=False → aggregator가 is_valid=False로 판정 → 재라우팅 시도.
        """
        # 공개된 강습만 검색 대상
        query = (
            select(Lesson)
            .options(selectinload(Lesson.instructor), selectinload(Lesson.contents))
            .where(Lesson.status == LessonStatus.PUBLISHED)
        )

        # 키워드는 제목/종목명에 ILIKE로 느슨하게 검색
        if keyword:
            query = query.where(
                or_(
                    Lesson.title.ilike(f"%{keyword}%"),
                    Lesson.sport_type.cast(str).ilike(f"%{keyword}%"),
                )
            )

        # 나머지 조건은 enum 값과 정확히 매칭
        if sport_type:
            query = query.where(Lesson.sport_type == sport_type)

        if difficulty:
            query = query.where(Lesson.difficulty == difficulty)

        if target_audience:
            query = query.where(Lesson.target_audience == target_audience)

        # 결과가 너무 많으면 LLM 프롬프트가 비대해지니까 상위 5개만
        query = query.limit(5)
        result = await self.db.execute(query)
        lessons = list(result.scalars().all())

        if not lessons:
            # filters도 같이 반환 → response_node가 "어떤 조건으로 검색했는지" 사용자에게 설명할 수 있게
            return {
                "success": False,
                "data": [],
                "filters": {
                    "sport_type": sport_type,
                    "difficulty": difficulty,
                    "target_audience": target_audience,
                    "keyword": keyword,
                },
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
                    "instructor_name": l.instructor.name if l.instructor else None,
                }
                for l in lessons
            ],
            "filters": {
                "sport_type": sport_type,
                "difficulty": difficulty,
                "target_audience": target_audience,
                "keyword": keyword,
            },
        }
    
    async def _get_lesson_detail(self, lesson_id: int) -> dict:
        """강습 상세 조회. 목록에서 특정 강습 선택 시 소개문/커리큘럼 등 상세 정보를 반환한다."""

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

        # 여러 버전 중 현재 활성 버전(is_active=True)만 사용
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
                "curriculum": active_content.curriculum if active_content else None,
            },
        }
    
    async def _get_my_enrollments(self, student_name: str) -> dict:
        """수강 현황 조회. 수강생 이름으로 전체 수강 이력을 반환한다 (진행 중/완료/취소 전부 포함)."""

        if not student_name:
            return {"success": False, "error": "student_name required"}

        result = await self.db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.lesson))
            .where(Enrollment.student_name == student_name)
        )
        enrollments = list(result.scalars().all())

        if not enrollments:
            # 수강 이력 없으면 response_node가 "아직 수강 이력이 없습니다" 안내
            return {"success": False, "data": [], "student_name": student_name}

        return {
            "success": True,
            "data": [
                {
                    "id": e.id,
                    "lesson_title": e.lesson.title if e.lesson else "알 수 없음",
                    "status": e.status.value,  # enrolled / in_progress / completed / cancelled
                    "attendance_rate": e.attendance_rate or 0,
                }
                for e in enrollments
            ],
            "student_name": student_name,
        }
    
    async def _get_recommendations(self, student_name: str) -> dict:
        """
        강습 추천. 추천 알고리즘은 RecommendationService에 위임하고 결과만 받아서 반환한다.
        추천 실패해도 다른 기능에 영향 없도록 에러만 반환한다.
        """

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
                        "reason": r["reason"],  # 개인화 추천 이유
                    }
                    for r in recommendations
                ],
                "student_name": student_name,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _search_faq(self, keyword: str) -> dict:
        """
        FAQ 검색.
        1순위: pgvector 벡터 검색 (의미 기반, 유사도 0.3 이상)
        2순위: ILIKE 폴백 (텍스트 기반) → 벡터 검색 실패하거나 결과 없을 때
        """

        if not keyword:
            return {"success": False, "data": [], "keyword": ""}

        try:
            # 순환 의존 방지를 위해 함수 내부에서 import
            from app.services.ai.embedding_service import search_similar

            rag_results = await search_similar(
                db=self.db,
                query=keyword,
                top_k=5,
                similarity_threshold=0.3,  # 유사도 0.3 미만이면 제외
                trace_id=self.trace_id,    # Langfuse 동일 trace에 묶기
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

            return await self._search_faq_fallback(keyword)

        except Exception as e:
            print(f"[RAG] 벡터 검색 에러: {e}, ILIKE 폴백")
            # 트랜잭션이 깨진 채로 쿼리하면 추가 오류가 나니까 롤백 후 폴백
            await self.db.rollback()
            try:
                return await self._search_faq_fallback(keyword)
            except Exception as e2:
                print(f"[RAG] ILIKE 폴백도 실패: {e2}")
                await self.db.rollback()
                return {
                    "success": False,
                    "data": [],
                    "keyword": keyword,
                    "error": str(e2),
                }

    async def _search_faq_fallback(self, keyword: str) -> dict:
        """
        벡터 검색 실패/결과 없을 때 사용하는 ILIKE 기반 FAQ 검색.
        텍스트 매칭이라 벡터 검색보다 품질이 낮아서 상위 3개만 반환한다.
        """

        if not keyword:
            return {"success": False, "data": [], "keyword": ""}

        # 질문/답변/키워드 중 하나라도 매칭되면 반환
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
                    "source_type": "faq",
                    "similarity": 1.0,  # 텍스트 매칭은 유사도 계산 불가하므로 1.0으로 고정
                }
                for f in faqs
            ],
            "keyword": keyword,
            "search_method": "like",
        }

