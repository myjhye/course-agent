from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class LessonView(Base):
    """강습 조회 기록"""
    __tablename__ = "lesson_views"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String(100), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # 같은 사람이 같은 강습 여러 번 조회 가능 (기록용)
    )


class LessonLike(Base):
    """강습 찜"""
    __tablename__ = "lesson_likes"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String(100), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('student_name', 'lesson_id', name='uq_student_lesson_like'),
    )
