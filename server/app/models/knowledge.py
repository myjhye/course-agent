"""
RAG용 지식 문서 + 임베딩 모델.

knowledge_base/ 폴더의 md 파일을 청킹하여 저장한다.
각 청크는 OpenAI text-embedding-3-small로 임베딩되어 pgvector에 저장되고,
embedding_service.search_similar()에서 쿼리 벡터와 유사도 검색에 사용된다.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)

    # 원본 문서 정보: 어느 파일·타입에서 왔는지 구분해 source_type 필터 검색에 쓴다.
    source_file = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # "sport_guide" | "platform" | "instructor" | "tips" 등
    title = Column(String(500), nullable=False)  # 청크 제목(섹션 헤더 등). 검색 결과에 표시용.

    # 청크 내용: RAG 검색 시 유사도 매칭 후 LLM에 넘기는 본문.
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # 추가 메타데이터(JSON 문자열). 확장용.

    # 벡터 임베딩. 1536차원 = text-embedding-3-small. pgvector 연산자(<=>)로 유사도 정렬한다.
    embedding = Column(Vector(1536), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

