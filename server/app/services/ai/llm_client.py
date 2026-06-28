"""
OpenAI 비동기 클라이언트(AsyncOpenAI) 싱글톤 인스턴스 관리 및
공통 텍스트 생성 유틸리티를 제공한다.
"""

from typing import Optional

from openai import AsyncOpenAI

from app.config import settings

_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """
    OpenAI 비동기 클라이언트(AsyncOpenAI)의 싱글톤 인스턴스를 반환한다.
    - 최초 호출 시 인스턴스를 생성하며, 이후에는 커넥션 오버헤드를 방지하기 위해 생성된 인스턴스를 재사용한다.
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def generate_text(prompt: str) -> str:
    """
    전달받은 사용자 프롬프트를 사용하여 OpenAI GPT 모델의 텍스트 응답을 일괄 생성하여 반환한다.
    - 공통 시스템 페르소나 지침을 내장하고 있어, 단순 단발성 문구 생성 시 보일러플레이트 코드를 최소화한다.
    """
    client = get_openai_client()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "당신은 온라인 강의 콘텐츠 전문가입니다. 한국어로 답변하세요.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content

