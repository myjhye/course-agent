from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    keywords = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

