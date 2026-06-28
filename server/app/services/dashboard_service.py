"""
관리자 대시보드에 필요한 통계를 DB에서 집계해 반환한다.

강습·수강·강사·AI 사용 현황을 하나의 응답으로 묶어 대시보드 카드에 표시한다.
기간 필터는 수강·AI 통계에만 적용한다. 강습·강사는 전체 누적이 의미 있기 때문이다.

함수:
- get_dashboard_stats()   : 아래 4개 집계를 모아 한 번에 반환하는 진입점
- _get_lesson_stats()     : 강습 전체 수, 발행/초안/보관 상태별, 종목별 건수
- _get_enrollment_stats() : 수강 신규 등록 수, 수료 수, 상태별 건수, 평균 출석률
- _get_instructor_stats() : 강사 전체 인원 수
- _get_ai_stats()         : AI 호출 수, 총 토큰, 평균 응답 시간, 수정률
- get_ai_logs()           : AI 로그 목록 최신순 조회 (기능별 필터, 페이지네이션)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime
from typing import Optional
from app.models.lesson import Lesson, LessonStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.ai_log import AILog
from app.models.instructor import Instructor


class DashboardService:
    @staticmethod
    async def get_dashboard_stats(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """
        대시보드 전체 통계를 한 번에 반환한다.
        start_date/end_date 없으면 이번 달 1일 ~ 오늘을 기본값으로 쓴다.
        기간 필터는 수강·AI 통계에만 전달된다. 강습·강사는 전체 누적을 집계한다.
        """
        if not start_date:
            today = datetime.now()
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()

        lesson_stats = await DashboardService._get_lesson_stats(db)
        enrollment_stats = await DashboardService._get_enrollment_stats(db, start_date, end_date)
        instructor_stats = await DashboardService._get_instructor_stats(db)
        ai_stats = await DashboardService._get_ai_stats(db, start_date, end_date)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "lessons": lesson_stats,
            "enrollments": enrollment_stats,
            "instructors": instructor_stats,
            "ai_usage": ai_stats
        }
    
    @staticmethod
    async def _get_lesson_stats(db: AsyncSession) -> dict:
        """
        강습 현황 통계. 전체 수, 상태별(발행/초안/보관), 종목별 분포를 반환한다.
        강습은 누적 재고 개념이라 기간 필터 없이 전체를 집계한다.
        """
        total_result = await db.execute(select(func.count(Lesson.id)))
        total = total_result.scalar() or 0
        
        status_result = await db.execute(
            select(Lesson.status, func.count(Lesson.id))
            .group_by(Lesson.status)
        )
        status_counts = {row[0].value: row[1] for row in status_result.all()}
        
        sport_result = await db.execute(
            select(Lesson.sport_type, func.count(Lesson.id))
            .group_by(Lesson.sport_type)
        )
        sport_counts = {row[0].value: row[1] for row in sport_result.all()}
        
        return {
            "total": total,
            "published": status_counts.get("published", 0),
            "draft": status_counts.get("draft", 0),
            "archived": status_counts.get("archived", 0),
            "by_sport": sport_counts
        }
    
    @staticmethod
    async def _get_enrollment_stats(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """
        수강 현황 통계.
        신규 등록·기간 내 수료는 start~end 기간으로 필터하고,
        전체 수·상태별·평균 출석률은 기간 필터 없이 전체를 집계한다.
        """
        total_result = await db.execute(select(func.count(Enrollment.id)))
        total = total_result.scalar() or 0
        
        # 기간 내 신규 등록 수
        new_result = await db.execute(
            select(func.count(Enrollment.id))
            .where(
                and_(
                    Enrollment.created_at >= start_date,
                    Enrollment.created_at <= end_date
                )
            )
        )
        new_count = new_result.scalar() or 0
        
        status_result = await db.execute(
            select(Enrollment.status, func.count(Enrollment.id))
            .group_by(Enrollment.status)
        )
        status_counts = {row[0].value: row[1] for row in status_result.all()}
        
        avg_result = await db.execute(
            select(func.avg(Enrollment.attendance_rate))
            .where(Enrollment.attendance_rate.isnot(None))
        )
        avg_attendance = avg_result.scalar() or 0
        
        # 기간 내 수료 수
        completed_result = await db.execute(
            select(func.count(Enrollment.id))
            .where(
                and_(
                    Enrollment.status == EnrollmentStatus.COMPLETED,
                    Enrollment.completion_date >= start_date,
                    Enrollment.completion_date <= end_date
                )
            )
        )
        completed_in_period = completed_result.scalar() or 0
        
        return {
            "total": total,
            "new_in_period": new_count,
            "completed_in_period": completed_in_period,
            "enrolled": status_counts.get("enrolled", 0),
            "in_progress": status_counts.get("in_progress", 0),
            "completed": status_counts.get("completed", 0),
            "cancelled": status_counts.get("cancelled", 0),
            "avg_attendance_rate": round(avg_attendance, 1)
        }
    
    @staticmethod
    async def _get_instructor_stats(db: AsyncSession) -> dict:
        """
        강사 현황 통계. 전체 강사 수를 반환한다.
        강사 수는 누적 인원이라 기간 필터 없이 전체를 집계한다.
        """
        total_result = await db.execute(select(func.count(Instructor.id)))
        total = total_result.scalar() or 0
        
        return {"total": total}
    
    @staticmethod
    async def _get_ai_stats(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """
        기간 내 AI 사용 현황. 기능별 호출 수, 총 토큰, 평균 응답 시간, 수정률을 반환한다.
        수정률(edit_rate)이 높으면 AI 출력 품질 점검이 필요하다는 신호다.
        edit_rate = 기간 내 수정된 로그 / 기간 내 전체 AI 호출 × 100
        """
        # 기능별 호출 수
        feature_result = await db.execute(
            select(AILog.feature_type, func.count(AILog.id))
            .where(
                and_(
                    AILog.created_at >= start_date,
                    AILog.created_at <= end_date
                )
            )
            .group_by(AILog.feature_type)
        )
        feature_counts = {row[0]: row[1] for row in feature_result.all()}
        
        # 총 토큰 사용량
        token_result = await db.execute(
            select(func.sum(AILog.tokens_used))
            .where(
                and_(
                    AILog.created_at >= start_date,
                    AILog.created_at <= end_date
                )
            )
        )
        total_tokens = token_result.scalar() or 0
        
        # 평균 응답 시간
        latency_result = await db.execute(
            select(func.avg(AILog.latency_ms))
            .where(
                and_(
                    AILog.created_at >= start_date,
                    AILog.created_at <= end_date,
                    AILog.latency_ms.isnot(None)
                )
            )
        )
        avg_latency = latency_result.scalar() or 0
        
        # 수정된 로그 수 (edit_rate 분자)
        edited_result = await db.execute(
            select(func.count(AILog.id))
            .where(
                and_(
                    AILog.created_at >= start_date,
                    AILog.created_at <= end_date,
                    AILog.was_edited == True
                )
            )
        )
        edited_count = edited_result.scalar() or 0
        
        total_in_period = sum(feature_counts.values())
        edit_rate = round((edited_count / total_in_period * 100), 1) if total_in_period > 0 else 0

        return {
            "total_calls": total_in_period,
            "by_feature": {
                "content": feature_counts.get("content", 0),
                "feedback": feature_counts.get("feedback", 0),
                "recommendation": feature_counts.get("recommendation", 0),
                "chat": feature_counts.get("chat", 0)
            },
            "total_tokens": total_tokens,
            "avg_latency_ms": round(avg_latency, 1),
            "edit_rate": edit_rate
        }
    
    @staticmethod
    async def get_ai_logs(
        db: AsyncSession,
        feature_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> list:
        """
        AI 로그 목록을 최신순으로 반환한다.
        feature_type으로 기능별 필터링, skip/limit으로 페이지네이션을 지원한다.
        관리자가 AI 호출 이력을 확인하고 품질을 모니터링할 때 사용한다.
        """
        query = select(AILog).order_by(AILog.created_at.desc())
        
        if feature_type:
            query = query.where(AILog.feature_type == feature_type)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        
        return list(result.scalars().all())


