"""
RAG용 지식 문서 + 임베딩 모델.

knowledge_base/ 폴더의 md 파일을 청킹하여 저장한다.
각 청크는 OpenAI text-embedding-3-small로 임베딩되어 pgvector에 저장된다.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)

    # 원본 문서 정보
    source_file = Column(String(255), nullable=False)   # 예: "sports/swimming.md"
    source_type = Column(String(50), nullable=False)    # 예: "sport_guide" | "platform" | "instructor" | "tips"
    title = Column(String(500), nullable=False)         # 청크 제목 (섹션 헤더 등)

    # 청크 내용
    content = Column(Text, nullable=False)              # 실제 텍스트
    metadata_json = Column(Text, nullable=True)         # 추가 메타데이터 (JSON 문자열)

    # 벡터 임베딩 (1536차원 = text-embedding-3-small)
    embedding = Column(Vector(1536), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

