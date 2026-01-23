from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.schemas.dashboard import DashboardResponse, AILogResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/admin/dashboard", tags=["admin-dashboard"])


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    start_date: Optional[datetime] = Query(None, description="시작일 (기본: 이번 달 1일)"),
    end_date: Optional[datetime] = Query(None, description="종료일 (기본: 오늘)"),
    db: AsyncSession = Depends(get_db)
):
    """대시보드 통계 조회"""
    return await DashboardService.get_dashboard_stats(db, start_date, end_date)


@router.get("/ai-logs", response_model=List[AILogResponse])
async def get_ai_logs(
    feature_type: Optional[str] = Query(None, description="기능 타입 (content, feedback, recommendation, chat)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """AI 사용 로그 목록"""
    return await DashboardService.get_ai_logs(db, feature_type, skip, limit)

