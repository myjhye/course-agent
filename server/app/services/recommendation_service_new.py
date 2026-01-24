from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, not_, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Set, Dict
from app.models.lesson import Lesson, LessonStatus, SportType, Difficulty
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.lesson_interest import LessonView, LessonLike
from app.models.ai_log import AILog
from app.services.ai.llm_client import get_openai_client
import json
import time


DIFFICULTY_ORDER = ['beginner', 'elementary', 'intermediate', 'advanced']
ATTENDANCE_THRESHOLD = 70


class RecommendationService:

    @staticmethod
    async def get_categorized_recommendations(
        db: AsyncSession,
        student_name: str
    ) -> Dict[str, Optional[dict]]:
        """카테고리별 추천 (3가지 고정)"""

        start_time = time.time()

        # 1. 수강 이력 조회
        enrollment_result = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.lesson).selectinload(Lesson.instructor))
            .where(Enrollment.student_name == student_name)
            .order_by(desc(Enrollment.created_at))
        )
        enrollments = list(enrollment_result.scalars().all())

        # 2. 제외할 강습 ID
        enrolled_ids = set(e.lesson_id for e in enrollments)

        # 3. target_audience 추론
        inferred_target = None
        for e in enrollments:
            if e.lesson and e.lesson.target_audience:
                inferred_target = e.lesson.target_audience.value
                break

        # 4. 각 카테고리별 추천
        next_level = await RecommendationService._get_next_level(
            db, enrollments, enrolled_ids, inferred_target
        )

        new_sport = await RecommendationService._get_new_sport(
            db, enrollments, enrolled_ids, inferred_target
        )

        interest_based = await RecommendationService._get_interest_based(
            db, student_name, enrolled_ids, inferred_target
        )

        # 5. AI로 추천 이유 생성 (있는 것만)
        categories = {
            "next_level": next_level,
            "new_sport": new_sport,
            "interest_based": interest_based
        }

        for key, rec in categories.items():
            if rec:
                rec["reason"] = await RecommendationService._generate_single_reason(
                    student_name, enrollments, rec["lesson"], key, rec.get("base_lesson")
                )

        # 6. AI 로그
        latency_ms = (time.time() - start_time) * 1000
        ai_log = AILog(
            feature_type="recommendation",
            input_data={"student_name": student_name},
            output_data={
                "has_next_level": next_level is not None,
                "has_new_sport": new_sport is not None,
                "has_interest_based": interest_based is not None
            },
            latency_ms=latency_ms
        )
        db.add(ai_log)
        await db.commit()

        return categories

    @staticmethod
    async def _get_next_level(
        db: AsyncSession,
        enrollments: List[Enrollment],
        exclude_ids: Set[int],
        inferred_target: Optional[str]
    ) -> Optional[dict]:
        """다음 단계 추천 (1개)"""

        # 완료 OR 수강 중(70%+)
        eligible = [
            e for e in enrollments
            if e.lesson and (
                e.status == EnrollmentStatus.COMPLETED or
                (e.status == EnrollmentStatus.IN_PROGRESS and
                 e.attendance_rate and e.attendance_rate >= ATTENDANCE_THRESHOLD)
            )
        ]

        if not eligible:
            return None

        for enrollment in eligible:
            lesson = enrollment.lesson
            next_diff = RecommendationService._get_next_difficulty(lesson.difficulty.value)

            if not next_diff:
                continue

            result = await db.execute(
                select(Lesson)
                .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
                .where(
                    and_(
                        Lesson.sport_type == lesson.sport_type,
                        Lesson.difficulty == next_diff,
                        Lesson.target_audience == lesson.target_audience,
                        Lesson.status == LessonStatus.PUBLISHED,
                        not_(Lesson.id.in_(exclude_ids))
                    )
                )
                .limit(1)
            )

            next_lesson = result.scalar_one_or_none()
            if next_lesson:
                return {
                    "lesson": RecommendationService._lesson_to_dict(next_lesson),
                    "reason_type": "next_level",
                    "base_lesson": lesson
                }

        return None

    @staticmethod
    async def _get_new_sport(
        db: AsyncSession,
        enrollments: List[Enrollment],
        exclude_ids: Set[int],
        inferred_target: Optional[str]
    ) -> Optional[dict]:
        """새로운 종목 추천 (1개)"""

        if not inferred_target:
            return None

        done_sports = set(e.lesson.sport_type for e in enrollments if e.lesson)
        new_sports = [s for s in SportType if s not in done_sports]

        if not new_sports:
            return None

        result = await db.execute(
            select(Lesson)
            .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
            .where(
                and_(
                    Lesson.sport_type.in_(new_sports),
                    Lesson.difficulty == Difficulty.BEGINNER,
                    Lesson.target_audience == inferred_target,
                    Lesson.status == LessonStatus.PUBLISHED,
                    not_(Lesson.id.in_(exclude_ids))
                )
            )
            .limit(1)
        )

        lesson = result.scalar_one_or_none()
        if lesson:
            return {
                "lesson": RecommendationService._lesson_to_dict(lesson),
                "reason_type": "new_sport",
                "base_lesson": None
            }

        return None

    @staticmethod
    async def _get_interest_based(
        db: AsyncSession,
        student_name: str,
        exclude_ids: Set[int],
        inferred_target: Optional[str]
    ) -> Optional[dict]:
        """관심 기반 추천 (조회 + 찜)"""

        # 1. 찜한 강습 중 미등록 (우선)
        liked_result = await db.execute(
            select(Lesson)
            .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
            .join(LessonLike, LessonLike.lesson_id == Lesson.id)
            .where(
                and_(
                    LessonLike.student_name == student_name,
                    Lesson.status == LessonStatus.PUBLISHED,
                    not_(Lesson.id.in_(exclude_ids))
                )
            )
            .order_by(desc(LessonLike.created_at))
            .limit(1)
        )

        liked_lesson = liked_result.scalar_one_or_none()
        if liked_lesson:
            return {
                "lesson": RecommendationService._lesson_to_dict(liked_lesson),
                "reason_type": "interest_based",
                "interest_source": "like",
                "base_lesson": None
            }

        # 2. 자주 조회한 종목의 강습
        view_stats = await db.execute(
            select(
                Lesson.sport_type,
                func.count(LessonView.id).label('view_count')
            )
            .join(LessonView, LessonView.lesson_id == Lesson.id)
            .where(LessonView.student_name == student_name)
            .group_by(Lesson.sport_type)
            .order_by(desc('view_count'))
            .limit(1)
        )

        top_sport_row = view_stats.first()
        if top_sport_row:
            top_sport = top_sport_row[0]

            # 해당 종목의 미등록 강습
            result = await db.execute(
                select(Lesson)
                .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
                .where(
                    and_(
                        Lesson.sport_type == top_sport,
                        Lesson.status == LessonStatus.PUBLISHED,
                        not_(Lesson.id.in_(exclude_ids))
                    )
                )
                .order_by(Lesson.created_at.desc())
                .limit(1)
            )

            lesson = result.scalar_one_or_none()
            if lesson:
                return {
                    "lesson": RecommendationService._lesson_to_dict(lesson),
                    "reason_type": "interest_based",
                    "interest_source": "view",
                    "base_lesson": None
                }

        return None

    @staticmethod
    async def _generate_single_reason(
        student_name: str,
        enrollments: List[Enrollment],
        lesson: dict,
        reason_type: str,
        base_lesson=None
    ) -> str:
        """단일 추천 이유 생성"""

        client = get_openai_client()

        context = ""
        if reason_type == "next_level" and base_lesson:
            context = f"'{base_lesson.title}'을 잘 수강하고 있어서 다음 단계인 '{lesson['title']}'을 추천"
        elif reason_type == "new_sport":
            done = [e.lesson.sport_type.value for e in enrollments if e.lesson]
            context = f"기존에 {', '.join(done)} 경험이 있고, 새로운 종목 '{lesson['title']}'을 추천"
        elif reason_type == "interest_based":
            context = f"관심을 보인 종목 기반으로 '{lesson['title']}'을 추천"

        prompt = f"""수강생에게 강습을 추천하는 이유를 1문장으로 작성하세요.

상황: {context}

규칙:
- 친근하고 격려하는 톤
- 구체적인 이유 포함
- 20~40자 내외"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "스포츠 강습 추천 전문가"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"추천 이유 생성 실패: {e}")
            return RecommendationService._get_default_reason(reason_type, base_lesson)

    @staticmethod
    def _get_default_reason(reason_type: str, base_lesson=None) -> str:
        if reason_type == "next_level" and base_lesson:
            return f"{base_lesson.title}에서 배운 기초로 한 단계 더 성장해보세요!"
        elif reason_type == "new_sport":
            return "새로운 종목에 도전하며 다양한 운동의 즐거움을 경험해보세요!"
        elif reason_type == "interest_based":
            return "관심 있게 보셨던 강습이에요. 지금 시작해보세요!"
        return "추천 강습입니다."

    @staticmethod
    def _get_next_difficulty(current: str) -> Optional[str]:
        try:
            idx = DIFFICULTY_ORDER.index(current)
            if idx < len(DIFFULTY_ORDER) - 1:
                return DIFFICULTY_ORDER[idx + 1]
        except ValueError:
            pass
        return None

    @staticmethod
    def _lesson_to_dict(lesson: Lesson) -> dict:
        active_content = None
        if lesson.contents:
            active_content = next((c for c in lesson.contents if c.is_active), None)

        return {
            "id": lesson.id,
            "title": lesson.title,
            "sport_type": lesson.sport_type.value,
            "target_audience": lesson.target_audience.value,
            "difficulty": lesson.difficulty.value,
            "instructor_name": lesson.instructor.name if lesson.instructor else None,
            "thumbnail_url": active_content.thumbnail_url if active_content else None
        }

    # 기존 호환성 유지
    @staticmethod
    async def get_recommendations(db: AsyncSession, student_name: str, limit: int = 3) -> List[dict]:
        """기존 API 호환"""
        categories = await RecommendationService.get_categorized_recommendations(db, student_name)
        results = []
        for key in ["next_level", "new_sport", "interest_based"]:
            if categories.get(key):
                results.append(categories[key])
        return results[:limit]
