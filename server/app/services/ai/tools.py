CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_lessons",
            "description": """강습을 검색합니다.

**반드시 이 도구를 사용해야 하는 경우:**
- 특정 종목 강습 요청: "수영 강습 알려줘", "테니스 배우고 싶어", "골프 추천해줘"
- 특정 조건 검색: "초급 요가", "성인 필라테스", "피트니스 강습"
- "OO 강습 추천해줘"처럼 종목이 명시된 경우

**주의:** "수영 추천", "테니스 강습 추천" 등 특정 종목이 언급되면 get_recommendations가 아닌 이 도구를 사용!""",
            "parameters": {
                "type": "object",
                "properties": {
                    "sport_type": {
                        "type": "string",
                        "description": "종목 (swimming=수영, tennis=테니스, golf=골프, yoga=요가, pilates=필라테스, fitness=피트니스)",
                        "enum": ["swimming", "tennis", "golf", "fitness", "yoga", "pilates"]
                    },
                    "difficulty": {
                        "type": "string",
                        "description": "난이도 (beginner=입문, elementary=초급, intermediate=중급, advanced=고급)",
                        "enum": ["beginner", "elementary", "intermediate", "advanced"]
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "대상 (adult=성인, child=어린이, senior=시니어)",
                        "enum": ["adult", "child", "senior"]
                    },
                    "keyword": {
                        "type": "string",
                        "description": "추가 검색 키워드 (선택)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lesson_detail",
            "description": "특정 강습의 상세 정보(소개, 커리큘럼)를 조회합니다. search_lessons로 찾은 강습의 자세한 내용이 필요할 때 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lesson_id": {
                        "type": "integer",
                        "description": "강습 ID (search_lessons 결과에서 확인)"
                    }
                },
                "required": ["lesson_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_enrollments",
            "description": "수강생의 수강 현황(수강 중인 강습, 완료한 강습, 출석률)을 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_name": {
                        "type": "string",
                        "description": "수강생 이름"
                    }
                },
                "required": ["student_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": """수강생의 수강 이력 기반 맞춤 추천을 제공합니다.

**이 도구를 사용해야 하는 경우:**
- 특정 종목 없이 일반적인 추천: "추천해줘", "뭐 들을까", "다음 강습 뭐 들어"
- 개인화 추천: "나한테 맞는 강습", "나한테 추천해줘"

**주의:** "수영 추천", "테니스 강습 추천"처럼 특정 종목이 언급되면 이 도구 대신 search_lessons 사용!""",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_name": {
                        "type": "string",
                        "description": "수강생 이름"
                    }
                },
                "required": ["student_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_faq",
            "description": "자주 묻는 질문(FAQ)을 검색합니다. 환불, 결제, 수강 방법, 수료증 등 이용 관련 질문에 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색 키워드 (예: 환불, 결제, 수료증)"
                    }
                },
                "required": ["keyword"]
            }
        }
    }
]

NO_RESULT_MESSAGES = {
    "search_lessons": "'{keyword}' 관련 강습을 찾지 못했습니다. 다른 키워드로 검색해보시겠어요?",
    "get_lesson_detail": "해당 강습을 찾을 수 없습니다.",
    "get_my_enrollments": "수강 내역이 없습니다. 강습을 둘러보시겠어요?",
    "get_recommendations": "추천할 강습을 찾지 못했습니다.",
    "search_faq": "관련 FAQ를 찾지 못했습니다. 고객센터로 문의해주세요.",
    "no_tool": "죄송합니다. 해당 질문에 답변드리기 어렵습니다. 강습 검색, 수강 현황, 이용 방법에 대해 물어봐주세요."
}

