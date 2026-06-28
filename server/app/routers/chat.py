"""
채팅 라우터. HTTP 요청을 받아 ChatOrchestrator에 위임한다.
실제 LLM 실행은 ChatOrchestrator가 담당하고, 여기서는 HTTP/SSE 계층만 처리한다.

엔드포인트:
- POST /         : 비스트리밍 채팅. 응답이 다 만들어지면 한 번에 반환. 프론트에서는 사용하지 않음.
- POST /stream   : 스트리밍 채팅. 토큰이 생길 때마다 브라우저로 바로 전송. 실제 채팅 화면에서 사용.
- GET  /sessions : 채팅 세션 목록 조회.
- GET  /sessions/{session_id}    : 세션 상세 + 전체 메시지 조회.
- DELETE /sessions/{session_id}  : 세션 및 하위 메시지 삭제.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatSessionDetailResponse,
    ChatMessageResponse,
)
from app.services.chat_orchestrator import ChatOrchestrator
from app.models.chat import ChatSession, ChatMessage

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    비스트리밍 채팅.
    응답이 완전히 생성된 후 한 번에 반환한다.
    프론트에서는 스트리밍을 쓰기 때문에 이 엔드포인트는 실제로 호출되지 않는다.
    """
    user_msg, assistant_msg = await ChatOrchestrator.chat(
        db=db,
        session_id=request.session_id,
        user_message=request.message,
        student_name=request.student_name,
    )

    return ChatResponse(
        session_id=request.session_id,
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg),
    )


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE 스트리밍 채팅. 실제 채팅 화면에서 사용하는 엔드포인트.
    ChatOrchestrator.chat_stream이 status/token/done 이벤트를 yield하고,
    EventSourceResponse가 SSE 프로토콜로 브라우저에 전달한다.
    브라우저 기본 EventSource는 GET만 지원해서, 프론트에서 fetch + ReadableStream으로 POST SSE를 직접 구현했다.
    """

    async def event_generator():
        async for event in ChatOrchestrator.chat_stream(
            db=db,
            session_id=request.session_id,
            user_message=request.message,
            student_name=request.student_name,
        ):
            yield event

    # 한글이 포함된 SSE 이벤트가 깨지지 않도록 charset을 명시한다.
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(db: AsyncSession = Depends(get_db)):
    """세션 목록 조회. 프론트 사이드바에 최근 대화 목록을 표시할 때 사용한다."""
    sessions = await ChatOrchestrator.get_sessions(db)
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session_detail(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    세션 상세 조회.
    세션 정보와 전체 메시지를 한 번에 반환한다.
    이전 대화를 클릭했을 때 채팅 화면을 복원하는 데 사용한다.
    """
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await ChatOrchestrator.get_session_messages(db, session_id)

    return ChatSessionDetailResponse(
        session=ChatSessionResponse.model_validate(session),
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    세션 삭제.
    FK 무결성을 위해 메시지를 먼저 삭제한 뒤 세션을 삭제한다.
    """
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.execute(delete(ChatSession).where(ChatSession.session_id == session_id))
    await db.commit()

    return {"message": "Session deleted"}


