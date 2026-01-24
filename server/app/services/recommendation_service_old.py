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
    async def get_recommendations(
        db: AsyncSession,
        student_name: str,
        limit: int = 3
    ) -> List[dict]:
        """수강생에게 강습 추천"""
        
        start_time = time.time()
        
        # 1. 수강 이력 조회
        enrollment_result = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.lesson).selectinload(Lesson.instructor))
            .where(Enrollment.student_name == student_name)
        )
        enrollments = list(enrollment_result.scalars().all())
        
        # 2. target_audience 추론
        inferred_target = RecommendationService._infer_target_audience(enrollments)
        
        if not enrollments:
            # 수강 이력 없으면 "전체" 대상 또는 추론된 대상의 인기 강습 추천
            return await RecommendationService._get_popular_lessons(db, limit, inferred_target)
        
        # 3. 이미 수강 중/완료한 강습 ID (중복 방지)
        enrolled_lesson_ids = set(e.lesson_id for e in enrollments)
        
        # 4. 완료된 강습 분석
        completed = [e for e in enrollments if e.status == EnrollmentStatus.COMPLETED]
        
        # 5. 규칙 기반 추천 후보 생성 (target_audience 고려)
        candidates = await RecommendationService._get_candidates(
            db, enrollments, enrolled_lesson_ids, inferred_target
        )
        
        if not candidates:
            return await RecommendationService._get_popular_lessons(
                db, limit, inferred_target, enrolled_lesson_ids
            )
        
        # 5. 중복 제거 후 상위 N개
        unique_candidates = RecommendationService._remove_duplicates(candidates)
        selected = unique_candidates[:limit]
        
        # 6. AI로 추천 이유 생성
        recommendations = await RecommendationService._generate_reasons(
            db, student_name, enrollments, selected
        )
        
        # 7. AI 로그 저장
        latency_ms = (time.time() - start_time) * 1000
        ai_log = AILog(
            feature_type="recommendation",
            input_data={
                "student_name": student_name,
                "enrollment_count": len(enrollments),
                "completed_count": len(completed),
                "inferred_target": inferred_target
            },
            output_data={
                "recommended_count": len(recommendations),
                "lesson_ids": [r["lesson"]["id"] for r in recommendations]
            },
            latency_ms=latency_ms
        )
        db.add(ai_log)
        await db.commit()
        
        return recommendations
    
    @staticmethod
    def _infer_target_audience(enrollments: List[Enrollment]) -> Optional[str]:
        """수강 이력에서 target_audience 추론"""
        
        if not enrollments:
            return None  # 이력 없으면 None (전체 대상만 추천)
        
        # 가장 최근 수강의 target_audience 사용
        for enrollment in sorted(enrollments, key=lambda e: e.created_at, reverse=True):
            if enrollment.lesson and enrollment.lesson.target_audience:
                return enrollment.lesson.target_audience.value
        
        return None
    
    @staticmethod
    async def _get_candidates(
        db: AsyncSession,
        enrollments: List[Enrollment],
        exclude_ids: Set[int],
        inferred_target: Optional[str]
    ) -> List[dict]:
        """규칙 기반 추천 후보 생성 (target_audience 필터링)"""
        
        candidates = []
        seen_ids = set(exclude_ids)
        
        # 다음 단계 추천 대상: 완료 OR (수강 중 + 출석률 70%+)
        next_level_eligible = [
            e for e in enrollments
            if e.status == EnrollmentStatus.COMPLETED or
               (e.status == EnrollmentStatus.IN_PROGRESS and
                e.attendance_rate and e.attendance_rate >= ATTENDANCE_THRESHOLD)
        ]

        # 1. 같은 종목의 다음 난이도 (우선순위 높음)
        for enrollment in next_level_eligible:
            lesson = enrollment.lesson
            if not lesson:
                continue
            
            next_difficulty = RecommendationService._get_next_difficulty(lesson.difficulty.value)
            if next_difficulty:
                result = await db.execute(
                    select(Lesson)
                    .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
                    .where(
                        and_(
                            Lesson.sport_type == lesson.sport_type,
                            Lesson.difficulty == next_difficulty,
                            Lesson.target_audience == lesson.target_audience,  # 같은 대상
                            Lesson.status == LessonStatus.PUBLISHED,
                            not_(Lesson.id.in_(seen_ids))
                        )
                    )
                )
                for l in result.scalars().all():
                    if l.id not in seen_ids:
                        candidates.append({
                            "lesson": l,
                            "reason_type": "next_level",
                            "base_lesson": lesson,
                            "priority": 1
                        })
                        seen_ids.add(l.id)
        
        # 2. 다른 종목 입문 (같은 target_audience)
        completed_sports = set(e.lesson.sport_type for e in completed if e.lesson)
        all_sports = [s for s in SportType if s not in completed_sports]
        
        if all_sports and inferred_target:
            result = await db.execute(
                select(Lesson)
                .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
                .where(
                    and_(
                        Lesson.sport_type.in_(all_sports),
                        Lesson.difficulty == Difficulty.BEGINNER,
                        Lesson.target_audience == inferred_target,  # 같은 대상만
                        Lesson.status == LessonStatus.PUBLISHED,
                        not_(Lesson.id.in_(seen_ids))
                    )
                )
                .limit(3)
            )
            for l in result.scalars().all():
                if l.id not in seen_ids:
                    candidates.append({
                        "lesson": l,
                        "reason_type": "new_sport",
                        "base_lesson": None,
                        "priority": 2
                    })
                    seen_ids.add(l.id)
        
        # 3. 같은 target_audience의 다른 강습 (보조)
        if len(candidates) < 3 and inferred_target:
            result = await db.execute(
                select(Lesson)
                .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
                .where(
                    and_(
                        Lesson.target_audience == inferred_target,
                        Lesson.status == LessonStatus.PUBLISHED,
                        not_(Lesson.id.in_(seen_ids))
                    )
                )
                .limit(3 - len(candidates))
            )
            for l in result.scalars().all():
                if l.id not in seen_ids:
                    candidates.append({
                        "lesson": l,
                        "reason_type": "same_audience",
                        "base_lesson": None,
                        "priority": 3
                    })
                    seen_ids.add(l.id)
        
        # 우선순위 정렬
        candidates.sort(key=lambda x: x["priority"])
        
        return candidates
    
    @staticmethod
    def _get_next_difficulty(current: str) -> Optional[str]:
        """다음 난이도 반환"""
        try:
            idx = DIFFICULTY_ORDER.index(current)
            if idx < len(DIFFICULTY_ORDER) - 1:
                return DIFFICULTY_ORDER[idx + 1]
        except ValueError:
            pass
        return None
    
    @staticmethod
    async def _get_popular_lessons(
        db: AsyncSession,
        limit: int,
        target_audience: Optional[str] = None,
        exclude_ids: Set[int] = None
    ) -> List[dict]:
        """인기 강습 반환 (수강 이력 없을 때)"""
        
        query = select(Lesson).options(
            selectinload(Lesson.contents),
            selectinload(Lesson.instructor)
        ).where(Lesson.status == LessonStatus.PUBLISHED)
        
        # target_audience 필터
        if target_audience:
            # 추론된 대상 또는 "전체" 대상
            query = query.where(
                (Lesson.target_audience == target_audience) | 
                (Lesson.target_audience == TargetAudience.ALL)
            )
        else:
            # 이력 없으면 "전체" 대상만
            query = query.where(Lesson.target_audience == TargetAudience.ALL)
        
        if exclude_ids:
            query = query.where(not_(Lesson.id.in_(exclude_ids)))
        
        # 입문 난이도 우선
        query = query.order_by(
            Lesson.difficulty == Difficulty.BEGINNER,  # 입문 우선
            Lesson.created_at.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        lessons = list(result.scalars().all())
        
        if not lessons:
            # 전체 대상도 없으면 그냥 입문 강습 아무거나
            fallback_query = select(Lesson).options(
                selectinload(Lesson.contents),
                selectinload(Lesson.instructor)
            ).where(
                and_(
                    Lesson.status == LessonStatus.PUBLISHED,
                    Lesson.difficulty == Difficulty.BEGINNER
                )
            ).limit(limit)
            
            result = await db.execute(fallback_query)
            lessons = list(result.scalars().all())
        
        return [
            {
                "lesson": RecommendationService._lesson_to_dict(l),
                "reason": RecommendationService._get_popular_reason(l, target_audience),
                "reason_type": "popular"
            }
            for l in lessons
        ]
    
    @staticmethod
    def _get_popular_reason(lesson: Lesson, target_audience: Optional[str]) -> str:
        """인기 강습 추천 이유"""
        sport_name = {
            "swimming": "수영",
            "tennis": "테니스", 
            "golf": "골프",
            "fitness": "피트니스",
            "yoga": "요가",
            "pilates": "필라테스"
        }.get(lesson.sport_type.value, lesson.sport_type.value)
        
        if target_audience:
            return f"인기 있는 {sport_name} 입문 강습입니다. 처음 시작하시기 좋아요!"
        else:
            return f"누구나 쉽게 시작할 수 있는 {sport_name} 강습입니다!"
    
    @staticmethod
    async def _generate_reasons(
        db: AsyncSession,
        student_name: str,
        enrollments: List[Enrollment],
        candidates: List[dict]
    ) -> List[dict]:
        """AI로 추천 이유 생성"""
        
        client = get_openai_client()
        
        # 수강 이력 텍스트
        history_lines = []
        for e in enrollments:
            if e.lesson:
                status_label = {
                    "enrolled": "수강 신청",
                    "in_progress": f"수강 중 (출석률 {e.attendance_rate or 0}%)",
                    "completed": "수강 완료",
                    "cancelled": "취소됨"
                }.get(e.status.value, e.status.value)
                history_lines.append(f"- {e.lesson.title} ({e.lesson.sport_type.value}) - {status_label}")
        history_text = "\n".join(history_lines)
        
        # 추천 강습 텍스트
        rec_lines = []
        for i, c in enumerate(candidates):
            base_info = ""
            if c["reason_type"] == "next_level" and c.get("base_lesson"):
                base_info = f" (기반: {c['base_lesson'].title})"
            rec_lines.append(
                f"{i+1}. {c['lesson'].title} ({c['lesson'].sport_type.value}, {c['lesson'].difficulty.value}) "
                f"- 타입: {c['reason_type']}{base_info}"
            )
        recommendations_text = "\n".join(rec_lines)
        
        prompt = f"""다음 수강생의 이력을 바탕으로 각 추천 강습에 대한 추천 이유를 작성해주세요.

## 수강생: {student_name}

## 수강 이력
{history_text or "(없음)"}

## 추천 강습
{recommendations_text}

## 추천 타입별 작성 가이드
- next_level: 이전 강습에서 배운 내용을 언급하며 다음 단계로의 자연스러운 성장 강조
- new_sport: 기존 운동 경험과의 시너지, 새로운 도전의 즐거움 강조
- same_audience: 비슷한 수준의 다른 강습 추천, 다양한 경험 강조

## 요청사항
각 강습에 대해 1-2문장으로 친근하고 격려하는 톤으로 추천 이유를 작성해주세요.
수강 이력의 대상(성인/어린이/시니어)에 맞는 톤으로 작성하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "reasons": [
    "첫 번째 강습 추천 이유",
    "두 번째 강습 추천 이유",
    "세 번째 강습 추천 이유"
  ]
}}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 스포츠 강습 플랫폼의 추천 전문가입니다. 수강생의 이력과 대상에 맞는 친근하고 격려하는 톤으로 추천 이유를 작성합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            result_text = response.choices[0].message.content
            
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(result_text[start:end])
                reasons = data.get("reasons", [])
            else:
                reasons = []
                
        except Exception as e:
            print(f"AI 추천 이유 생성 실패: {e}")
            reasons = []
        
        # 결과 조합
        results = []
        for i, candidate in enumerate(candidates):
            reason = reasons[i] if i < len(reasons) else RecommendationService._get_default_reason(candidate['reason_type'], candidate.get('base_lesson'))
            results.append({
                "lesson": RecommendationService._lesson_to_dict(candidate['lesson']),
                "reason": reason,
                "reason_type": candidate['reason_type']
            })
        
        return results
    
    @staticmethod
    def _get_default_reason(reason_type: str, base_lesson: Optional[Lesson] = None) -> str:
        """기본 추천 이유"""
        if reason_type == "next_level" and base_lesson:
            return f"{base_lesson.title}을 잘 마치셨으니, 다음 단계로 도전해보세요!"
        elif reason_type == "new_sport":
            return "새로운 종목에 도전해보세요! 다양한 운동 경험이 건강에 좋습니다."
        elif reason_type == "same_audience":
            return "비슷한 수준의 다른 강습도 함께 들어보시는 건 어떨까요?"
        else:
            return "이 강습을 추천드립니다."
    
    @staticmethod
    def _lesson_to_dict(lesson: Lesson) -> dict:
        """Lesson 객체를 dict로 변환"""
        active_content = next((c for c in lesson.contents if c.is_active), None) if lesson.contents else None
        
        return {
            "id": lesson.id,
            "title": lesson.title,
            "sport_type": lesson.sport_type.value,
            "target_audience": lesson.target_audience.value,
            "difficulty": lesson.difficulty.value,
            "instructor_name": lesson.instructor.name if lesson.instructor else None,
            "thumbnail_url": active_content.thumbnail_url if active_content else None
        }

