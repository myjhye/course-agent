from openai import AsyncOpenAI, OpenAI
from google import genai
from app.config import settings
import os
import cloudinary
import cloudinary.uploader

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

# Cloudinary 설정 (환경 변수에서 읽어옴)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


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
    """Gemini로 생성한 이미지를 Cloudinary에 업로드하고 영구 URL 반환"""
    
    # 이미지 생성 요청
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config={"response_modalities": ["image", "text"]}
    )
    
    # 응답에서 이미지 추출 및 Cloudinary 업로드
    for part in response.candidates[0].content.parts:
        if hasattr(part, 'inline_data') and part.inline_data:
            image_bytes = part.inline_data.data
            
            # 🔥 서버 폴더 대신 Cloudinary로 직접 업로드
            upload_result = cloudinary.uploader.upload(
                image_bytes,
                folder="course_agent/thumbnails"  # 폴더 정리용
            )
            
            # 🔥 이 URL은 서버가 꺼져도 영구적으로 유지됩니다
            return upload_result['secure_url']
    
    # 이미지 생성 실패 시
    return None
