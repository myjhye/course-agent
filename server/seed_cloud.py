# server/seed_cloud.py
"""
Railway 클라우드 DB에 초기 데이터를 삽입하는 스크립트입니다.

실행 전 체크리스트:
1. .env 파일의 DATABASE_URL이 Railway PostgreSQL 주소로 설정되어 있어야 합니다.
   예: postgresql+asyncpg://postgres:xxxxx@xxx.railway.app:5432/railway
2. 가상환경이 활성화되어 있어야 합니다.

실행 방법:
   cd server
   python seed_cloud.py
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일을 강제로 로드합니다.
load_dotenv()

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import AsyncSessionLocal, engine, Base
from app.models.instructor import Instructor
from app.models.lesson import Lesson, SportType, TargetAudience, Difficulty, LessonStatus
from app.models.lesson_content import LessonContent
from app.models.faq import FAQ
from app.services.ai.llm_client import generate_image
from sqlalchemy import text


# ===== 강사 데이터 =====
INSTRUCTORS = [
    {"name": "김수영", "specialty": "swimming", "bio": "전 국가대표 수영선수, 10년 강습 경력"},
    {"name": "박테니", "specialty": "tennis", "bio": "ATP 투어 경험, 주니어 전문 코치"},
    {"name": "이골프", "specialty": "golf", "bio": "KPGA 프로, 기업 레슨 전문"},
    {"name": "최피트", "specialty": "fitness", "bio": "생활체육지도사 1급, 체형교정 전문"},
    {"name": "정요가", "specialty": "yoga", "bio": "인도 요가 자격증, 명상 지도"},
    {"name": "한필라", "specialty": "pilates", "bio": "재활 필라테스 전문, 물리치료사 출신"},
]

# ===== FAQ 데이터 =====
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

# ===== 강습 데이터 (콘텐츠 포함) =====
LESSONS = [
    {
        "title": "왕초보 자유형 마스터 클래스",
        "sport_type": SportType.SWIMMING,
        "target_audience": TargetAudience.ADULT,
        "difficulty": Difficulty.BEGINNER,
        "status": LessonStatus.PUBLISHED,
        "instructor_idx": 0,  # 김수영
        "content": {
            "introduction": "물이 무서웠던 분들도 4주 만에 자유형 25m 완주! 국가대표 출신 코치의 체계적인 커리큘럼으로 수영의 기초부터 탄탄하게 배워보세요.",
            "curriculum": {
                "weeks": [
                    {"week": 1, "title": "물 적응 & 호흡법", "topics": ["물에 뜨기", "기본 호흡법", "발차기 기초"]},
                    {"week": 2, "title": "킥 동작 마스터", "topics": ["자유형 킥", "벽 잡고 연습", "거리 늘리기"]},
                    {"week": 3, "title": "팔 동작 & 콤비네이션", "topics": ["팔 돌리기", "팔+발 조합", "호흡 타이밍"]},
                    {"week": 4, "title": "25m 완주 도전", "topics": ["지구력 훈련", "폼 교정", "실전 연습"]}
                ]
            }
        }
    },
    {
        "title": "테니스 입문: 라켓 잡는 법부터",
        "sport_type": SportType.TENNIS,
        "target_audience": TargetAudience.ADULT,
        "difficulty": Difficulty.BEGINNER,
        "status": LessonStatus.PUBLISHED,
        "instructor_idx": 1,  # 박테니
        "content": {
            "introduction": "테니스를 처음 시작하는 분들을 위한 완벽 입문 코스! 그립부터 서브까지, ATP 투어 경험 코치가 기초를 확실하게 잡아드립니다.",
            "curriculum": {
                "weeks": [
                    {"week": 1, "title": "장비 & 그립", "topics": ["라켓 선택법", "그립 종류", "기본 자세"]},
                    {"week": 2, "title": "포핸드 스트로크", "topics": ["스윙 궤도", "타점", "팔로우 스루"]},
                    {"week": 3, "title": "백핸드 & 발리", "topics": ["원핸드/투핸드", "네트 플레이", "포지셔닝"]},
                    {"week": 4, "title": "서브 & 게임", "topics": ["토스 연습", "서브 동작", "미니 게임"]}
                ]
            }
        }
    },
    {
        "title": "골프 스윙 기초 완성",
        "sport_type": SportType.GOLF,
        "target_audience": TargetAudience.ADULT,
        "difficulty": Difficulty.BEGINNER,
        "status": LessonStatus.PUBLISHED,
        "instructor_idx": 2,  # 이골프
        "content": {
            "introduction": "KPGA 프로와 함께하는 골프 입문! 어드레스부터 풀스윙까지, 올바른 기본기로 시작하세요. 장비 선택 팁도 드려요!",
            "curriculum": {
                "weeks": [
                    {"week": 1, "title": "그립 & 어드레스", "topics": ["그립 잡는 법", "스탠스", "정렬"]},
                    {"week": 2, "title": "하프스윙", "topics": ["백스윙", "다운스윙", "임팩트"]},
                    {"week": 3, "title": "풀스윙", "topics": ["탑 포지션", "체중이동", "피니시"]},
                    {"week": 4, "title": "숏게임 기초", "topics": ["퍼팅", "칩샷", "코스 매너"]}
                ]
            }
        }
    },
    {
        "title": "홈트 피트니스: 맨몸 운동의 정석",
        "sport_type": SportType.FITNESS,
        "target_audience": TargetAudience.ALL,
        "difficulty": Difficulty.BEGINNER,
        "status": LessonStatus.PUBLISHED,
        "instructor_idx": 3,  # 최피트
        "content": {
            "introduction": "헬스장 없이 집에서 완성하는 탄탄한 몸! 푸시업, 스쿼트, 플랭크 등 맨몸 운동으로 기초 체력을 키워보세요.",
            "curriculum": {
                "weeks": [
                    {"week": 1, "title": "웜업 & 스트레칭", "topics": ["동적 스트레칭", "관절 풀기", "부상 예방"]},
                    {"week": 2, "title": "상체 운동", "topics": ["푸시업 변형", "딥스", "플랭크"]},
                    {"week": 3, "title": "하체 운동", "topics": ["스쿼트", "런지", "힙 브릿지"]},
                    {"week": 4, "title": "전신 루틴", "topics": ["버피", "마운틴 클라이머", "루틴 구성"]}
                ]
            }
        }
    },
    {
        "title": "아침 요가: 하루를 여는 30분",
        "sport_type": SportType.YOGA,
        "target_audience": TargetAudience.ALL,
        "difficulty": Difficulty.BEGINNER,
        "status": LessonStatus.PUBLISHED,
        "instructor_idx": 4,  # 정요가
        "content": {
            "introduction": "인도 요가 자격증 보유 강사와 함께하는 모닝 요가! 30분으로 몸과 마음을 깨우고, 하루를 활기차게 시작하세요.",
            "curriculum": {
                "weeks": [
                    {"week": 1, "title": "호흡 & 명상", "topics": ["복식호흡", "마음 비우기", "집중력"]},
                    {"week": 2, "title": "기본 아사나", "topics": ["태양경배", "전사자세", "나무자세"]},
                    {"week": 3, "title": "유연성 향상", "topics": ["전굴", "비틀기", "고관절 열기"]},
                    {"week": 4, "title": "밸런스 & 명상", "topics": ["균형 자세", "마무리 명상", "루틴 완성"]}
                ]
            }
        }
    },
    {
        "title": "코어 필라테스: 탄탄한 중심 만들기",
        "sport_type": SportType.PILATES,
        "target_audience": TargetAudience.ADULT,
        "difficulty": Difficulty.ELEMENTARY,
        "status": LessonStatus.PUBLISHED,
        "instructor_idx": 5,  # 한필라
        "content": {
            "introduction": "재활 전문 필라테스 강사와 함께 코어를 단련하세요! 자세 교정과 허리 건강에 효과적인 동작들을 배워봅니다.",
            "curriculum": {
                "weeks": [
                    {"week": 1, "title": "필라테스 원리", "topics": ["호흡법", "중립 척추", "코어 인지"]},
                    {"week": 2, "title": "기본 매트 동작", "topics": ["헌드레드", "롤업", "싱글레그"]},
                    {"week": 3, "title": "중급 동작", "topics": ["더블레그", "크리스크로스", "사이드킥"]},
                    {"week": 4, "title": "플로우 & 응용", "topics": ["동작 연결", "밸런스", "홈 루틴"]}
                ]
            }
        }
    },
    {
        "title": "중급 테니스: 스핀과 전술",
        "sport_type": SportType.TENNIS,
        "target_audience": TargetAudience.ADULT,
        "difficulty": Difficulty.INTERMEDIATE,
        "status": LessonStatus.PUBLISHED,
        "instructor_idx": 1,  # 박테니
        "content": {
            "introduction": "기본기를 마스터한 분들을 위한 중급 과정! 톱스핀, 슬라이스 등 다양한 구질과 실전 전술을 배워봅니다.",
            "curriculum": {
                "weeks": [
                    {"week": 1, "title": "톱스핀 마스터", "topics": ["라켓 헤드 스피드", "각도 조절", "높은 바운스"]},
                    {"week": 2, "title": "슬라이스 & 드롭샷", "topics": ["백스핀", "언더스핀", "터치"]},
                    {"week": 3, "title": "전술 & 포지셔닝", "topics": ["코트 커버리지", "상대 분석", "약점 공략"]},
                    {"week": 4, "title": "경기 운영", "topics": ["세트 전략", "멘탈 관리", "실전 매치"]}
                ]
            }
        }
    },
    {
        "title": "키즈 수영: 물놀이가 재밌어요!",
        "sport_type": SportType.SWIMMING,
        "target_audience": TargetAudience.CHILD,
        "difficulty": Difficulty.BEGINNER,
        "status": LessonStatus.PUBLISHED,
        "instructor_idx": 0,  # 김수영
        "content": {
            "introduction": "아이들 눈높이에 맞춘 재미있는 수영 교실! 물에 대한 두려움을 없애고, 놀이처럼 수영을 배워요.",
            "curriculum": {
                "weeks": [
                    {"week": 1, "title": "물과 친해지기", "topics": ["얼굴 담그기", "물 뿌리기", "뜨기"]},
                    {"week": 2, "title": "발차기 놀이", "topics": ["킥보드 잡고", "개구리 발차기", "물놀이"]},
                    {"week": 3, "title": "팔 동작 배우기", "topics": ["물 젓기", "강아지 수영", "조합 연습"]},
                    {"week": 4, "title": "5m 도전!", "topics": ["짧은 거리", "뜨기 유지", "자신감 UP"]}
                ]
            }
        }
    },
]


async def check_connection():
    """DB 연결 확인"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("SELECT 1"))
            print("✅ Railway DB 연결 성공!")
            return True
        except Exception as e:
            print(f"❌ DB 연결 실패: {e}")
            return False


async def seed():
    """초기 데이터 삽입"""
    print("🚀 Railway DB 시딩 시작...")
    print("-" * 50)
    
    # 연결 확인
    if not await check_connection():
        return
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. 강사 추가
            print("\n📌 강사 데이터 삽입 중...")
            instructors = []
            for data in INSTRUCTORS:
                instructor = Instructor(**data)
                db.add(instructor)
                instructors.append(instructor)
            await db.flush()  # ID 생성을 위해 flush
            print(f"   ✅ {len(instructors)}명의 강사 추가 완료")
            
            # 2. FAQ 추가
            print("\n📌 FAQ 데이터 삽입 중...")
            for data in FAQS:
                faq = FAQ(**data)
                db.add(faq)
            print(f"   ✅ {len(FAQS)}개의 FAQ 추가 완료")
            
            # 3. 강습 + 콘텐츠 추가 (썸네일 AI 생성 포함)
            print("\n📌 강습 데이터 삽입 중...")
            for lesson_data in LESSONS:
                content_data = lesson_data.pop("content")
                instructor_idx = lesson_data.pop("instructor_idx")
                
                # 강습 생성
                lesson = Lesson(
                    **lesson_data,
                    instructor_id=instructors[instructor_idx].id
                )
                db.add(lesson)
                await db.flush()  # lesson.id 생성
                
                # 🎨 썸네일 AI 생성
                print(f"   🎨 '{lesson.title}' 썸네일 생성 중...")
                try:
                    generated_url = generate_image(f"{lesson.title} sports lesson thumbnail, professional, vibrant colors")
                except Exception as e:
                    print(f"      ⚠️ 썸네일 생성 실패: {e}")
                    generated_url = None
                
                # 콘텐츠 생성 (생성된 URL 주입)
                content = LessonContent(
                    lesson_id=lesson.id,
                    introduction=content_data["introduction"],
                    curriculum=content_data["curriculum"],
                    thumbnail_url=generated_url,  # AI 생성된 URL 사용
                    version=1,
                    is_active=True
                )
                db.add(content)
                print(f"   ✅ '{lesson.title}' 추가 완료")
            
            # 커밋
            await db.commit()
            
            print("\n" + "=" * 50)
            print("🎉 모든 시드 데이터 삽입 완료!")
            print(f"   - 강사: {len(INSTRUCTORS)}명")
            print(f"   - FAQ: {len(FAQS)}개")
            print(f"   - 강습: {len(LESSONS)}개")
            print("=" * 50)
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ 에러 발생: {e}")
            raise


async def clear_all():
    """모든 데이터 삭제 (주의: 위험!)"""
    print("⚠️  모든 데이터를 삭제합니다...")
    
    async with AsyncSessionLocal() as db:
        try:
            # 순서 중요: 외래키 의존성 고려
            await db.execute(text("DELETE FROM lesson_contents"))
            await db.execute(text("DELETE FROM enrollments"))
            await db.execute(text("DELETE FROM lessons"))
            await db.execute(text("DELETE FROM instructors"))
            await db.execute(text("DELETE FROM faqs"))
            await db.commit()
            print("✅ 모든 데이터 삭제 완료")
        except Exception as e:
            await db.rollback()
            print(f"❌ 삭제 실패: {e}")


async def main():
    """메인 실행 흐름 제어 - 하나의 이벤트 루프에서 모든 작업 실행"""
    args = sys.argv[1:]
    
    if "--clear" in args:
        # 데이터 초기화 후 시딩
        await clear_all()
        await seed()
    elif "--clear-only" in args:
        # 데이터 초기화만
        await clear_all()
    else:
        # 기본: 시딩만
        await seed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 실행 중 에러 발생: {e}")

