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
                "content": "당신은 온라인 강의 콘텐츠 전문가입니다. 한국어로 답변하세요.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content

