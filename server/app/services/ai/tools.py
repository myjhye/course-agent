CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_lessons",
            "description": "강습을 검색합니다. 사용자가 강습을 찾거나 특정 조건의 강습을 물어볼 때 사용합니다. 검색 후 상세 정보가 필요하면 get_lesson_detail을 추가로 호출하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색 키워드 (예: 수영, 테니스, 입문)"
                    },
                    "sport_type": {
                        "type": "string",
                        "description": "종목 필터",
                        "enum": ["swimming", "tennis", "golf", "fitness", "yoga", "pilates"]
                    },
                    "difficulty": {
                        "type": "string",
                        "description": "난이도 필터",
                        "enum": ["beginner", "elementary", "intermediate", "advanced"]
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
            "description": "수강생의 수강 현황(수강 중인 강습, 완료한 강습, 출석률)을 조회합니다. 추천이 필요하면 이후 get_recommendations를 호출하세요.",
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
            "description": "수강생의 수강 이력을 바탕으로 다음에 들을 강습을 추천합니다. 수강 현황과 함께 보여주려면 get_my_enrollments를 먼저 호출하세요.",
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

