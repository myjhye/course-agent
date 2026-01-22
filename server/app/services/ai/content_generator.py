from app.services.ai.llm_client import generate_text, generate_image


async def generate_course_content(title: str, category: str) -> dict:
    """강의 콘텐츠 전체 생성 (설명, 커리큘럼, 썸네일)"""
    
    # 1. 설명 생성
    description_prompt = f"""
다음 강의의 매력적인 설명을 작성해주세요.

강의 제목: {title}
카테고리: {category}

요구사항:
- 3~4문장으로 작성
- 수강 대상과 기대 효과 포함
- 전문적이면서도 친근한 톤
"""
    description = await generate_text(description_prompt)
    
    # 2. 커리큘럼 생성
    curriculum_prompt = f"""
다음 강의의 커리큘럼을 작성해주세요.

강의 제목: {title}
카테고리: {category}

요구사항:
- 5~8개 섹션으로 구성
- 각 섹션에 2~3개 소주제
- 번호 매기기 형식 (1. 2. 3.)
"""
    curriculum = await generate_text(curriculum_prompt)
    
    # 3. 썸네일 이미지 생성
    thumbnail_url = None
    try:
        thumbnail_prompt = f"""
Create a professional educational course thumbnail image.
Course title: "{title}"
Category: {category}

Requirements:
- Modern, clean design
- Vibrant colors
- Professional e-learning style
- Include relevant icons or imagery for {category}
- No text in image
- 16:9 aspect ratio
"""
        thumbnail_url = generate_image(thumbnail_prompt)
    except Exception as e:
        print(f"썸네일 생성 실패: {e}")
        thumbnail_url = None
    
    return {
        "description": description,
        "curriculum": curriculum,
        "thumbnail_url": thumbnail_url
    }
