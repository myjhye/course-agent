from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/my/recommendations", tags=["my-recommendations"])


@router.get("/", response_model=List[RecommendationResponse])
async def get_recommendations(
    student_name: str = Query(..., description="수강생 이름"),
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    """수강생 맞춤 강습 추천"""
    recommendations = await RecommendationService.get_recommendations(
        db, student_name, limit
    )
    return recommendations

