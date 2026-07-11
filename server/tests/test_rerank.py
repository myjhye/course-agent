import pytest
import os
from dotenv import load_dotenv
from app.services.ai.cohere_client import rerank_documents

load_dotenv()

@pytest.mark.asyncio
async def test_cohere_rerank_integration():
    # API 키가 환경변수에 없을 경우 테스트를 스킵(skip) 처리하여 CI/CD 파이프라인에서 오류 방지
    if not os.getenv("COHERE_API_KEY"):
        pytest.skip("COHERE_API_KEY 환경변수가 설정되지 않아 통합 테스트를 스킵합니다.")

    query = "환불 규정이 어떻게 되나요?"
    
    # 1차 벡터 검색 후보군을 시뮬레이션한 가상 문서 리스트
    documents = [
        {
            "title": "강습 연기 규정",
            "content": "강습 연기는 개시일 전까지 1회에 한해 신청 가능하며, 시작 이후에는 연기가 불가합니다.",
            "source_type": "faq"
        },
        {
            "title": "환불 규정 및 절차 안내",
            "content": "수강 시작 후 7일 이내이고 진도율이 10% 미만일 경우 전액 환불이 가능합니다. 이후에는 수강한 기간에 따라 일할 계산되어 환불됩니다.",
            "source_type": "faq"
        },
        {
            "title": "셔틀버스 운행 안내",
            "content": "셔틀버스는 매시 정각 체육센터 정문에서 출발하며, 회원증을 소지한 분에 한하여 무료 탑승이 가능합니다.",
            "source_type": "faq"
        }
    ]

    # 리랭킹 수행 (top_n=2)
    reranked = await rerank_documents(query, documents, top_n=2)

    # 1. 반환된 개수가 top_n 스펙을 준수하는지 확인
    assert len(reranked) == 2
    
    # 2. Rerank 결과에 relevance_score 메트릭이 정상 포함되어 있는지 확인
    assert "relevance_score" in reranked[0]
    
    # 3. 질문("환불 규정")과 가장 일치도가 높은 '환불 규정 및 절차 안내' 문서가 1위(인덱스 0)로 올라왔는지 검증
    assert reranked[0]["title"] == "환불 규정 및 절차 안내"
    print("\n[Rerank Test Success] 1위 문서:", reranked[0]["title"], "점수:", reranked[0]["relevance_score"])
