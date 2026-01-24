from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional
from app.database import get_db
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/my/recommendations", tags=["my-recommendations"])


@router.get("/")
async def get_recommendations(
    student_name: str = Query(..., description="수강생 이름"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Optional[dict]]:
    """카테고리별 추천 조회"""
    return await RecommendationService.get_categorized_recommendations(db, student_name)

