"""
LangGraph 에이전트 상태 정의.

모든 노드가 공유하는 단일 상태 객체이다. 각 노드는 이 상태를 읽고,
자기 출력만 병합(merge)해서 반환하며, 그래프가 다음 노드로 전달한다.
TypedDict이므로 필드는 선택적으로 넣을 수 있고, 노드가 건드리지 않은 키는 유지된다.
"""

from typing import TypedDict, Optional, Any, List, Dict, Literal


class AgentState(TypedDict, total=False):
    """
    에이전트의 전체 상태. 라우터 → 툴 실행 → 검증 → 재시도/응답 흐름에서
    단계 간에 넘겨지는 모든 정보가 여기 담긴다.
    """

    # ── 입력 (chat_service에서 초기 세팅) ──
    user_message: str
    # 사용자 원본 메시지. Router/추출/Response 노드에서 공통으로 참조한다.

    student_name: Optional[str]
    # 수강생 이름. None이면 비로그인/미확인. Response 노드에서 "~님" 등 개인화에 쓴다.

    chat_history: List[Dict[str, str]]
    # 이전 턴의 [{role, content}, ...]. Response 노드가 맥락을 넣어 답변할 때 사용한다.

    trace_id: Optional[str]
    # Langfuse trace/루트 span ID. 각 노드에서 observation에 metadata로 넣어 같은 대화를 하나의 trace로 묶는다.

    # ── Router 결과 (router_node가 채움) ──
    intent: str
    # 분류된 의도. "search_lessons" | "get_recommendations" | "manage_enrollment" | "faq_inquiry" | "general_inquiry"
    # general_inquiry면 툴 없이 바로 Response로 가고, 나머지는 ToolExecutor → Validator 경로를 탄다.

    # ── Tool 실행 결과 (tool_executor_node가 채움) ──
    tool_name: Optional[str]
    # 이번 턴에 실행한 도구 이름. Response 노드가 "어떤 도구 결과인지" 프롬프트에 넣을 때 쓴다.

    tool_args: Optional[Dict[str, Any]]
    # 해당 도구에 넘긴 인자. 디버깅/로그용.

    tool_result: Optional[Dict[str, Any]]
    # 도구 반환값 {success, data, ...}. Validator가 is_valid 판단하고, Response가 문장으로 요약할 때 쓴다.

    # ── Validator 결과 (validator_node가 채움) ──
    is_valid: bool
    # Tool 결과가 "성공 + 데이터 있음"이면 True. False면 should_retry_or_respond에서 재시도 여부를 본다.

    retry_count: int
    # 이번 대화에서 툴 재시도한 횟수. 0=첫 실행, 1~2=재시도. 2 이상이면 더 이상 재시도하지 않고 Response로 넘긴다.

    retry_strategy: Optional[str]
    # "relax_filters" | "broaden_keyword" 등. ToolExecutor가 재실행 시 인자를 어떻게 완화할지 결정하는 데 쓴다.

    # ── 최종 출력 (Response 노드 / chat_service가 채움) ──
    response: str
    # 최종 사용자에게 보낼 자연어. 스트리밍이면 토큰을 모아서 여기 넣거나, 클라이언트에 바로 내려보낸다.

    tools_used: List[str]
    # 이번 턴에서 호출된 도구 이름 목록. 같은 도구가 재시도로 여러 번 나와도 누적된다. 분석/로그용.

    all_tool_results: Dict[str, Any]
    # 도구별·재시도별 결과를 tool_name_1, tool_name_2 형태로 저장. Langfuse/대시보드에서 비교용.

    total_tokens: int
    # Router + 추출 + Response 등 모든 LLM 호출의 토큰 합. 비용/모니터링용.

    error: Optional[str]
    # 예외 발생 시 메시지. 클라이언트에 보낼 fallback 문구를 만들 때 참고할 수 있다.

    routing_mode: Literal["single_agent", "multi_agent", "direct_response"]
    agent_plan: list[Literal["lesson", "enrollment", "faq", "facility"]]
    current_agent_index: int
    agent_outputs: dict[str, dict]
    handoff_reason: Optional[str]
    rerouting_count: int
    rerouted_from: Optional[str]

