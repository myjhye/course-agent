from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()


# TODO: 구현 예정
@router.get("/")
async def get_enrollments(db: AsyncSession = Depends(get_db)):
    pass

