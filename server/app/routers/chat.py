from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from app.database import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatSessionDetailResponse,
    ChatMessageResponse
)
from app.services.chat_service import ChatService
from app.models.chat import ChatSession, ChatMessage

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """메시지 전송 및 AI 응답"""
    user_msg, assistant_msg = await ChatService.chat(
        db=db,
        session_id=request.session_id,
        user_message=request.message,
        student_name=request.student_name
    )
    
    return ChatResponse(
        session_id=request.session_id,
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg)
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(db: AsyncSession = Depends(get_db)):
    """채팅 세션 목록"""
    sessions = await ChatService.get_sessions(db)
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session_detail(session_id: str, db: AsyncSession = Depends(get_db)):
    """세션 상세 (메시지 포함)"""
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = await ChatService.get_session_messages(db, session_id)
    
    return ChatSessionDetailResponse(
        session=ChatSessionResponse.model_validate(session),
        messages=[ChatMessageResponse.model_validate(m) for m in messages]
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """세션 삭제"""
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.execute(delete(ChatSession).where(ChatSession.session_id == session_id))
    await db.commit()
    
    return {"message": "Session deleted"}

