from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Enrollment(Base):
    __tablename__ = "enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    # TODO: user_id, course_id 관계 추가 예정
    created_at = Column(DateTime(timezone=True), server_default=func.now())

