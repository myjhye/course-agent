from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Any


class ChatRequest(BaseModel):
    session_id: str
    message: str
    student_name: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    tool_used: Optional[str] = None
    tool_result: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    session_id: str
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class ChatSessionResponse(BaseModel):
    id: int
    session_id: str
    student_name: Optional[str]
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionDetailResponse(BaseModel):
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]
