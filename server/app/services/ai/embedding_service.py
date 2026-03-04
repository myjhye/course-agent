"""
임베딩 생성 + pgvector 벡터 검색 서비스.
"""

from typing import Optional, List, Dict

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings


EMBEDDING_MODEL = "text-embedding-3-small"  # 1536차원, 저비용
EMBEDDING_DIMENSION = 1536

_client: Optional[AsyncOpenAI] = None


def get_embedding_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def create_embedding(text_input: str) -> List[float]:
    """텍스트를 임베딩 벡터로 변환."""
    client = get_embedding_client()
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text_input,
    )
    return response.data[0].embedding


async def search_similar(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    source_type: Optional[str] = None,
    similarity_threshold: float = 0.3,
) -> List[Dict]:
    """
    knowledge_chunks 테이블을 대상으로 벡터 유사도 검색을 수행한다.

    Args:
        query: 검색 쿼리 텍스트
        top_k: 반환할 최대 결과 수
        source_type: 필터링할 소스 타입 (None이면 전체 검색)
        similarity_threshold: 최소 유사도 (코사인 유사도, 0~1)
    """

    # 1) 쿼리 임베딩 생성
    query_embedding = await create_embedding(query)

    # 2) pgvector 코사인 유사도 검색
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    where_clause = ""
    if source_type:
        where_clause = "AND source_type = :source_type"

    sql = text(
        f"""
        SELECT
            id,
            title,
            content,
            source_type,
            source_file,
            1 - (embedding <=> cast(:embedding AS vector)) AS similarity
        FROM knowledge_chunks
        WHERE embedding IS NOT NULL
        {where_clause}
        ORDER BY embedding <=> cast(:embedding AS vector)
        LIMIT :top_k
        """
    )

    params: Dict[str, object] = {
        "embedding": embedding_str,
        "top_k": top_k,
    }
    if source_type:
        params["source_type"] = source_type

    result = await db.execute(sql, params)
    rows = result.fetchall()

    filtered_rows = [
        row for row in rows if getattr(row, "similarity", 0.0) >= similarity_threshold
    ]

    return [
        {
            "id": row.id,
            "title": row.title,
            "content": row.content,
            "source_type": row.source_type,
            "source_file": row.source_file,
            "similarity": round(row.similarity, 4),
        }
        for row in filtered_rows
    ]

