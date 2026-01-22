from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class AILog(Base):
    __tablename__ = "ai_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    # TODO: log_type, content 등 필드 추가 예정
    created_at = Column(DateTime(timezone=True), server_default=func.now())

