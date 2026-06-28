"""
임베딩 생성 + pgvector 벡터 검색 서비스.

사용자 질문을 벡터로 변환하고, knowledge_chunks 테이블에서
의미적으로 가장 유사한 FAQ 문서를 찾아오는 RAG 검색을 담당한다.
faq_agent가 이 파일을 통해 검색을 수행한다.
"""

from typing import Optional, List, Dict, Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.services.ai.langfuse_client import get_langfuse


EMBEDDING_MODEL = "text-embedding-3-small"  # 1536차원, 저비용 임베딩 모델
EMBEDDING_DIMENSION = 1536

_client: Optional[AsyncOpenAI] = None


def get_embedding_client() -> AsyncOpenAI:
    """임베딩 전용 OpenAI 클라이언트 싱글톤. 매 호출마다 새로 만들지 않고 재사용한다."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def create_embedding(text_input: str, trace_id: Optional[str] = None) -> List[float]:
    """
    텍스트를 1536차원 벡터로 변환한다.
    예: "환불 정책" → [0.12, -0.34, 0.07, ...] (1536개 숫자)

    Langfuse가 있으면 어떤 텍스트를 임베딩했는지 generation으로 기록한다.
    Langfuse 오류가 나도 임베딩은 정상 실행된다.
    """
    client = get_embedding_client()
    trace = get_langfuse()

    async def _call() -> List[float]:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text_input,
        )
        return response.data[0].embedding  # 1536개 숫자로 이루어진 벡터 반환

    if not trace:
        return await _call()

    obs_kwargs: Dict[str, Any] = {
        "as_type": "generation",
        "name": "embedding",
        "model": EMBEDDING_MODEL,
        "input": {"text": text_input},  # 어떤 텍스트를 임베딩했는지 기록
    }
    if trace_id:
        obs_kwargs["metadata"] = {"trace_id": trace_id}

    try:
        with trace.start_as_current_observation(**obs_kwargs) as gen:
            embedding = await _call()
            gen.update(output={"vector_dim": len(embedding)})  # 결과 차원수(1536) 기록
            return embedding
    except Exception:
        return await _call()  # Langfuse 오류나도 임베딩은 정상 실행


async def search_similar(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    source_type: Optional[str] = None,
    similarity_threshold: float = 0.3,
    trace_id: Optional[str] = None,
) -> List[Dict]:
    """
    knowledge_chunks 테이블에서 질문과 가장 유사한 문서를 찾아온다.

    흐름:
    1. 질문을 벡터로 변환
    2. pgvector로 코사인 유사도 기준 top_k개 검색
    3. 유사도 0.3 미만 결과 제거 (낮은 유사도는 LLM 환각 유발 가능)

    Args:
        query: 검색할 텍스트
        top_k: 가져올 최대 결과 수
        source_type: 특정 소스 타입으로 필터링 (None이면 전체)
        similarity_threshold: 이 값 미만 결과는 제거 (기본 0.3)
    """
    trace = get_langfuse()

    async def _run() -> List[Dict]:
        # 질문을 knowledge_chunks 임베딩과 같은 모델로 벡터화해서 같은 공간에서 비교
        query_embedding = await create_embedding(query, trace_id=trace_id)

        # pgvector는 텍스트 형태 배열을 받으니까 Python 리스트를 문자열로 변환
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        where_clause = ""
        if source_type:
            where_clause = "AND source_type = :source_type"

        # <=> : 코사인 거리 연산자 (거리가 작을수록 유사)
        # 1 - 거리 = 유사도 (1에 가까울수록 유사)
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

        # 유사도 임계값 미만 결과 제거
        # 관련 없는 문서를 LLM에 넘기면 엉뚱한 답변을 생성할 수 있어서 미리 걸러낸다
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

    # RAG 검색 전체를 span으로 묶어 쿼리, 결과 수, 상위 유사도를 한 번에 모니터링
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
            span.update(
                output={
                    "result_count": len(results),
                    "top_similarities": [r["similarity"] for r in results[:3]],
                }
            )
            return results
    except Exception:
        return await _run()  # Langfuse 오류가 검색을 막으면 안 되므로 무시
