from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False, unique=True)
    student_feedback = Column(Text, nullable=True)    # 수강생용
    instructor_feedback = Column(Text, nullable=True)  # 강사용
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    enrollment = relationship("Enrollment", back_populates="feedback")

