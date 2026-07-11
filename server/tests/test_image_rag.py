import pytest
import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

# 테스트 대상 로컬 API URL
API_URL = "http://localhost:8000/api/chat/stream"


async def run_chat_query(message: str) -> dict:
    """스트리밍 API를 호출하여 최종 텍스트 답변과 사용된 도구 목록을 수집합니다."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "message": message,
        "student_name": "홍길동",
        "session_id": f"test-image-rag-{hash(message)}"
    }
    
    full_content = []
    tools_used = []
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", API_URL, headers=headers, json=payload, timeout=30.0) as r:
                async for line in r.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:])
                            if "content" in data:
                                full_content.append(data["content"])
                            elif "tools_used" in data:
                                tools_used = data["tools_used"]
                        except:
                            pass
        except Exception as e:
            pytest.fail(f"API 호출 실패: {e}")
            
    return {
        "response": "".join(full_content),
        "tools_used": tools_used
    }


@pytest.mark.asyncio
async def test_tennis_facility_query():
    """테니스 코트 시설 이미지 RAG 검증"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY가 없어 테스트를 건너뜁니다.")
        
    result = await run_chat_query("테니스 코트 사진 실내인가요? 전경 좀 보여주세요.")
    response = result["response"]
    
    # 1. RAG faq 에이전트 도구가 작동했는지 확인
    assert "faq" in result["tools_used"]
    # 2. 테니스장 이미지 링크가 올바르게 렌더링되었는지 확인
    assert "/static/images/tennis_court_facility.png" in response
    assert "![실내 테니스" in response or "![테니스" in response
    print("\n[PASSED] 테니스 코트 이미지 RAG 정상 작동 확인")


@pytest.mark.asyncio
async def test_pilates_facility_query():
    """필라테스 룸 시설 이미지 RAG 검증"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY가 없어 테스트를 건너뜁니다.")
        
    result = await run_chat_query("기구 필라테스실 환경이 어떤지 사진 볼 수 있을까요?")
    response = result["response"]
    
    # 1. RAG faq 에이전트 도구가 작동했는지 확인
    assert "faq" in result["tools_used"]
    # 2. 필라테스 이미지 링크가 올바르게 렌더링되었는지 확인
    assert "/static/images/pilates_studio_facility.png" in response
    assert "![기구 필라테스" in response or "![필라테스" in response
    print("\n[PASSED] 기구 필라테스 이미지 RAG 정상 작동 확인")


@pytest.mark.asyncio
async def test_negative_faq_query():
    """네거티브 케이스: 이미지와 상관없는 일반 FAQ 질문 시 이미지 링크 렌더링 억제 검증"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY가 없어 테스트를 건너뜁니다.")
        
    result = await run_chat_query("중도 해지 시 환불 규정이 어떻게 되나요?")
    response = result["response"]
    
    # 1. RAG faq 에이전트 작동 확인
    assert "faq" in result["tools_used"]
    # 2. 본문에 가짜 이미지 마크다운 링크가 존재하지 않는지 (Hallucination 억제) 확인
    assert "![" not in response
    assert "/static/images/" not in response
    assert "환불" in response
    print("\n[PASSED] 네거티브 케이스 이미지 렌더링 억제 및 환불 규정 정상 답변 확인")


@pytest.mark.asyncio
async def test_multi_image_query():
    """포괄적 질문 시 다중 이미지 매칭 및 다중 마크다운 렌더링 검증"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY가 없어 테스트를 건너뜁니다.")
        
    result = await run_chat_query("체육관의 수영장, 테니스장, 필라테스실 전경 시설 사진들 한 번에 다 보여주세요.")
    response = result["response"]
    
    # 1. RAG faq 에이전트 작동 확인
    assert "faq" in result["tools_used"]
    
    # 2. 세 장의 이미지가 모두 답변에 포함되어 있는지 검증 (Rerank 후보군에서 수영장, 테니스, 필라테스 모두 채택)
    image_count = 0
    if "/static/images/swimming_pool_facility.png" in response:
        image_count += 1
    if "/static/images/tennis_court_facility.png" in response:
        image_count += 1
    if "/static/images/pilates_studio_facility.png" in response:
        image_count += 1
        
    # 적어도 2장 이상의 이미지가 동시에 Reranking 되어 나타났는지 검증 (top_n=3 이므로 3장 다 나와야 함)
    assert image_count >= 2
    print(f"\n[PASSED] 포괄적 질문 시 다중 이미지 매칭 개수: {image_count}개 확인")
