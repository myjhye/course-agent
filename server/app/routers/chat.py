from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


# TODO: 구현 예정
@router.post("/")
async def create_chat(db: AsyncSession = Depends(get_db)):
    pass

