from openai import AsyncOpenAI, OpenAI
from google import genai
from app.config import settings
import os
import uuid

# OpenAI 비동기 클라이언트 (기존 함수용)
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

# OpenAI 동기 클라이언트 (채팅용)
_openai_client = None


def get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 반환 (채팅용 - 동기)"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client

# Gemini 클라이언트
gemini_client = genai.Client(api_key=settings.gemini_api_key)


async def generate_text(prompt: str) -> str:
    """OpenAI로 텍스트 생성"""
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 온라인 강의 콘텐츠 전문가입니다. 한국어로 답변하세요."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content


def generate_image(prompt: str) -> str:
    """Gemini Imagen으로 이미지 생성 후 로컬 저장"""
    
    # 이미지 생성 요청
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config={
            "response_modalities": ["image", "text"]
        }
    )
    
    # 이미지 저장 디렉토리 생성
    os.makedirs("static/thumbnails", exist_ok=True)
    filename = f"{uuid.uuid4()}.png"
    filepath = f"static/thumbnails/{filename}"
    
    # 응답에서 이미지 추출 및 저장
    for part in response.candidates[0].content.parts:
        if hasattr(part, 'inline_data') and part.inline_data:
            image_data = part.inline_data.data
            with open(filepath, "wb") as f:
                f.write(image_data)
            return f"/static/thumbnails/{filename}"
    
    # 이미지 생성 실패 시
    return None
