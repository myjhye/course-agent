from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import Any, Optional

from app.models.lesson import Lesson, LessonStatus
from app.models.enrollment import Enrollment
from app.models.faq import FAQ
from app.services.recommendation_service import RecommendationService


class ToolExecutor:
    """
    LangGraph 에이전트가 사용할 실제 비즈니스 도구들을 모아 둔 실행기.

    Router/노드 쪽에서는 \"도구 이름 + 인자\"만 넘기고, DB 세션에 직접 접근하지 않는다.
    이렇게 분리해 두면:
    - 에이전트 로직(프롬프트/재시도)과 DB/쿼리 구현을 느슨하게 결합할 수 있고
    - 테스트 시에는 ToolExecutor만 별도로 호출해 비즈니스 결과를 검증하기 쉽다.
    """

    def __init__(self, db: AsyncSession, trace_id: Optional[str] = None):
        # LangGraph에서 전달된 요청 범위 DB 세션을 보관한다.
        self.db = db
        # Langfuse 상에서의 trace/루트 span ID (있을 경우). RAG 검색 시 embedding_service에 그대로 전달한다.
        self.trace_id = trace_id

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """
        도구 이름과 인자를 받아 실제 도구 메서드를 라우팅한다.

        LangGraph 쪽에서는 이 메서드만 알면 되고, 개별 도구 구현 상세는 숨긴다.
        반환 형식은 {\"success\", \"data\", ...}로 통일해 Validator/Response 노드가 일관되게 처리할 수 있게 한다.
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

        # 정의되지 않은 도구 이름이 들어오면 명시적으로 실패 응답을 주어, LLM이 잘못된 tool_name을
        # 생성했을 때도 디버깅이 쉽도록 한다.
        return {"success": False, "error": "Unknown tool"}

    async def _search_lessons(
        self,
        keyword: str = None,
        sport_type: str = None,
        difficulty: str = None,
        target_audience: str = None,
    ) -> dict:
        """
        강습 검색 도구.

        Router/추출 노드에서 만든 검색 인자를 그대로 받아 Lesson 목록을 조회한다.
        검색 파라미터는 그대로 \"filters\"로 돌려줘서 Response 노드가
        \"어떤 조건으로 검색했는지\"를 사용자에게 설명할 수 있게 한다.
        """

        # 공개된 강습(PUBLISHED)만 검색 대상으로 삼는다.
        query = (
            select(Lesson)
            .options(selectinload(Lesson.instructor), selectinload(Lesson.contents))
            .where(Lesson.status == LessonStatus.PUBLISHED)
        )

        # 키워드는 제목/종목명에 대해 ILIKE로 느슨하게 검색해 첫 번째 진입 장벽을 낮춘다.
        if keyword:
            query = query.where(
                or_(
                    Lesson.title.ilike(f"%{keyword}%"),
                    Lesson.sport_type.cast(str).ilike(f"%{keyword}%"),
                )
            )

        # 나머지 파라미터는 enum 값과 정확히 매칭되도록 필터링한다.
        if sport_type:
            query = query.where(Lesson.sport_type == sport_type)

        if difficulty:
            query = query.where(Lesson.difficulty == difficulty)

        if target_audience:
            query = query.where(Lesson.target_audience == target_audience)

        # 한번에 너무 많은 결과를 보내면 LLM 프롬프트가 비대해지므로 상위 5개까지만 가져온다.
        query = query.limit(5)
        result = await self.db.execute(query)
        lessons = list(result.scalars().all())

        if not lessons:
            # 결과 없음도 명시적으로 success=False + data=[]로 표현해 Validator/Response가
            # \"검색 결과 없음\" 분기를 태울 수 있게 한다.
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
        """
        강습 상세 조회 도구.

        목록에서 특정 강습을 골랐을 때, 수강 판단에 필요한 상세 정보(소개/커리큘럼)를 제공한다.
        """

        if not lesson_id:
            # lesson_id가 없으면 어떤 강습을 봐야 할지 알 수 없으므로 바로 실패 처리한다.
            return {"success": False, "error": "lesson_id required"}

        result = await self.db.execute(
            select(Lesson)
            .options(selectinload(Lesson.instructor), selectinload(Lesson.contents))
            .where(Lesson.id == lesson_id, Lesson.status == LessonStatus.PUBLISHED)
        )
        lesson = result.scalar_one_or_none()

        if not lesson:
            return {"success": False, "data": None}

        # 여러 콘텐츠 버전 중 현재 활성 버전(is_active)을 우선 사용한다.
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
        """
        내 수강 현황 조회 도구.

        로그인/이름 기반으로 사용자의 수강 중/수강 완료 강좌를 보여준다.
        """

        if not student_name:
            # 누가 물어봤는지 없으면 수강 현황을 찾을 수 없으므로 실패 처리.
            return {"success": False, "error": "student_name required"}

        result = await self.db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.lesson))
            .where(Enrollment.student_name == student_name)
        )
        enrollments = list(result.scalars().all())

        if not enrollments:
            # 수강 내역이 없는 것도 data=[]로 명시해, Response 쪽에서 \"아직 수강 이력이 없습니다\"라고 안내할 수 있게 한다.
            return {"success": False, "data": [], "student_name": student_name}

        return {
            "success": True,
            "data": [
                {
                    "id": e.id,
                    "lesson_title": e.lesson.title if e.lesson else "알 수 없음",
                    "status": e.status.value,
                    "attendance_rate": e.attendance_rate or 0,
                }
                for e in enrollments
            ],
            "student_name": student_name,
        }
    
    async def _get_recommendations(self, student_name: str) -> dict:
        """
        강습 추천 도구.

        RecommendationService에 위임해 추천 알고리즘을 캡슐화하고,
        에이전트 쪽에는 \"추천 결과 + 추천 이유\"만 넘겨준다.
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
                        "reason": r["reason"],
                    }
                    for r in recommendations
                ],
                "student_name": student_name,
            }
        except Exception as e:
            # 추천 로직 내부 예외가 UI 전체를 깨지 않도록, 에러 메시지만 담아 실패 응답으로 넘긴다.
            return {"success": False, "error": str(e)}
    
    async def _search_faq(self, keyword: str) -> dict:
        """
        FAQ/RAG 검색 도구.

        1순위로 pgvector 기반 벡터 검색을 시도하고, 결과가 없거나 에러가 나면
        기존 ILIKE 기반 검색으로 폴백한다.
        """

        if not keyword:
            return {"success": False, "data": [], "keyword": ""}

        # RAG 벡터 검색 + ILIKE 폴백
        try:
            # 순환 의존을 피하기 위해 함수 내부에서 import 한다.
            from app.services.ai.embedding_service import search_similar

            # pgvector 기반 RAG 검색으로 FAQ/지식 문서를 찾는다.
            rag_results = await search_similar(
                db=self.db,
                query=keyword,
                top_k=5,
                similarity_threshold=0.3,
                trace_id=self.trace_id,
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

            # 벡터 검색 결과가 없으면 폴백. 사용자는 여전히 FAQ 일부를 발견할 수 있다.
            return await self._search_faq_fallback(keyword)

        except Exception as e:
            # 임베딩/pgvector 에러 시에도 전체 FAQ 기능이 죽지 않도록 SQL ILIKE 폴백을 시도한다.
            print(f"[RAG] 벡터 검색 에러: {e}, ILIKE 폴백")
            # 벡터 검색 중 트랜잭션이 깨졌을 수 있으므로 롤백하여 세션을 정리한다.
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
        벡터 검색 실패/결과 없음 시 사용하는 기존 ILIKE 기반 FAQ 검색.

        RAG 인프라가 없거나 장애여도 최소한의 FAQ 검색 경험을 제공하기 위한 안전망이다.
        """

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

