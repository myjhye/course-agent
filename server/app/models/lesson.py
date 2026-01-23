from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class SportType(str, enum.Enum):
    SWIMMING = "swimming"
    TENNIS = "tennis"
    GOLF = "golf"
    FITNESS = "fitness"
    YOGA = "yoga"
    PILATES = "pilates"
    OTHER = "other"


class TargetAudience(str, enum.Enum):
    ADULT = "adult"
    CHILD = "child"
    SENIOR = "senior"
    ALL = "all"


class Difficulty(str, enum.Enum):
    BEGINNER = "beginner"      # 입문
    ELEMENTARY = "elementary"  # 초급
    INTERMEDIATE = "intermediate"  # 중급
    ADVANCED = "advanced"      # 고급


class LessonStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    sport_type = Column(Enum(SportType), nullable=False)
    target_audience = Column(Enum(TargetAudience), nullable=False, default=TargetAudience.ADULT)
    difficulty = Column(Enum(Difficulty), nullable=False, default=Difficulty.BEGINNER)
    instructor_id = Column(Integer, ForeignKey("instructors.id"), nullable=True)
    status = Column(Enum(LessonStatus), nullable=False, default=LessonStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    instructor = relationship("Instructor", back_populates="lessons")
    contents = relationship("LessonContent", back_populates="lesson", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="lesson", cascade="all, delete-orphan")

