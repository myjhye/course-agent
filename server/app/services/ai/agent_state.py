"""
LangGraph 에이전트 상태 정의.

모든 노드가 공유하는 상태 객체이며,
각 노드는 이 상태를 읽고 수정하여 다음 노드에 전달한다.
"""

from typing import TypedDict, Optional, Any, List, Dict


class AgentState(TypedDict):
    """에이전트의 전체 상태"""

    # ── 입력 ──
    user_message: str                          # 사용자 원본 메시지
    student_name: Optional[str]                # 수강생 이름 (None이면 비로그인)
    chat_history: List[Dict[str, str]]         # 이전 대화 히스토리 [{role, content}, ...]

    # ── Router 결과 ──
    intent: str                                # 분류된 의도
    # "search_lessons" | "get_recommendations" | "manage_enrollment"
    # "faq_inquiry" | "general_inquiry"

    # ── Tool 실행 결과 ──
    tool_name: Optional[str]                   # 실행한 Tool 이름
    tool_args: Optional[Dict[str, Any]]        # Tool에 전달한 인자
    tool_result: Optional[Dict[str, Any]]      # Tool 실행 결과

    # ── Validator 결과 ──
    is_valid: bool                             # Tool 결과가 유효한지
    retry_count: int                           # 재시도 횟수 (최대 2)
    retry_strategy: Optional[str]              # 재시도 전략 설명

    # ── 최종 출력 ──
    response: str                              # 최종 응답 텍스트
    tools_used: List[str]                      # 사용된 Tool 목록
    all_tool_results: Dict[str, Any]           # 모든 Tool 결과
    total_tokens: int                          # 총 토큰 사용량
    error: Optional[str]                       # 에러 메시지 (있을 경우)

