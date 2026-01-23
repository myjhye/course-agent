import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import AsyncSessionLocal
from app.models.instructor import Instructor
from app.models.faq import FAQ


INSTRUCTORS = [
    {"name": "김수영", "specialty": "swimming", "bio": "전 국가대표 수영선수, 10년 강습 경력"},
    {"name": "박테니", "specialty": "tennis", "bio": "ATP 투어 경험, 주니어 전문 코치"},
    {"name": "이골프", "specialty": "golf", "bio": "KPGA 프로, 기업 레슨 전문"},
    {"name": "최피트", "specialty": "fitness", "bio": "생활체육지도사 1급, 체형교정 전문"},
    {"name": "정요가", "specialty": "yoga", "bio": "인도 요가 자격증, 명상 지도"},
]

FAQS = [
    {
        "category": "payment",
        "question": "결제 방법은 무엇이 있나요?",
        "answer": "신용카드, 체크카드, 카카오페이, 네이버페이를 지원합니다.",
        "keywords": "결제 방법 카드 페이"
    },
    {
        "category": "refund",
        "question": "환불은 어떻게 하나요?",
        "answer": "수강 시작 후 7일 이내, 진도율 10% 미만인 경우 전액 환불 가능합니다. 마이페이지에서 환불 신청하세요.",
        "keywords": "환불 취소 반환"
    },
    {
        "category": "refund",
        "question": "환불은 언제 되나요?",
        "answer": "환불 신청 후 영업일 기준 3~5일 내에 처리됩니다.",
        "keywords": "환불 기간 시간"
    },
    {
        "category": "usage",
        "question": "수강 기간은 얼마인가요?",
        "answer": "강습마다 다르지만, 대부분 등록일로부터 3개월간 수강 가능합니다.",
        "keywords": "수강 기간 기한"
    },
    {
        "category": "usage",
        "question": "강습 장소는 어디인가요?",
        "answer": "각 강습 상세 페이지에서 장소를 확인할 수 있습니다. 대부분 서울/경기 지역입니다.",
        "keywords": "장소 위치 어디"
    },
    {
        "category": "certificate",
        "question": "수료증은 어떻게 받나요?",
        "answer": "강습 완료 후 마이페이지에서 수료증을 다운로드할 수 있습니다.",
        "keywords": "수료증 인증서 완료"
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        # 강사 추가
        for data in INSTRUCTORS:
            instructor = Instructor(**data)
            db.add(instructor)
        
        # FAQ 추가
        for data in FAQS:
            faq = FAQ(**data)
            db.add(faq)
        
        await db.commit()
        print(f"✅ Seeded {len(INSTRUCTORS)} instructors")
        print(f"✅ Seeded {len(FAQS)} FAQs")


if __name__ == "__main__":
    asyncio.run(seed())

