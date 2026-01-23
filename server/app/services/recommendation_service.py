from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, not_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.lesson import Lesson, LessonStatus, SportType, Difficulty
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.ai_log import AILog
from app.services.ai.llm_client import generate_text
import json
import time


# 난이도 순서
DIFFICULTY_ORDER = ['beginner', 'elementary', 'intermediate', 'advanced']


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
            .options(selectinload(Enrollment.lesson))
            .where(Enrollment.student_name == student_name)
        )
        enrollments = list(enrollment_result.scalars().all())
        
        if not enrollments:
            # 수강 이력 없으면 인기 강습 추천
            return await RecommendationService._get_popular_lessons(db, limit)
        
        # 2. 수강 중/완료된 강습 ID 목록
        enrolled_lesson_ids = [e.lesson_id for e in enrollments]
        
        # 3. 완료된 강습 분석
        completed = [e for e in enrollments if e.status == EnrollmentStatus.COMPLETED]
        in_progress = [e for e in enrollments if e.status in [EnrollmentStatus.ENROLLED, EnrollmentStatus.IN_PROGRESS]]
        
        # 4. 규칙 기반 추천 후보 생성
        candidates = await RecommendationService._get_candidates(
            db, enrollments, enrolled_lesson_ids
        )
        
        if not candidates:
            return await RecommendationService._get_popular_lessons(db, limit, enrolled_lesson_ids)
        
        # 5. 상위 N개 선택
        selected = candidates[:limit]
        
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
                "completed_count": len(completed)
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
    async def _get_candidates(
        db: AsyncSession,
        enrollments: List[Enrollment],
        exclude_ids: List[int]
    ) -> List[dict]:
        """규칙 기반 추천 후보 생성"""
        
        candidates = []
        seen_ids = set(exclude_ids)
        
        # 완료된 강습 기준으로 다음 단계 찾기
        completed = [e for e in enrollments if e.status == EnrollmentStatus.COMPLETED]
        
        for enrollment in completed:
            lesson = enrollment.lesson
            if not lesson:
                continue
            
            # 같은 종목의 다음 난이도
            next_difficulty = RecommendationService._get_next_difficulty(lesson.difficulty.value)
            if next_difficulty:
                result = await db.execute(
                    select(Lesson)
                    .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
                    .where(
                        and_(
                            Lesson.sport_type == lesson.sport_type,
                            Lesson.difficulty == next_difficulty,
                            Lesson.status == LessonStatus.PUBLISHED,
                            Lesson.target_audience == lesson.target_audience,
                            not_(Lesson.id.in_(seen_ids))
                        )
                    )
                )
                for l in result.scalars().all():
                    if l.id not in seen_ids:
                        candidates.append({"lesson": l, "reason_type": "next_level", "base_lesson": lesson})
                        seen_ids.add(l.id)
        
        # 다른 종목 입문 추천
        completed_sports = set(e.lesson.sport_type for e in completed if e.lesson)
        all_sports = [s for s in SportType if s not in completed_sports]
        
        if all_sports:
            result = await db.execute(
                select(Lesson)
                .options(selectinload(Lesson.contents), selectinload(Lesson.instructor))
                .where(
                    and_(
                        Lesson.sport_type.in_(all_sports),
                        Lesson.difficulty == Difficulty.BEGINNER,
                        Lesson.status == LessonStatus.PUBLISHED,
                        not_(Lesson.id.in_(seen_ids))
                    )
                )
                .limit(3)
            )
            for l in result.scalars().all():
                if l.id not in seen_ids:
                    candidates.append({"lesson": l, "reason_type": "new_sport", "base_lesson": None})
                    seen_ids.add(l.id)
        
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
        exclude_ids: List[int] = None
    ) -> List[dict]:
        """인기 강습 반환 (수강 이력 없을 때)"""
        
        query = select(Lesson).options(
            selectinload(Lesson.contents),
            selectinload(Lesson.instructor)
        ).where(Lesson.status == LessonStatus.PUBLISHED)
        
        if exclude_ids:
            query = query.where(not_(Lesson.id.in_(exclude_ids)))
        
        query = query.limit(limit)
        result = await db.execute(query)
        lessons = list(result.scalars().all())
        
        return [
            {
                "lesson": RecommendationService._lesson_to_dict(l),
                "reason": "인기 있는 입문 강습입니다. 새로운 운동을 시작해보세요!",
                "reason_type": "popular"
            }
            for l in lessons
        ]
    
    @staticmethod
    async def _generate_reasons(
        db: AsyncSession,
        student_name: str,
        enrollments: List[Enrollment],
        candidates: List[dict]
    ) -> List[dict]:
        """AI로 추천 이유 생성"""
        
        # 수강 이력 텍스트
        history_text = "\n".join([
            f"- {e.lesson.title} ({e.lesson.sport_type.value}, {e.lesson.difficulty.value}) - {e.status.value}"
            for e in enrollments if e.lesson
        ])
        
        # 추천 강습 텍스트
        recommendations_text = "\n".join([
            f"{i+1}. {c['lesson'].title} ({c['lesson'].sport_type.value}, {c['lesson'].difficulty.value}) - 타입: {c['reason_type']}"
            for i, c in enumerate(candidates)
        ])
        
        prompt = f"""다음 수강생의 이력을 바탕으로 각 추천 강습에 대한 추천 이유를 작성해주세요.

## 수강생: {student_name}

## 수강 이력
{history_text}

## 추천 강습
{recommendations_text}

## 요청사항
각 강습에 대해 1-2문장으로 친근하고 격려하는 톤으로 추천 이유를 작성해주세요.
- next_level: 다음 단계로 자연스러운 성장 강조
- new_sport: 새로운 도전, 기존 운동과의 시너지 강조

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "reasons": [
    "첫 번째 강습 추천 이유",
    "두 번째 강습 추천 이유",
    "세 번째 강습 추천 이유"
  ]
}}"""

        try:
            response_text = await generate_text(prompt)
            
            # JSON 파싱
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(response_text[start:end])
                reasons = data.get("reasons", [])
            else:
                reasons = []
                
        except Exception as e:
            print(f"AI 추천 이유 생성 실패: {e}")
            reasons = []
        
        # 결과 조합
        results = []
        for i, candidate in enumerate(candidates):
            reason = reasons[i] if i < len(reasons) else RecommendationService._get_default_reason(candidate['reason_type'])
            results.append({
                "lesson": RecommendationService._lesson_to_dict(candidate['lesson']),
                "reason": reason,
                "reason_type": candidate['reason_type']
            })
        
        return results
    
    @staticmethod
    def _get_default_reason(reason_type: str) -> str:
        """기본 추천 이유"""
        if reason_type == "next_level":
            return "이전 단계를 성공적으로 마치셨으니, 다음 단계로 도전해보세요!"
        elif reason_type == "new_sport":
            return "새로운 종목에 도전해보세요! 다양한 운동 경험이 건강에 좋습니다."
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

