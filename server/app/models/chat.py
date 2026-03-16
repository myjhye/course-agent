"""
채팅 세션 및 메시지 모델.

세션 단위로 대화를 묶고, 각 메시지는 user/assistant 역할과 내용을 저장한다.
에이전트가 도구를 썼을 때는 tool_used/tool_result로 어떤 도구·결과가 쓰였는지 남겨 분석/디버깅에 쓴다.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # 클라이언트가 생성한 UUID 등으로 세션을 식별. API에서는 이 값으로 세션을 지정한다.
    session_id = Column(String(36), unique=True, index=True, nullable=False)
    # 수강생 이름(옵션). 있으면 에이전트가 개인화·수강 현황/추천 도구에 사용한다.
    student_name = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    # 에이전트가 이 턴에서 사용한 도구 이름. 없으면 None.
    tool_used = Column(String(50), nullable=True)
    # 도구 실행 결과(요약). Langfuse 없이도 "무슨 도구가 어떤 결과를 냈는지"를 DB에서 볼 수 있게 한다.
    tool_result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

