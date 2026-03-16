"""
임베딩 생성 + pgvector 벡터 검색 서비스.
"""

from typing import Optional, List, Dict, Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.services.ai.langfuse_client import get_langfuse


EMBEDDING_MODEL = "text-embedding-3-small"  # 1536차원, 저비용
EMBEDDING_DIMENSION = 1536

_client: Optional[AsyncOpenAI] = None


def get_embedding_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def create_embedding(text_input: str, trace_id: Optional[str] = None) -> List[float]:
    """텍스트를 임베딩 벡터로 변환."""
    client = get_embedding_client()
    trace = get_langfuse()

    async def _call() -> List[float]:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text_input,
        )
        return response.data[0].embedding

    if not trace:
        return await _call()

    obs_kwargs: Dict[str, Any] = {
        "as_type": "generation",
        "name": "embedding",
        "model": EMBEDDING_MODEL,
        "input": {"text": text_input},
    }
    if trace_id:
        obs_kwargs["metadata"] = {"trace_id": trace_id}

    try:
        # 임베딩 호출도 LLM과 동일한 관측 단위로 남겨, RAG 품질 이슈를 추적 가능하게 만든다
        with trace.start_as_current_observation(**obs_kwargs) as gen:
            embedding = await _call()
            gen.update(output={"vector_dim": len(embedding)})
            return embedding
    except Exception:
        # 관측 실패 시, 임베딩 호출만 수행
        return await _call()


async def search_similar(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    source_type: Optional[str] = None,
    similarity_threshold: float = 0.3,
    trace_id: Optional[str] = None,
) -> List[Dict]:
    """
    knowledge_chunks 테이블을 대상으로 벡터 유사도 검색을 수행한다.

    Args:
        query: 검색 쿼리 텍스트
        top_k: 반환할 최대 결과 수
        source_type: 필터링할 소스 타입 (None이면 전체 검색)
        similarity_threshold: 최소 유사도 (코사인 유사도, 0~1)
    """

    trace = get_langfuse()

    async def _run() -> List[Dict]:
        # 검색 쿼리를 동일한 모델로 임베딩해, 저장된 knowledge 임베딩과 같은 공간에서 비교한다
        query_embedding = await create_embedding(query, trace_id=trace_id)

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

        # SQLAlchemy를 통해 실제 벡터 검색 쿼리를 실행한다
        result = await db.execute(sql, params)
        rows = result.fetchall()

        filtered_rows = [
            row
            for row in rows
            if getattr(row, "similarity", 0.0) >= similarity_threshold
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

    if not trace:
        return await _run()

    span_kwargs: Dict[str, Any] = {
        "as_type": "span",
        "name": "rag_search",
        "input": {
            "query": query,
            "top_k": top_k,
            "source_type": source_type,
            "similarity_threshold": similarity_threshold,
        },
    }
    if trace_id:
        span_kwargs["metadata"] = {"trace_id": trace_id}

    try:
        with trace.start_as_current_observation(**span_kwargs) as span:
            results = await _run()
            top_similarities = [r["similarity"] for r in results[:3]]
            span.update(
                output={
                    "result_count": len(results),
                    "top_similarities": top_similarities,
                }
            )
            return results
    except Exception:
        return await _run()

