"""
LangGraph 에이전트 분기 조건 함수 모음.

should_use_tool: Router 후 ToolExecutor 또는 Response로 분기
should_retry_or_respond: Validator 후 재시도 또는 Response로 분기

실제 그래프 조립은 chat_service.py에서 담당한다.
"""

from typing import Any, Dict, Literal

from app.services.ai.agent_state import AgentState


def should_use_tool(state: AgentState) -> Literal["tool_executor", "response"]:
    """
    Router가 분류한 intent에 따라 ToolExecutor를 탈지, 바로 Response로 갈지 결정한다.

    일반 대화(general_inquiry)는 DB/RAG 같은 외부 도구를 호출할 필요가 없기 때문에
    여기서 곧바로 Response 노드로 보내 토큰 사용량과 레이턴시를 줄인다.
    그 외 intent(search_lessons, faq_inquiry 등)는 비즈니스 로직이 필요하므로 ToolExecutor로 보낸다.
    """

    if state["intent"] == "general_inquiry":
        return "response"
    return "tool_executor"


# 같은 툴이 이 횟수 이상 호출되면 무한 루프 방지를 위해 무조건 응답 노드로 이동
MAX_TOOL_CALLS = 3


def should_retry_or_respond(state: AgentState) -> Literal["tool_executor", "response"]:
    """
    Validator 결과에 따라 Tool을 한 번 더 실행할지, 아니면 최종 Response로 넘어갈지 결정한다.

    재시도 정책을 여기에서 분리해두면:
    - Validator는 "이 결과가 충분한가?"만 판단하고,
    - 실제로 몇 번까지 다시 시도할지, 무한루프를 어떻게 방지할지는 이 함수에서 일관되게 관리할 수 있다.
    """

    # 방어 로직: 같은 요청에서 툴이 3번 이상 호출되었다면
    # (예: Router/Validator가 번갈아가며 재시도 루프에 빠진 경우),
    # 더 이상 ToolExecutor로 보내지 않고 무조건 Response로 보내 무한 반복을 끊는다.
    tools_used = state.get("tools_used") or []
    if len(tools_used) >= MAX_TOOL_CALLS:
        return "response"

    # Validator가 "유효한 결과"라고 판단했으면 더 이상의 재시도는 의미가 없으므로 Response로 보낸다.
    if state.get("is_valid", False):
        return "response"

    # retry_count가 1~2이고 retry_strategy가 설정된 경우에만 재시도를 허용한다.
    # 0이면 아직 첫 시도가 끝나지 않았거나 재시도 필요가 없는 상태,
    # 2를 넘기면 "조건을 더 완화할수록 품질이 떨어진다"는 경험적 기준에 따라 중단한다.
    retry_count = state.get("retry_count", 0)
    if retry_count > 0 and retry_count <= 2 and state.get("retry_strategy"):
        return "tool_executor"

    # 나머지 모든 경우(유효하지도 않고, 재시도 조건도 충족하지 못할 때)는
    # 강제로 Response로 이동해 "결과 없음"에 대한 자연어 안내를 생성하게 한다.
    return "response"


# ---------------------------------------------------------------------------
# 멀티에이전트 그래프 (Supervisor → 서브에이전트 → Aggregator → Response)
# 기존 chat_service 단일 Router 그래프와 병존. Step 5B에서 feature flag로 선택.
# ---------------------------------------------------------------------------


def should_route_from_supervisor(state: AgentState) -> Literal["dispatcher", "response"]:
    """
    Supervisor 이후 분기.
    direct_response면 바로 response로, 그 외는 dispatcher로.
    """
    if state.get("routing_mode") == "direct_response":
        return "response"
    return "dispatcher"


def should_dispatch_agent(
    state: AgentState,
) -> Literal["lesson", "enrollment", "faq", "aggregator"]:
    """
    dispatcher에서 어느 에이전트로 갈지 결정.
    agent_plan[current_agent_index]를 보고 분기.
    인덱스가 범위를 벗어나면 aggregator로 빠져 바로 종료 경로를 타게 한다.
    (aggregator는 idx를 한 번 더 증가시키지만 그 뒤 should_continue_after_aggregator가
     즉시 response로 보낸다.)
    """
    plan = state.get("agent_plan") or []
    idx = state.get("current_agent_index", 0)
    if idx >= len(plan):
        return "aggregator"
    nxt = plan[idx]
    if nxt not in {"lesson", "enrollment", "faq"}:
        # facility는 Step 11에서 활성화. 안전장치.
        return "aggregator"
    return nxt  # type: ignore[return-value]


def should_continue_after_aggregator(
    state: AgentState,
) -> Literal["dispatcher", "response"]:
    """
    Aggregator 이후 분기.
    - agent_plan에 다음 에이전트가 남았으면 dispatcher로 (multi_agent 순차)
    - single_agent에서 방금 유효한 결과를 얻었으면 response로 바로
    - plan 끝까지 순회했으면 response로

    (Step 7에서 재라우팅 분기가 여기에 추가될 예정. 현재는 2-way만.)
    """
    plan = state.get("agent_plan") or []
    idx = state.get("current_agent_index", 0)

    # plan에 다음 에이전트가 남았음
    if idx < len(plan):
        return "dispatcher"
    return "response"


def build_multi_agent_graph():
    """
    Supervisor + 서브에이전트 + Aggregator 기반 멀티에이전트 그래프.

    기존 chat_service의 단일 Router 조립과 공존하며, Step 5B에서
    settings.use_multi_agent에 따라 둘 중 하나를 선택한다.

    dispatcher는 상태를 변경하지 않는 passthrough로,
    조건부 엣지를 통해 실제 에이전트 노드로 라우팅하는 역할만 한다.
    """
    from langgraph.graph import END, StateGraph

    from app.services.ai.agent_nodes import response_node
    from app.services.ai.agents import enrollment_agent, faq_agent, lesson_agent
    from app.services.ai.supervisor_node import aggregator_node, supervisor_node

    async def _dispatcher_passthrough(state: AgentState) -> Dict[str, Any]:
        """상태 변경 없는 passthrough. 조건부 엣지로만 라우팅."""
        return {}

    g = StateGraph(AgentState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("dispatcher", _dispatcher_passthrough)
    g.add_node("lesson", lesson_agent)
    g.add_node("enrollment", enrollment_agent)
    g.add_node("faq", faq_agent)
    g.add_node("aggregator", aggregator_node)
    g.add_node("response", response_node)

    g.set_entry_point("supervisor")

    g.add_conditional_edges(
        "supervisor",
        should_route_from_supervisor,
        {
            "dispatcher": "dispatcher",
            "response": "response",
        },
    )

    g.add_conditional_edges(
        "dispatcher",
        should_dispatch_agent,
        {
            "lesson": "lesson",
            "enrollment": "enrollment",
            "faq": "faq",
            "aggregator": "aggregator",
        },
    )

    for agent_name in ("lesson", "enrollment", "faq"):
        g.add_edge(agent_name, "aggregator")

    # Step 7: 재라우팅 시 아래 맵에 "reroute": "reroute_supervisor" 등 추가 예정
    g.add_conditional_edges(
        "aggregator",
        should_continue_after_aggregator,
        {
            "dispatcher": "dispatcher",
            "response": "response",
        },
    )

    g.add_edge("response", END)

    return g.compile()
