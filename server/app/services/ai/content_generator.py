import json
import uuid
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.lesson import Lesson
from app.models.lesson_content import LessonContent
from app.models.ai_log import AILog
from app.services.ai.llm_client import get_openai_client, generate_image


class ContentGenerator:
    
    @staticmethod
    async def generate_full_content(db: AsyncSession, lesson: Lesson) -> LessonContent:
        """전체 콘텐츠 생성 (소개 + 커리큘럼 + 썸네일)"""
        
        start_time = time.time()
        
        # 1. 소개 문구 생성
        introduction = await ContentGenerator._generate_introduction(lesson)
        
        # 2. 커리큘럼 생성
        curriculum = await ContentGenerator._generate_curriculum(lesson)
        
        # 3. 썸네일 생성
        thumbnail_url = await ContentGenerator._generate_thumbnail(lesson)
        
        # 4. 버전 계산
        result = await db.execute(
            select(LessonContent)
            .where(LessonContent.lesson_id == lesson.id)
            .order_by(LessonContent.version.desc())
        )
        existing = result.scalars().first()
        new_version = (existing.version + 1) if existing else 1
        
        # 5. 기존 콘텐츠 비활성화
        if existing:
            all_contents = await db.execute(
                select(LessonContent).where(LessonContent.lesson_id == lesson.id)
            )
            for content in all_contents.scalars().all():
                content.is_active = False
        
        # 6. 새 콘텐츠 저장
        content = LessonContent(
            lesson_id=lesson.id,
            introduction=introduction,
            curriculum=curriculum,
            thumbnail_url=thumbnail_url,
            version=new_version,
            is_active=True
        )
        db.add(content)
        
        # 7. AI 로그
        latency_ms = (time.time() - start_time) * 1000
        ai_log = AILog(
            feature_type="content",
            lesson_id=lesson.id,
            input_data={"title": lesson.title, "action": "full"},
            output_data={"version": new_version},
            latency_ms=latency_ms
        )
        db.add(ai_log)
        
        await db.commit()
        await db.refresh(content)
        
        return content
    
    @staticmethod
    async def regenerate_introduction(db: AsyncSession, lesson: Lesson, content_id: int) -> LessonContent:
        """소개 문구만 재생성"""
        
        result = await db.execute(
            select(LessonContent).where(LessonContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        
        if not content:
            raise ValueError("Content not found")
        
        introduction = await ContentGenerator._generate_introduction(lesson)
        content.introduction = introduction
        
        # AI 로그
        ai_log = AILog(
            feature_type="content",
            lesson_id=lesson.id,
            input_data={"title": lesson.title, "action": "regenerate_introduction"},
            output_data={"introduction_length": len(introduction)}
        )
        db.add(ai_log)
        
        await db.commit()
        await db.refresh(content)
        
        return content
    
    @staticmethod
    async def regenerate_curriculum(db: AsyncSession, lesson: Lesson, content_id: int) -> LessonContent:
        """커리큘럼만 재생성"""
        
        result = await db.execute(
            select(LessonContent).where(LessonContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        
        if not content:
            raise ValueError("Content not found")
        
        curriculum = await ContentGenerator._generate_curriculum(lesson)
        content.curriculum = curriculum
        
        # AI 로그
        ai_log = AILog(
            feature_type="content",
            lesson_id=lesson.id,
            input_data={"title": lesson.title, "action": "regenerate_curriculum"},
            output_data={"weeks_count": len(curriculum.get("weeks", []))}
        )
        db.add(ai_log)
        
        await db.commit()
        await db.refresh(content)
        
        return content
    
    @staticmethod
    async def regenerate_thumbnail(db: AsyncSession, lesson: Lesson, content_id: int) -> LessonContent:
        """썸네일만 재생성"""
        
        result = await db.execute(
            select(LessonContent).where(LessonContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        
        if not content:
            raise ValueError("Content not found")
        
        thumbnail_url = await ContentGenerator._generate_thumbnail(lesson)
        content.thumbnail_url = thumbnail_url
        
        # AI 로그
        ai_log = AILog(
            feature_type="content",
            lesson_id=lesson.id,
            input_data={"title": lesson.title, "action": "regenerate_thumbnail"},
            output_data={"thumbnail_url": thumbnail_url}
        )
        db.add(ai_log)
        
        await db.commit()
        await db.refresh(content)
        
        return content
    
    @staticmethod
    async def _generate_introduction(lesson: Lesson) -> str:
        """소개 문구 생성"""
        
        client = get_openai_client()
        
        target_labels = {
            "adult": "성인",
            "child": "어린이",
            "senior": "시니어",
            "all": "전체"
        }
        difficulty_labels = {
            "beginner": "입문",
            "elementary": "초급",
            "intermediate": "중급",
            "advanced": "고급"
        }
        sport_labels = {
            "swimming": "수영",
            "tennis": "테니스",
            "golf": "골프",
            "fitness": "피트니스",
            "yoga": "요가",
            "pilates": "필라테스"
        }
        
        target = target_labels.get(lesson.target_audience.value, lesson.target_audience.value)
        difficulty = difficulty_labels.get(lesson.difficulty.value, lesson.difficulty.value)
        sport = sport_labels.get(lesson.sport_type.value, lesson.sport_type.value)
        
        prompt = f"""다음 강습의 소개 문구를 작성해주세요.

강습명: {lesson.title}
종목: {sport}
대상: {target}
난이도: {difficulty}
강사: {lesson.instructor.name if lesson.instructor else "미정"}

요청사항:
- 3~4문장으로 작성
- 대상({target})에 맞는 톤 사용
- 이 강습을 통해 얻을 수 있는 것 강조
- 친근하고 격려하는 톤
- 마크다운이나 특수문자 없이 순수 텍스트로만"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 스포츠 강습 플랫폼의 카피라이터입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"소개 문구 생성 실패: {e}")
            return f"{lesson.title}에 오신 것을 환영합니다!"
    
    @staticmethod
    async def _generate_curriculum(lesson: Lesson) -> dict:
        """커리큘럼 생성 (4~8주차)"""
        
        client = get_openai_client()
        
        # 난이도별 주차 수
        weeks_by_difficulty = {
            "beginner": 4,
            "elementary": 6,
            "intermediate": 8,
            "advanced": 8
        }
        num_weeks = weeks_by_difficulty.get(lesson.difficulty.value, 4)
        
        target_labels = {
            "adult": "성인",
            "child": "어린이",
            "senior": "시니어",
            "all": "전체"
        }
        sport_labels = {
            "swimming": "수영",
            "tennis": "테니스",
            "golf": "골프",
            "fitness": "피트니스",
            "yoga": "요가",
            "pilates": "필라테스"
        }
        
        target = target_labels.get(lesson.target_audience.value, lesson.target_audience.value)
        sport = sport_labels.get(lesson.sport_type.value, lesson.sport_type.value)
        
        prompt = f"""다음 강습의 {num_weeks}주차 커리큘럼을 작성해주세요.

강습명: {lesson.title}
종목: {sport}
대상: {target}
난이도: {lesson.difficulty.value}

요청사항:
- 총 {num_weeks}주차 커리큘럼
- 각 주차별로 제목(title)과 세부 주제(topics) 3~4개 작성
- 점진적으로 난이도가 올라가도록 구성
- 마지막 주차는 종합/실전 내용으로
- 대상({target})에 맞는 내용과 용어 사용

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "weeks": [
    {{
      "week": 1,
      "title": "주차 제목",
      "topics": ["주제1", "주제2", "주제3"]
    }},
    {{
      "week": 2,
      "title": "주차 제목",
      "topics": ["주제1", "주제2", "주제3"]
    }}
  ]
}}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 스포츠 강습 커리큘럼 전문가입니다. JSON 형식으로만 응답합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            result_text = response.choices[0].message.content
            
            # JSON 파싱
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(result_text[start:end])
            
        except Exception as e:
            print(f"커리큘럼 생성 실패: {e}")
        
        # 실패 시 기본 커리큘럼
        return {
            "weeks": [
                {"week": i, "title": f"{i}주차", "topics": ["기초 동작", "연습", "복습"]}
                for i in range(1, num_weeks + 1)
            ]
        }
    
    @staticmethod
    async def _generate_thumbnail(lesson: Lesson) -> str:
        """썸네일 생성"""
        try:
            thumbnail_prompt = f"""
Create a professional sports lesson thumbnail image.
Lesson title: "{lesson.title}"
Sport type: {lesson.sport_type.value}
Target: {lesson.target_audience.value}
Difficulty: {lesson.difficulty.value}
Requirements: High quality, 16:9 aspect ratio, No text.
"""
            return generate_image(thumbnail_prompt)
        except Exception as e:
            print(f"썸네일 생성 실패: {e}")
            return None


# 기존 함수들 호환성 유지
async def generate_lesson_content(db, lesson) -> LessonContent:
    """강습 콘텐츠 생성 (기존 호환성)"""
    return await ContentGenerator.generate_full_content(db, lesson)
