from openai import AsyncOpenAI, OpenAI
from app.config import settings

# OpenAI 비동기 클라이언트
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

# OpenAI 동기 클라이언트 (채팅용)
_openai_client = None


def get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 반환 (채팅용 - 동기)"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def generate_text(prompt: str) -> str:
    """OpenAI로 텍스트 생성"""
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 온라인 강의 콘텐츠 전문가입니다. 한국어로 답변하세요."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content
