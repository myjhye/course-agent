"""
OpenAI 클라이언트 관리와 단순 텍스트 생성 유틸리티.

에이전트 노드(router, response 등)는 get_openai_client()로 동기 클라이언트를 가져다 쓰고,
콘텐츠 생성·피드백 생성처럼 단순한 GPT 호출은 generate_text()를 바로 쓴다.

함수:
- get_openai_client() : 에이전트 노드용 동기 클라이언트 싱글톤 반환
- generate_text()     : 프롬프트를 받아 GPT 응답을 반환하는 단순 유틸리티
"""

from openai import AsyncOpenAI, OpenAI
from app.config import settings

# OpenAI 비동기 클라이언트 (컨텐츠 생성 등 백그라운드 작업용)
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

# OpenAI 동기 클라이언트 (에이전트 채팅용)
_openai_client = None


def get_openai_client() -> OpenAI:
    """
    OpenAI 동기 클라이언트 반환 (채팅용).

    LangGraph 에이전트 노드들은 대부분 동기 OpenAI SDK를 쓰고 있으므로,
    여기서 싱글톤으로 생성해 연결 수를 최소화한다.
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def generate_text(prompt: str) -> str:
    """
    간단한 텍스트 생성 유틸리티.

    강의 콘텐츠/문구 생성 등 에이전트 외부에서 재사용하기 위한 헬퍼이며,
    gpt-4o-mini + 고정 시스템 프롬프트를 사용한다.
    """
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                # 콘텐츠 생성·피드백 등 모든 호출에 공통으로 적용되는 역할 지시다.
                "content": "당신은 온라인 강의 콘텐츠 전문가입니다. 한국어로 답변하세요.",
            },
            {"role": "user", "content": prompt}, # 호출하는 쪽에서 넘기는 실제 요청
        ],
        temperature=0.7, # 창의성과 일관성의 균형. 0이면 항상 같은 답, 1이면 너무 자유분방해진다.
    )
    return response.choices[0].message.content

