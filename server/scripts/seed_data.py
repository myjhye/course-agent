import asyncio
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import AsyncSessionLocal
from app.models.instructor import Instructor
from app.models.lesson import Lesson, SportType, TargetAudience, Difficulty, LessonStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.lesson_interest import LessonView, LessonLike
from app.models.faq import FAQ


# ============================================================
# 1. 강사 데이터 (15명)
# ============================================================
INSTRUCTORS = [
    # 수영
    {"name": "김수영", "specialty": "swimming", "bio": "전 국가대표 수영선수 출신으로 10년간 수영 강습 경력을 보유하고 있습니다. 자유형과 배영을 전문으로 지도하며, 입문자부터 선수반까지 폭넓게 가르치고 있습니다."},
    {"name": "이해수", "specialty": "swimming", "bio": "수상안전강사 자격을 보유한 유아/어린이 수영 전문 코치입니다. 7년간 아이들의 물 공포를 없애고 수영의 즐거움을 알려주는 데 전념하고 있습니다."},
    # 테니스
    {"name": "박테니", "specialty": "tennis", "bio": "ATP 투어 참가 경험이 있는 테니스 전문 코치입니다. 12년간 주니어부터 동호인까지 체계적인 레슨을 제공하며, 특히 서브와 리턴 전략 지도에 강점이 있습니다."},
    # 골프
    {"name": "이골프", "specialty": "golf", "bio": "KPGA 프로 자격을 갖춘 골프 레슨 전문가입니다. 15년간 기업 임원 레슨과 입문자 지도를 병행하며, 스윙 교정에 탁월한 능력을 인정받고 있습니다."},
    {"name": "한그린", "specialty": "golf", "bio": "KLPGA 출신으로 여성 입문자 전문 골프 코치입니다. 8년간 골프의 진입장벽을 낮추는 친근한 레슨 스타일로 인기를 얻고 있습니다."},
    # 피트니스
    {"name": "최피트", "specialty": "fitness", "bio": "생활체육지도사 1급 자격의 체형교정 전문 트레이너입니다. 9년간 거북목, 라운드숄더 등 현대인의 체형 문제를 운동으로 해결하는 데 집중하고 있습니다."},
    {"name": "강체력", "specialty": "fitness", "bio": "크로스핏 Level 2 트레이너로 기능성 체력 훈련 전문가입니다. 6년간 고강도 인터벌 트레이닝과 체력 극대화 프로그램을 지도하고 있습니다."},
    # 요가
    {"name": "정요가", "specialty": "yoga", "bio": "인도 리시케시에서 RYT-500 자격을 취득한 요가 지도자입니다. 11년간 하타요가와 빈야사를 지도하며, 호흡과 명상을 통한 심신 안정에 중점을 두고 있습니다."},
    # 필라테스
    {"name": "민코어", "specialty": "pilates", "bio": "물리치료사 출신의 재활 필라테스 전문가입니다. 7년간 디스크, 관절 환자의 재활 운동을 지도하며, 매트와 기구 필라테스 모두 전문적으로 가르치고 있습니다."},
    {"name": "서유연", "specialty": "pilates", "bio": "대한필라테스협회 공인 강사로 산전/산후 필라테스 전문가입니다. 5년간 여성의 라이프사이클에 맞춘 맞춤형 프로그램을 운영하고 있습니다."},
    # OTHER 종목 (배드민턴, 농구, 축구, 클라이밍, 탁구, 댄스)
    {"name": "강셔틀", "specialty": "badminton", "bio": "전 실업팀 배드민턴 선수 출신으로 8년간 동호회 및 입문자 레슨을 진행하고 있습니다. 클리어, 드롭, 스매시 등 기본기부터 복식 전략까지 지도합니다."},
    {"name": "윤바스켓", "specialty": "basketball", "bio": "전 KBL 프로농구 선수 출신으로 6년간 유소년 농구 캠프를 운영하고 있습니다. 드리블, 패스, 슈팅 기초와 팀플레이를 중점적으로 가르칩니다."},
    {"name": "손킥", "specialty": "soccer", "bio": "AFC C급 지도자 자격의 축구/풋살 겸임 코치입니다. 10년간 유소년부터 성인 동호회까지 폭넓게 지도하며, 기초 패스와 전술 이해를 중시합니다."},
    {"name": "오벽", "specialty": "climbing", "bio": "볼더링 전문 클라이밍 코치로 실내 클라이밍장 5년 운영 경험이 있습니다. 입문자의 안전 교육과 기초 무브먼트 지도를 전문으로 합니다."},
    {"name": "류비트", "specialty": "dance", "bio": "K-POP 안무가 출신의 방송댄스/힙합 전문 강사입니다. 6년간 최신 K-POP 안무와 힙합 기본기를 가르치며, 즐겁게 배우는 댄스를 추구합니다."},
]


# ============================================================
# 2. 강습 데이터
# ============================================================
LESSON_TEMPLATES = [
    # ---- 수영 (swimming) ----
    {"sport_type": SportType.SWIMMING, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.CHILD,
     "title": "어린이 첫 수영교실", "instructor_name": "이해수"},
    {"sport_type": SportType.SWIMMING, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "성인 왕초보 수영", "instructor_name": "김수영"},
    {"sport_type": SportType.SWIMMING, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.ADULT,
     "title": "자유형 마스터 과정", "instructor_name": "김수영"},
    {"sport_type": SportType.SWIMMING, "difficulty": Difficulty.INTERMEDIATE, "target_audience": TargetAudience.ADULT,
     "title": "4영법 완성반", "instructor_name": "김수영"},
    {"sport_type": SportType.SWIMMING, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.SENIOR,
     "title": "시니어 아쿠아로빅", "instructor_name": "이해수"},
    {"sport_type": SportType.SWIMMING, "difficulty": Difficulty.ADVANCED, "target_audience": TargetAudience.ADULT,
     "title": "마스터즈 수영 도전반", "instructor_name": "김수영"},

    # ---- 테니스 (tennis) ----
    {"sport_type": SportType.TENNIS, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "테니스 A to Z", "instructor_name": "박테니"},
    {"sport_type": SportType.TENNIS, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.CHILD,
     "title": "주니어 테니스 아카데미", "instructor_name": "박테니"},
    {"sport_type": SportType.TENNIS, "difficulty": Difficulty.INTERMEDIATE, "target_audience": TargetAudience.ADULT,
     "title": "동호인 실전 매치 클래스", "instructor_name": "박테니"},
    {"sport_type": SportType.TENNIS, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.SENIOR,
     "title": "시니어 테니스 건강교실", "instructor_name": "박테니"},

    # ---- 골프 (golf) ----
    {"sport_type": SportType.GOLF, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "골프 입문 100타 깨기", "instructor_name": "이골프"},
    {"sport_type": SportType.GOLF, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.ADULT,
     "title": "숏게임 집중 클리닉", "instructor_name": "한그린"},
    {"sport_type": SportType.GOLF, "difficulty": Difficulty.INTERMEDIATE, "target_audience": TargetAudience.ADULT,
     "title": "싱글 도전 라운드 레슨", "instructor_name": "이골프"},
    {"sport_type": SportType.GOLF, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "여성 전용 골프 입문", "instructor_name": "한그린"},

    # ---- 피트니스 (fitness) ----
    {"sport_type": SportType.FITNESS, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "헬스 기초 3대 운동", "instructor_name": "최피트"},
    {"sport_type": SportType.FITNESS, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.ADULT,
     "title": "체형교정 퍼스널 트레이닝", "instructor_name": "최피트"},
    {"sport_type": SportType.FITNESS, "difficulty": Difficulty.INTERMEDIATE, "target_audience": TargetAudience.ADULT,
     "title": "크로스핏 챌린지", "instructor_name": "강체력"},
    {"sport_type": SportType.FITNESS, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.SENIOR,
     "title": "시니어 근력 강화 프로그램", "instructor_name": "최피트"},
    {"sport_type": SportType.FITNESS, "difficulty": Difficulty.ADVANCED, "target_audience": TargetAudience.ADULT,
     "title": "바디프로필 챌린지 12주", "instructor_name": "강체력"},

    # ---- 요가 (yoga) ----
    {"sport_type": SportType.YOGA, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "하타요가 입문", "instructor_name": "정요가"},
    {"sport_type": SportType.YOGA, "difficulty": Difficulty.INTERMEDIATE, "target_audience": TargetAudience.ADULT,
     "title": "빈야사 플로우", "instructor_name": "정요가"},
    {"sport_type": SportType.YOGA, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.SENIOR,
     "title": "시니어 체어 요가", "instructor_name": "정요가"},
    {"sport_type": SportType.YOGA, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.ADULT,
     "title": "아침 명상 요가", "instructor_name": "정요가"},

    # ---- 필라테스 (pilates) ----
    {"sport_type": SportType.PILATES, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "매트 필라테스 기초", "instructor_name": "민코어"},
    {"sport_type": SportType.PILATES, "difficulty": Difficulty.INTERMEDIATE, "target_audience": TargetAudience.ADULT,
     "title": "기구 필라테스 중급", "instructor_name": "민코어"},
    {"sport_type": SportType.PILATES, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "산전산후 필라테스", "instructor_name": "서유연"},
    {"sport_type": SportType.PILATES, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.ADULT,
     "title": "코어 강화 필라테스", "instructor_name": "서유연"},

    # ---- OTHER 종목들 (배드민턴, 농구, 축구, 클라이밍, 댄스) ----
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "배드민턴 왕초보 탈출", "instructor_name": "강셔틀"},
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.INTERMEDIATE, "target_audience": TargetAudience.ADULT,
     "title": "배드민턴 복식 전략반", "instructor_name": "강셔틀"},
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.CHILD,
     "title": "청소년 농구 캠프", "instructor_name": "윤바스켓"},
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.ADULT,
     "title": "성인 농구 동호회 입문", "instructor_name": "윤바스켓"},
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.CHILD,
     "title": "어린이 축구교실", "instructor_name": "손킥"},
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.ADULT,
     "title": "주말 풋살 스킬업", "instructor_name": "손킥"},
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "실내 볼더링 입문", "instructor_name": "오벽"},
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.BEGINNER, "target_audience": TargetAudience.ADULT,
     "title": "K-POP 댄스 입문", "instructor_name": "류비트"},
    {"sport_type": SportType.OTHER, "difficulty": Difficulty.ELEMENTARY, "target_audience": TargetAudience.CHILD,
     "title": "청소년 힙합 댄스", "instructor_name": "류비트"},
]


# ============================================================
# 3. FAQ 데이터
# ============================================================
FAQS = [
    # ---- 결제/환불 ----
    {"category": "payment", "question": "결제 방법은 무엇이 있나요?",
     "answer": "신용카드, 체크카드, 카카오페이, 네이버페이를 지원합니다.",
     "keywords": "결제 방법 카드 페이"},
    {"category": "payment", "question": "할인이나 프로모션이 있나요?",
     "answer": "매월 첫째 주 신규 가입자 10% 할인, 2개 이상 강습 동시 등록 시 5% 추가 할인이 적용됩니다.",
     "keywords": "할인 프로모션 쿠폰 이벤트"},
    {"category": "payment", "question": "분할 결제가 가능한가요?",
     "answer": "3개월 이상 장기 과정의 경우 2~3회 분할 결제가 가능합니다. 결제 시 분할 옵션을 선택해주세요.",
     "keywords": "분할 결제 할부 나눠"},
    {"category": "refund", "question": "환불은 어떻게 하나요?",
     "answer": "수강 시작 후 7일 이내, 진도율 10% 미만인 경우 전액 환불 가능합니다. 마이페이지에서 환불 신청하세요.",
     "keywords": "환불 취소 반환"},
    {"category": "refund", "question": "환불 처리 기간은 얼마나 걸리나요?",
     "answer": "환불 신청 후 영업일 기준 3~5일 내에 원래 결제 수단으로 환불됩니다.",
     "keywords": "환불 기간 시간 처리"},
    {"category": "refund", "question": "수강 시작 후 부분 환불이 가능한가요?",
     "answer": "전체 과정의 1/3 경과 전에는 수강료의 2/3를, 1/2 경과 전에는 1/2를 환불받을 수 있습니다. 1/2 경과 후에는 환불이 불가합니다.",
     "keywords": "부분 환불 중도 해지 취소"},

    # ---- 수강 관련 ----
    {"category": "enrollment", "question": "수강 기간은 얼마인가요?",
     "answer": "강습마다 다르지만, 대부분 4주~12주 과정입니다. 각 강습 상세 페이지에서 확인할 수 있습니다.",
     "keywords": "수강 기간 기한 얼마나"},
    {"category": "enrollment", "question": "수강 인원이 꽉 차면 어떻게 하나요?",
     "answer": "대기 신청을 걸어두시면 자리가 나는 즉시 알림을 보내드립니다.",
     "keywords": "정원 마감 대기 인원"},
    {"category": "enrollment", "question": "강습 장소는 어디인가요?",
     "answer": "각 강습 상세 페이지에서 장소를 확인할 수 있습니다. 서울/경기 지역에서 주로 운영됩니다.",
     "keywords": "장소 위치 어디 주소"},
    {"category": "enrollment", "question": "다른 강습으로 변경할 수 있나요?",
     "answer": "강습 시작 전이라면 마이페이지에서 변경 가능합니다. 시작 후에는 고객센터로 문의해주세요.",
     "keywords": "변경 전환 다른 강습"},
    {"category": "enrollment", "question": "결석하면 보강이 되나요?",
     "answer": "사전 연락 시 같은 주 내 다른 시간대로 보강이 가능합니다. 강사와 일정을 조율해주세요.",
     "keywords": "결석 보강 빠지면 불참"},
    {"category": "enrollment", "question": "동시에 여러 강습을 수강할 수 있나요?",
     "answer": "네, 최대 3개 강습까지 동시 수강이 가능합니다. 시간이 겹치지 않도록 주의해주세요.",
     "keywords": "동시 여러 강습 중복 수강"},

    # ---- 수료/인증 ----
    {"category": "certificate", "question": "수료증은 어떻게 받나요?",
     "answer": "출석률 80% 이상이면 강습 완료 후 마이페이지에서 수료증을 다운로드할 수 있습니다.",
     "keywords": "수료증 인증서 완료 증명"},
    {"category": "certificate", "question": "수료 조건은 무엇인가요?",
     "answer": "전체 강습의 80% 이상 출석하면 수료가 인정됩니다.",
     "keywords": "수료 조건 출석 기준"},

    # ---- 종목별 FAQ ----
    {"category": "sport_swimming", "question": "수영 강습 시 준비물은 무엇인가요?",
     "answer": "수영복, 수경, 수영모는 필수입니다. 세면도구와 타월도 준비해주세요. 수영복은 실리콘 재질을 권장합니다.",
     "keywords": "수영 준비물 수영복 수경"},
    {"category": "sport_swimming", "question": "물을 무서워하는데 수영을 배울 수 있나요?",
     "answer": "네, 입문 과정에서 물 적응부터 시작합니다. 얕은 물에서 호흡 연습과 뜨기부터 차근차근 진행하므로 걱정하지 않으셔도 됩니다.",
     "keywords": "물 공포 무서워 못하는"},
    {"category": "sport_swimming", "question": "어린이 수영은 몇 살부터 가능한가요?",
     "answer": "만 5세부터 가능합니다. 만 5~7세는 놀이 수영 위주, 만 8세 이상은 본격적인 영법 학습이 가능합니다.",
     "keywords": "어린이 나이 몇살 유아"},

    {"category": "sport_tennis", "question": "테니스 라켓은 직접 준비해야 하나요?",
     "answer": "입문 과정에서는 대여 라켓을 제공합니다. 초급 이상부터는 자신에게 맞는 라켓 구매를 권장하며, 강사가 추천해드립니다.",
     "keywords": "테니스 라켓 장비 준비"},
    {"category": "sport_tennis", "question": "테니스를 처음 배우는데 어려울까요?",
     "answer": "포핸드부터 시작하면 첫 수업에서도 공을 넘길 수 있습니다. 입문 과정은 2~3주면 기본 랠리가 가능해집니다.",
     "keywords": "테니스 초보 어려운 처음"},

    {"category": "sport_golf", "question": "골프 입문 비용이 많이 드나요?",
     "answer": "입문 과정에서는 연습용 클럽을 대여해드립니다. 스크린 골프장에서 시작하므로 초기 비용이 크지 않습니다. 본격적으로 시작하시면 중고 클럽 세트(30~50만원)부터 추천합니다.",
     "keywords": "골프 비용 돈 장비 가격"},
    {"category": "sport_golf", "question": "골프 레슨과 필드 라운드는 별도인가요?",
     "answer": "네, 기본 레슨은 실내 연습장/스크린에서 진행됩니다. 필드 라운드 레슨은 별도 과정으로 중급 이상에서 진행합니다.",
     "keywords": "골프 필드 라운드 실내 스크린"},

    {"category": "sport_fitness", "question": "운동을 한 번도 안 해봤는데 PT 받을 수 있나요?",
     "answer": "물론입니다. 입문 과정은 운동 경험이 전혀 없는 분을 기준으로 설계되어 있습니다. 올바른 자세와 기초 체력부터 만들어갑니다.",
     "keywords": "피트니스 PT 초보 처음 운동"},
    {"category": "sport_fitness", "question": "크로스핏은 체력이 좋아야 하나요?",
     "answer": "중급 과정이라 기본 체력이 필요합니다. 스쿼트/데드리프트/풀업을 자세 무너짐 없이 할 수 있는 분에게 추천합니다. 입문자는 피트니스 기초 과정을 먼저 추천드립니다.",
     "keywords": "크로스핏 체력 조건 힘든"},

    {"category": "sport_yoga", "question": "몸이 뻣뻣한데 요가를 할 수 있나요?",
     "answer": "요가는 유연성을 '만들어가는' 운동입니다. 뻣뻣할수록 효과를 더 크게 느낄 수 있어요. 입문 과정에서 개인 수준에 맞게 동작을 조절해드립니다.",
     "keywords": "요가 유연성 뻣뻣 몸 굳은"},
    {"category": "sport_yoga", "question": "요가와 필라테스의 차이가 뭔가요?",
     "answer": "요가는 호흡/명상/유연성 중심이고, 필라테스는 코어 근력/자세 교정 중심입니다. 스트레스 관리에는 요가, 체형 교정에는 필라테스를 추천합니다.",
     "keywords": "요가 필라테스 차이 비교"},

    {"category": "sport_pilates", "question": "매트 필라테스와 기구 필라테스의 차이는?",
     "answer": "매트 필라테스는 자신의 체중을 이용하는 운동이고, 기구 필라테스는 리포머/캐딜락 등 전문 기구를 활용합니다. 입문자는 매트부터, 심화 과정은 기구를 추천합니다.",
     "keywords": "매트 기구 필라테스 차이 리포머"},
    {"category": "sport_pilates", "question": "필라테스는 여성만 하는 건가요?",
     "answer": "전혀 아닙니다. 남성에게도 코어 강화, 유연성 향상, 부상 예방에 매우 효과적입니다. 최근 남성 수강생이 크게 늘고 있습니다.",
     "keywords": "필라테스 남자 남성"},

    {"category": "sport_other", "question": "배드민턴 라켓은 어떤 걸 사야 하나요?",
     "answer": "입문자는 4U(80~84g) 무게의 이븐 밸런스 라켓을 추천합니다. 5~10만원대면 충분합니다. 강습 시 추천 모델을 안내해드립니다.",
     "keywords": "배드민턴 라켓 추천 장비"},
    {"category": "sport_other", "question": "클라이밍은 근력이 좋아야 하나요?",
     "answer": "입문 단계에서는 상체 근력보다 발 디딤과 밸런스가 더 중요합니다. 근력은 하면서 자연스럽게 생기니 걱정하지 마세요.",
     "keywords": "클라이밍 근력 힘 체력 조건"},
    {"category": "sport_other", "question": "축구와 풋살의 차이는 무엇인가요?",
     "answer": "풋살은 5인제로 좁은 코트에서 진행됩니다. 기술/패스 중심이라 초보자가 시작하기 좋고, 체력 소모도 상대적으로 적습니다.",
     "keywords": "축구 풋살 차이 비교 5인제"},
    {"category": "sport_other", "question": "춤을 전혀 못 추는데 댄스 수업 따라갈 수 있나요?",
     "answer": "입문 과정은 리듬 타기와 기본 스텝부터 시작합니다. 안무도 동작을 쪼개서 천천히 배우니 걱정하지 않으셔도 됩니다.",
     "keywords": "댄스 춤 못추는 초보 박치"},
    {"category": "sport_other", "question": "농구 키가 작아도 할 수 있나요?",
     "answer": "물론입니다! 드리블, 패스, 슈팅 기술은 키와 무관합니다. 동호회 수준에서는 팀워크와 기본기가 더 중요합니다.",
     "keywords": "농구 키 작은 체격 조건"},

    # ---- 플랫폼 이용 ----
    {"category": "platform", "question": "회원가입은 어떻게 하나요?",
     "answer": "홈페이지 우측 상단 '회원가입' 버튼을 클릭하고, 이메일과 비밀번호를 입력하면 가입됩니다.",
     "keywords": "회원가입 가입 계정 등록"},
    {"category": "platform", "question": "고객센터 운영 시간은 언제인가요?",
     "answer": "평일 09:00~18:00 (점심 12:00~13:00 제외)에 운영됩니다. 주말과 공휴일에는 AI 챗봇 상담이 가능합니다.",
     "keywords": "고객센터 상담 문의 전화 운영시간"},
    {"category": "platform", "question": "AI 챗봇은 어떤 걸 도와주나요?",
     "answer": "강습 검색, 맞춤 추천, 수강 현황 확인, FAQ 답변 등을 도와드립니다. 복잡한 문의는 고객센터로 연결해드립니다.",
     "keywords": "챗봇 AI 상담 채팅 도움"},
    {"category": "platform", "question": "앱도 있나요?",
     "answer": "현재는 모바일 웹으로 이용 가능합니다. 앱은 준비 중이며, 출시 시 알려드리겠습니다.",
     "keywords": "앱 모바일 어플 다운로드"},
]


# ============================================================
# 4. 가상 수강생 이름
# ============================================================
STUDENTS = ["홍길동", "김영희", "이철수", "박민지", "정다은", "강수진", "조현우", "윤서연"]


# ============================================================
# 5. 시드 메인 함수
# ============================================================
async def seed():
    async with AsyncSessionLocal() as db:
        # ──────────────────────────────────────────────
        # 1) 강사 시드
        # ──────────────────────────────────────────────
        instructor_map = {}  # name → Instructor 객체
        for data in INSTRUCTORS:
            instructor = Instructor(
                name=data["name"],
                specialty=data["specialty"],
                bio=data["bio"],
            )
            db.add(instructor)
            await db.flush()
            instructor_map[data["name"]] = instructor

        print(f"✅ 강사 {len(INSTRUCTORS)}명 생성 완료")

        # ──────────────────────────────────────────────
        # 2) 강습 시드 (모두 published 상태)
        # ──────────────────────────────────────────────
        lesson_objects = []
        for data in LESSON_TEMPLATES:
            instructor = instructor_map.get(data["instructor_name"])
            lesson = Lesson(
                title=data["title"],
                sport_type=data["sport_type"],
                difficulty=data["difficulty"],
                target_audience=data["target_audience"],
                instructor_id=instructor.id if instructor else None,
                status=LessonStatus.PUBLISHED,
            )
            db.add(lesson)
            await db.flush()
            lesson_objects.append(lesson)

        print(f"✅ 강습 {len(LESSON_TEMPLATES)}개 생성 완료")

        # ──────────────────────────────────────────────
        # 3) FAQ 시드
        # ──────────────────────────────────────────────
        for data in FAQS:
            faq = FAQ(
                category=data["category"],
                question=data["question"],
                answer=data["answer"],
                keywords=data.get("keywords", ""),
            )
            db.add(faq)

        print(f"✅ FAQ {len(FAQS)}개 생성 완료")

        # ──────────────────────────────────────────────
        # 4) 수강 데이터 시드
        # ──────────────────────────────────────────────
        enrollment_count = 0
        for student in STUDENTS:
            # 학생마다 3~6개 강습 수강
            num = random.randint(3, 6)
            selected = random.sample(lesson_objects, min(num, len(lesson_objects)))

            for lesson in selected:
                # 상태 랜덤 결정
                status_roll = random.random()
                if status_roll < 0.45:
                    status = EnrollmentStatus.COMPLETED
                    attendance = round(random.uniform(75, 100), 1)
                    completion_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))
                elif status_roll < 0.85:
                    status = EnrollmentStatus.IN_PROGRESS
                    attendance = round(random.uniform(30, 90), 1)
                    completion_date = None
                elif status_roll < 0.95:
                    status = EnrollmentStatus.ENROLLED
                    attendance = 0.0
                    completion_date = None
                else:
                    status = EnrollmentStatus.CANCELLED
                    attendance = round(random.uniform(5, 30), 1)
                    completion_date = None

                enrollment = Enrollment(
                    student_name=student,
                    lesson_id=lesson.id,
                    status=status,
                    attendance_rate=attendance,
                    completion_date=completion_date,
                )
                db.add(enrollment)
                enrollment_count += 1

        print(f"✅ 수강 {enrollment_count}건 생성 완료")

        # ──────────────────────────────────────────────
        # 5) 조회/찜 데이터 시드
        # ──────────────────────────────────────────────
        view_count = 0
        like_count = 0

        for student in STUDENTS:
            # 학생마다 6~15개 강습 조회
            num_views = random.randint(6, 15)
            viewed_lessons = random.sample(lesson_objects, min(num_views, len(lesson_objects)))

            for lesson in viewed_lessons:
                # 같은 강습 1~4번 조회
                for _ in range(random.randint(1, 4)):
                    view = LessonView(
                        student_name=student,
                        lesson_id=lesson.id,
                    )
                    db.add(view)
                    view_count += 1

            # 조회한 강습 중 일부를 찜
            num_likes = random.randint(2, min(5, len(viewed_lessons)))
            liked_lessons = random.sample(viewed_lessons, num_likes)

            for lesson in liked_lessons:
                like = LessonLike(
                    student_name=student,
                    lesson_id=lesson.id,
                )
                db.add(like)
                like_count += 1

        print(f"✅ 조회 {view_count}건, 찜 {like_count}건 생성 완료")

        # ──────────────────────────────────────────────
        # 커밋
        # ──────────────────────────────────────────────
        await db.commit()

        # ──────────────────────────────────────────────
        # 요약 출력
        # ──────────────────────────────────────────────
        sport_counts = {}
        for lt in LESSON_TEMPLATES:
            sport = lt["sport_type"].value
            sport_counts[sport] = sport_counts.get(sport, 0) + 1

        print("\n" + "=" * 55)
        print("📊 시드 데이터 요약")
        print("=" * 55)
        print(f"  강사:    {len(INSTRUCTORS)}명")
        print(f"  강습:    {len(LESSON_TEMPLATES)}개")
        for sport, count in sorted(sport_counts.items()):
            print(f"           - {sport}: {count}개")
        print(f"  FAQ:     {len(FAQS)}개")
        print(f"  수강생:  {len(STUDENTS)}명")
        print(f"  수강:    {enrollment_count}건")
        print(f"  조회:    {view_count}건")
        print(f"  찜:      {like_count}건")
        print("=" * 55)
        print("✅ 시드 데이터 생성이 모두 완료되었습니다!")


if __name__ == "__main__":
    asyncio.run(seed())