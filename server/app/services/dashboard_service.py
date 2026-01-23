from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
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
        """대시보드 전체 통계"""
        
        # 기본값: 이번 달
        if not start_date:
            today = datetime.now()
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        # 강습 통계
        lesson_stats = await DashboardService._get_lesson_stats(db)
        
        # 수강 통계
        enrollment_stats = await DashboardService._get_enrollment_stats(db, start_date, end_date)
        
        # 강사 통계
        instructor_stats = await DashboardService._get_instructor_stats(db)
        
        # AI 사용 통계
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
        """강습 통계"""
        
        # 전체 수
        total_result = await db.execute(select(func.count(Lesson.id)))
        total = total_result.scalar() or 0
        
        # 상태별 수
        status_result = await db.execute(
            select(Lesson.status, func.count(Lesson.id))
            .group_by(Lesson.status)
        )
        status_counts = {row[0].value: row[1] for row in status_result.all()}
        
        # 종목별 수
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
        """수강 통계"""
        
        # 전체 수강 수
        total_result = await db.execute(select(func.count(Enrollment.id)))
        total = total_result.scalar() or 0
        
        # 기간 내 신규 등록
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
        
        # 상태별 수
        status_result = await db.execute(
            select(Enrollment.status, func.count(Enrollment.id))
            .group_by(Enrollment.status)
        )
        status_counts = {row[0].value: row[1] for row in status_result.all()}
        
        # 평균 출석률
        avg_result = await db.execute(
            select(func.avg(Enrollment.attendance_rate))
            .where(Enrollment.attendance_rate.isnot(None))
        )
        avg_attendance = avg_result.scalar() or 0
        
        # 기간 내 수료
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
        """강사 통계"""
        
        total_result = await db.execute(select(func.count(Instructor.id)))
        total = total_result.scalar() or 0
        
        return {
            "total": total
        }
    
    @staticmethod
    async def _get_ai_stats(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """AI 사용 통계"""
        
        # 기능별 사용 횟수
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
        
        # 전체 토큰 사용량
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
        
        # 수정된 비율 (was_edited)
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
        """AI 로그 목록"""
        
        query = select(AILog).order_by(AILog.created_at.desc())
        
        if feature_type:
            query = query.where(AILog.feature_type == feature_type)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        
        return list(result.scalars().all())

