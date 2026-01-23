from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean
from sqlalchemy.sql import func
from app.database import Base


class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    feature_type = Column(String(50), nullable=False)  # content, feedback, recommendation, chat
    lesson_id = Column(Integer, nullable=True)
    enrollment_id = Column(Integer, nullable=True)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    was_edited = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

