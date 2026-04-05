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
    """
    수강생별 강습 추천을 세 카테고리로 나눠 제공한다.

    카테고리별 근거 데이터:
    - next_level     : 완료하거나 출석률 70% 이상인 강습의 다음 난이도를 추천한다.
    - new_sport      : 아직 수강하지 않은 종목의 입문 강습을 추천한다.
    - interest_based : 찜한 강습을 우선하고, 없으면 조회 횟수가 많은 종목을 추천한다.

    후보 선정은 규칙 기반으로 하고, 추천 이유(reason)만 GPT로 생성한다.
    """

    @staticmethod
    async def get_categorized_recommendations(
        db: AsyncSession,
        student_name: str
    ) -> Dict[str, Optional[dict]]:
        """
        세 카테고리(next_level, new_sport, interest_based) 추천을 각 1건씩 반환한다.

        카테고리별로 독립적으로 후보를 고르기 때문에 한 카테고리가 비어도 나머지에 영향을 주지 않는다.

        후보가 없는 카테고리는 None으로 두고, 이유 생성과 로그는 채워진 항목만 처리한다.
        """

        start_time = time.time()

        # ── 1. 수강 이력 조회 ──
        # 최신순으로 정렬해 같은 종목이 여러 번 있을 때 가장 최근 수강을 기준으로 삼는다.
        enrollment_result = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.lesson).selectinload(Lesson.instructor))
            .where(Enrollment.student_name == student_name)
            .order_by(desc(Enrollment.created_at))
        )
        enrollments = list(enrollment_result.scalars().all())

        # ── 2. 추천 제외 ID 수집 ──
        # 이미 수강·완료한 강습을 다시 추천하면 중복 신청과 혼란이 발생한다.
        enrolled_ids = set(e.lesson_id for e in enrollments)

        # ── 3. 대상 연령대 추론 ──
        # 프로필에 연령대가 없을 때 과거 수강의 target_audience로 신규 강습 대상을 맞춘다.
        inferred_target = None
        for e in enrollments:
            if e.lesson and e.lesson.target_audience:
                inferred_target = e.lesson.target_audience.value
                break

        # ── 4. 카테고리별 후보 선정 ──
        # 독립적으로 실행해 한 카테고리가 비어도 나머지에 영향을 주지 않는다.
        next_level = await RecommendationService._get_next_level(
            db, enrollments, enrolled_ids, inferred_target
        )

        new_sport = await RecommendationService._get_new_sport(
            db, enrollments, enrolled_ids, inferred_target
        )

        interest_based = await RecommendationService._get_interest_based(
            db, student_name, enrolled_ids, inferred_target
        )

        # ── 5. 추천 이유 생성 ──
        # 후보 선정은 규칙 기반, 맥락이 달라지는 이유 문구만 GPT로 생성한다.
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

        # ── 6. AI 로그 저장 ──
        # 어떤 카테고리가 채워졌는지 기록해 추천 품질을 추후 분석한다.
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
        """
        같은 종목·대상에서 난이도 한 단계 위 강습을 추천한다.

        완료했거나 출석률 70% 이상인 수강만 후보로 삼는다.
        기초가 부족한 상태에서 상위 난이도를 추천하면 이탈과 부상 리스크가 커지기 때문이다.
        후보가 없거나 다음 난이도 강습이 없으면 None을 반환한다.
        """

        # ── 1. 다음 단계 수강 필터링 ──
        # 완료 또는 출석률 70% 이상인 수강만 기초가 쌓였다고 판단해 후보로 삼는다.
        eligible = [
            e for e in enrollments
            if e.lesson and (
                e.status == EnrollmentStatus.COMPLETED or
                (e.status == EnrollmentStatus.IN_PROGRESS and
                 e.attendance_rate and e.attendance_rate >= ATTENDANCE_THRESHOLD)  # 진행 중은 70% 미만이면 제외한다.
            )
        ]

        if not eligible:
            return None

        # ── 2. 후보별 다음 난이도 강습 탐색 ──
        # 최근 수강부터 탐색하고, 조건에 맞는 강습이 나오면 바로 반환한다.
        for enrollment in eligible:
            lesson = enrollment.lesson
            next_diff = RecommendationService._get_next_difficulty(lesson.difficulty.value)

            # 이미 최고 난이도(advanced)면 다음 단계가 없으므로 건너뛴다.
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
                # 카테고리당 1건만 반환하므로 첫 매칭에서 바로 멈춘다.
                .limit(1)
            )

            next_lesson = result.scalar_one_or_none()
            if next_lesson:
                # ── 3. 매칭 점수 계산 ──
                # 출석률과 완료 여부를 합산해 점수를 산정한다.
                # 출석률 100%라도 숙련도를 단정할 수 없어 0.9를 곱해 보정한다.
                # 99 상한은 "완벽한 적합"을 수치로 표현하지 않기 위함이다.
                # 출석 기록이 없으면 70을 쓴다. ATTENDANCE_THRESHOLD와 맞춰 보수적으로 잡는다.
                base_score = enrollment.attendance_rate or 70
                completion_bonus = 10 if enrollment.status == EnrollmentStatus.COMPLETED else 0
                match_score = min(int(base_score * 0.9 + completion_bonus), 99)

                return {
                    "lesson": RecommendationService._lesson_to_dict(next_lesson),
                    "reason_type": "next_level",
                    "base_lesson_title": lesson.title,
                    "match_score": match_score
                }

        # 탐색을 끝냈는데 적합한 다음 단계 강습이 없다.
        return None

    @staticmethod
    async def _get_new_sport(
        db: AsyncSession,
        enrollments: List[Enrollment],
        exclude_ids: Set[int],
        inferred_target: Optional[str]
    ) -> Optional[dict]:
        """
        아직 수강하지 않은 종목의 입문 강습을 추천한다.

        target_audience를 추론하지 못한 경우 None을 반환한다.
        대상을 모르면 어린이에게 성인용 강습을 추천하는 등의 오류가 생길 수 있기 때문이다.
        새 종목은 항상 입문(BEGINNER)으로 고정한다.
        미수강 종목이 없거나 입문 강습이 없으면 None을 반환한다.
        """

        # ── 1. 대상 연령대 확인 ──
        # 대상을 모르면 잘못된 연령대 강습을 추천할 수 있어 바로 포기한다.
        if not inferred_target:
            return None

        # ── 2. 미수강 종목 목록 추출 ──
        # 기존에 경험한 종목을 제외하고 새로 도전할 종목만 후보로 남긴다.
        done_sports = set(e.lesson.sport_type for e in enrollments if e.lesson)
        new_sports = [s for s in SportType if s not in done_sports]

        if not new_sports:
            return None

        # ── 3. 입문 강습 조회 ──
        # 새 종목은 항상 입문부터 시작하도록 BEGINNER로 고정해 조회한다.
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
            .limit(1)  # 카테고리당 1건만 반환하므로 첫 매칭에서 바로 멈춘다.
        )

        lesson = result.scalar_one_or_none()
        if lesson:
            # ── 4. 매칭 점수 계산 ──
            # 완료 수강이 많을수록 새 종목 도전 가능성이 높다고 보아 건당 5점씩 더한다.
            completed_count = len([e for e in enrollments if e.status == EnrollmentStatus.COMPLETED])
            match_score = min(70 + completed_count * 5, 90)  # 과장을 막기 위해 90에서 캡한다.

            return {
                "lesson": RecommendationService._lesson_to_dict(lesson),
                "reason_type": "new_sport",
                "base_lesson": None,
                "match_score": match_score
            }

        # 입문 강습 후보가 없다.
        return None

    @staticmethod
    async def _get_interest_based(
        db: AsyncSession,
        student_name: str,
        exclude_ids: Set[int],
        inferred_target: Optional[str]
    ) -> Optional[dict]:
        """
        찜하거나 자주 조회한 강습을 추천한다.

        찜을 조회보다 우선한다.
        찜은 명시적 관심 표현이고, 조회는 약한 신호이기 때문이다.
        찜한 강습이 없으면 조회 횟수가 가장 많은 종목의 강습을 추천한다.
        둘 다 없으면 None을 반환한다.
        """

        # ── 1. 찜한 강습 조회 ──
        # 찜은 명시적 관심 표현이라 조회보다 우선해 먼저 확인한다.
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
            .limit(1)  # 카테고리당 1건만 반환하므로 첫 매칭에서 바로 멈춘다.
        )

        liked_lesson = liked_result.scalar_one_or_none()
        if liked_lesson:
            # 찜이 있으면 바로 반환한다. 조회 기반(80)보다 5점 높게 잡아 명시적 관심을 반영한다.
            return {
                "lesson": RecommendationService._lesson_to_dict(liked_lesson),
                "reason_type": "interest_based",
                "interest_source": "like",
                "base_lesson": None,
                "match_score": 85,
            }

        # ── 2. 조회 기록 기반 종목 탐색 ──
        # 찜이 없을 때 조회 횟수가 가장 많은 종목으로 관심을 추론한다.
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
            view_count = top_sport_row[1]

            # ── 3. 해당 종목 강습 조회 ──
            # 가장 최근에 등록된 강습을 우선해 신규 강습이 노출되도록 한다.
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
                .limit(1)  # 카테고리당 1건만 반환하므로 첫 매칭에서 바로 멈춘다.
            )

            lesson = result.scalar_one_or_none()
            if lesson:
                # ── 4. 매칭 점수 계산 ──
                # 클릭은 찜보다 관심 강도가 약하므로 찜(85)보다 낮은 80을 상한으로 캡한다.
                match_score = min(50 + view_count * 10, 80)

                return {
                    "lesson": RecommendationService._lesson_to_dict(lesson),
                    "reason_type": "interest_based",
                    "interest_source": "view",
                    "base_lesson": None,
                    "match_score": match_score
                }

        # 찜과 조회로는 후보를 만들 수 없다.
        return None

    @staticmethod
    async def _generate_single_reason(
        student_name: str,
        enrollments: List[Enrollment],
        lesson: dict,
        reason_type: str,
        base_lesson=None
    ) -> str:
        """
        추천 카테고리별 이유를 GPT로 생성한다.

        카테고리가 같아도 수강 이력과 강습명이 달라 맥락이 매번 달라지기 때문에,
        고정 문구 대신 GPT로 개인화된 한 문장을 만든다.
        실패 시 _get_default_reason()으로 폴백해 reason 칸이 비지 않게 한다.
        """

        client = get_openai_client()

        # ── 1. 카테고리별 맥락 문장 구성 ──
        # reason_type에 따라 GPT에 넘길 상황 설명을 다르게 구성한다.
        context = ""
        if reason_type == "next_level" and base_lesson:
            title = base_lesson.get("title") if isinstance(base_lesson, dict) else getattr(base_lesson, 'title', '이전 강습')
            context = f"'{title}'을 잘 수강하고 있어서 다음 단계인 '{lesson['title']}'을 추천"
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

        # ── 2. 맥락 문장을 프롬프트에 넣어 GPT로 개인화된 한 문장을 생성한다. ──
        try:
            response = await client.chat.completions.create(
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
            # ── 3. 실패 시 고정 문구 폴백 ──
            # 이유 생성 실패로 추천 카드 전체를 버리면 UX가 나빠지므로 고정 문구로 대체한다.
            print(f"추천 이유 생성 실패: {e}")
            return RecommendationService._get_default_reason(reason_type, base_lesson)

    @staticmethod
    def _get_default_reason(reason_type: str, base_lesson=None) -> str:
        """
        GPT 생성 실패 시 카테고리별 고정 문구를 반환한다.

        이유 생성 실패로 추천 카드 전체를 버리면 UX가 나빠지기 때문에 폴백으로 사용한다.

        알 수 없는 reason_type이면 일반 문구를 반환한다.
        """
        if reason_type == "next_level" and base_lesson:
            title = base_lesson.get("title") if isinstance(base_lesson, dict) else getattr(base_lesson, 'title', '이전 강습')
            return f"{title}에서 배운 기초로 한 단계 더 성장해보세요!"
        elif reason_type == "new_sport":
            return "새로운 종목에 도전하며 다양한 운동의 즐거움을 경험해보세요!"
        elif reason_type == "interest_based":
            return "관심 있게 보셨던 강습이에요. 지금 시작해보세요!"
        return "추천 강습입니다."

    @staticmethod
    def _get_next_difficulty(current: str) -> Optional[str]:
        """
        현재 난이도의 다음 단계를 반환한다.

        DIFFICULTY_ORDER 기준으로 한 단계 위를 찾는다.

        가장 높은 난이도(advanced)이거나 목록에 없는 값이면 None을 반환한다.
        """
        try:
            idx = DIFFICULTY_ORDER.index(current)
            if idx < len(DIFFICULTY_ORDER) - 1:
                return DIFFICULTY_ORDER[idx + 1]
        except ValueError:
            pass
        return None

    @staticmethod
    def _lesson_to_dict(lesson: Lesson) -> dict:
        """
        Lesson 모델을 추천 응답용 dict로 변환한다.

        여러 콘텐츠 버전 중 is_active인 것만 썸네일에 사용한다.

        활성 콘텐츠가 없으면 thumbnail_url은 None이 된다.
        """
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

    @staticmethod
    async def get_recommendations(db: AsyncSession, student_name: str, limit: int = 3) -> List[dict]:
        """
        기존 호출부(ToolExecutor)와의 하위 호환용 래퍼다.

        get_categorized_recommendations() 결과를 리스트로 변환해 반환한다.

        채워진 카테고리만 순서대로 모은 뒤 limit개로 잘라 반환한다.
        신규 코드는 get_categorized_recommendations()를 직접 사용한다.
        """
        categories = await RecommendationService.get_categorized_recommendations(db, student_name)
        results = []
        for key in ["next_level", "new_sport", "interest_based"]:
            if categories.get(key):
                results.append(categories[key])
        return results[:limit]
