import os
import httpx
from typing import List, Dict, Any

# Cohere Rerank API URL
COHERE_RERANK_URL = "https://api.cohere.com/v1/rerank"


async def rerank_documents(
    query: str,
    documents: List[Dict[str, Any]],
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """
    Cohere Rerank v3 API를 호출하여 문서를 질문과의 의미적 정합성에 기반해 재정렬합니다.
    
    [역할 분담]
    - 이 함수는 Cohere API 연동만 전담하며, 호출 실패 시 빈 리스트 []를 반환합니다.
    - 실제 원본 벡터 검색 결과로의 폴백 처리는 원본 컨텍스트를 쥐고 있는 호출부(tool_executor.py)가 전담합니다.
    """
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        print("[Cohere] COHERE_API_KEY가 설정되지 않아 리랭킹을 건너뜁니다.")
        return []

    if not documents:
        return []

    try:
        # Cohere API는 정렬할 문서 본문 텍스트 배열을 요구함
        # documents의 각 항목은 {"title": ..., "content": ..., "source_type": ...} 형태
        docs_content = [doc.get("content", "") for doc in documents]

        payload = {
            "model": "rerank-multilingual-v3.0",  # 한국어 등 다국어 정밀 재정렬 모델
            "query": query,
            "documents": docs_content,
            "top_n": top_n
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                COHERE_RERANK_URL,
                headers=headers,
                json=payload,
                timeout=8.0  # RAG 검색 속도에 무리 없도록 타임아웃 제한
            )
            
            if response.status_code != 200:
                print(f"[Cohere] Rerank API 호출 실패 (상태코드 {response.status_code}): {response.text}")
                return []
                
            result = response.json()

        reranked_docs = []
        for hit in result.get("results", []):
            idx = hit["index"]
            original_doc = dict(documents[idx])
            # Cohere가 제공한 정밀 정합성 점수를 매핑
            original_doc["relevance_score"] = hit.get("relevance_score", 0.0)
            reranked_docs.append(original_doc)

        return reranked_docs

    except Exception as e:
        print(f"[Cohere] Rerank 처리 중 예외 발생: {e}")
        return []
