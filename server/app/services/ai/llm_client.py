"""
OpenAI Async 클라이언트 싱글톤과 단순 텍스트 생성 헬퍼.

용도 요약: 챗봇 에이전트·콘텐츠·추천 문구는 get_openai_client()로 클라이언트를 받아
각 파일에서 await chat.completions.create(...)로 호출한다.
피드백 문구만 generate_text() 헬퍼(고정 시스템 프롬프트)를 쓴다.

get_openai_client()
    └── agent_nodes.py
            router_node()         → 의도 분류
            tool_executor_node()  → _extract_search_args / _extract_faq_keyword (검색·FAQ 인자 추출)
            response_node()       → 비스트리밍 최종 답변
            response_node_stream() → 스트리밍 최종 답변
    └── content_generator.py      → 강습 소개·커리큘럼 (동일 클라이언트로 직접 호출)
    └── recommendation_service.py → 추천 이유 한 줄

generate_text()
    └── feedback_generator.py     → 수강생·강사 피드백 문구

함수:
- get_openai_client() : AsyncOpenAI 클라이언트 싱글톤 반환
- generate_text()     : 고정 시스템 프롬프트로 GPT 응답만 받는 유틸리티
"""

from typing import Optional

from openai import AsyncOpenAI

from app.config import settings

_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """
    OpenAI 클라이언트를 반환한다.

    에이전트 노드(의도 분류, 검색 인자 추출, 답변 생성)와
    콘텐츠·추천 문구 생성에서 공통으로 사용한다.
    처음 호출할 때만 생성하고 이후에는 만들어둔 걸 재사용한다.
    매 요청마다 새로 만들면 연결 오버헤드가 생기기 때문이다.
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def generate_text(prompt: str) -> str:
    """
    프롬프트를 받아 GPT 응답 텍스트를 반환한다.

    get_openai_client()와 달리 클라이언트 가져오기 + GPT 호출 + 결과 반환을 한 번에 처리한다.
    시스템 프롬프트가 고정되어 있어 user 프롬프트만 넘기면 된다.
    피드백 생성처럼 매번 같은 옵션으로 호출하는 곳에서 반복 코드를 줄이기 위해 쓴다.
    """
    client = get_openai_client()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                # generate_text() 호출(피드백 등)에 공통으로 적용되는 역할 지시다.
                "content": "당신은 온라인 강의 콘텐츠 전문가입니다. 한국어로 답변하세요.",
            },
            {"role": "user", "content": prompt},  # 호출하는 쪽에서 넘기는 실제 요청
        ],
        temperature=0.7,  # 창의성과 일관성의 균형. 0이면 항상 같은 답, 1이면 너무 자유분방해진다.
    )
    return response.choices[0].message.content
