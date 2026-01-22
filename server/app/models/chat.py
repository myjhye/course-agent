from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    # TODO: user_id, course_id, message 등 필드 추가 예정
    created_at = Column(DateTime(timezone=True), server_default=func.now())

