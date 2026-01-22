from app.services.ai.llm_client import generate_text, generate_image

# ✅ 1. 비즈니스 룰: 우리 서비스에서 허용하는 카테고리 목록 정의
VALID_CATEGORIES = [
    "프로그래밍",
    "데이터 사이언스",
    "디자인",
    "마케팅",
    "비즈니스",
    "외국어",
    "자기계발",
    "기타"
]


async def generate_course_draft(topic: str) -> dict:
    """Topic 기반으로 강의 초안 생성 (정형화된 카테고리 적용)"""
    
    # ✅ 2. 프롬프트에 '허용된 목록'을 주입 (Grounding)
    categories_str = ", ".join(VALID_CATEGORIES)
    
    title_category_prompt = f"""
다음 주제를 바탕으로 강의 제목과 카테고리를 생성해주세요.

주제: {topic}

[제약 사항]
1. 제목: 20자 이내로 매력적이고 명확하게 작성.
2. 카테고리: 반드시 다음 목록 중 가장 적절한 하나를 선택할 것. 목록에 없으면 '기타'를 선택.
   - 목록: [{categories_str}]

[응답 형식]
제목: [생성된 제목]
카테고리: [선택한 카테고리]
"""
    
    # LLM 호출
    response_text = await generate_text(title_category_prompt)
    
    # --- 파싱 및 검증 로직 ---
    title = ""
    category = "기타"  # 기본값
    
    for line in response_text.split('\n'):
        line = line.strip()
        if line.startswith('제목:'):
            title = line.split(':', 1)[1].strip()
        elif line.startswith('카테고리:'):
            raw_category = line.split(':', 1)[1].strip()
            
            # ✅ 3. 안전 장치: LLM이 뱉은 말이 유효한 카테고리인지 확인
            # (공백 제거 및 정확한 매칭 확인)
            if raw_category in VALID_CATEGORIES:
                category = raw_category
            else:
                # LLM이 엉뚱한 말을 했다면 '기타'로 강제 매핑하거나, 
                # 가장 유사한 걸 찾는 로직을 추가할 수도 있음.
                category = "기타"

    if not title:
        title = f"{topic} 강의"

    # 2. 설명 생성
    description_prompt = f"""
다음 강의의 매력적인 설명을 작성해주세요.

강의 제목: {title}
카테고리: {category}
주제: {topic}

요구사항:
- 3~4문장으로 작성
- 수강 대상과 기대 효과 포함
- 전문적이면서도 친근한 톤
"""
    description = await generate_text(description_prompt)
    
    # 3. 커리큘럼 생성
    curriculum_prompt = f"""
다음 강의의 커리큘럼을 작성해주세요.

강의 제목: {title}
카테고리: {category}
주제: {topic}

요구사항:
- 5~8개 섹션으로 구성
- 각 섹션에 2~3개 소주제
- 번호 매기기 형식 (1. 2. 3.)
"""
    curriculum = await generate_text(curriculum_prompt)

    # 4. 썸네일 생성 (카테고리가 정확해져서 이미지 퀄리티도 올라감)
    thumbnail_url = None
    try:
        thumbnail_prompt = f"""
Create a professional educational course thumbnail image.
Course title: "{title}"
Category: {category}
Topic: {topic}
Requirements: High quality, 16:9 aspect ratio, No text.
"""
        thumbnail_url = generate_image(thumbnail_prompt)
    except Exception as e:
        print(f"썸네일 오류: {e}")
        thumbnail_url = None

    return {
        "title": title,
        "category": category,  # 이제 항상 정해진 값 중 하나가 나옴
        "description": description,
        "curriculum": curriculum,
        "thumbnail_url": thumbnail_url
    }


async def generate_course_content(title: str, category: str) -> dict:
    """강의 콘텐츠 전체 생성 (설명, 커리큘럼, 썸네일)"""
    
    # 카테고리 검증 (기존 강의 업데이트 시에도 적용)
    if category not in VALID_CATEGORIES:
        category = "기타"
    
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
