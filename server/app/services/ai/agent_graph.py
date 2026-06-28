"""
LangGraph 그래프 조립 파일. 노드 등록, 엣지 연결, 조건부 분기 함수를 정의하고 컴파일된 그래프를 반환한다.

-> 이 파일은 비스트리밍 경로(POST /api/chat)에서만 실제로 사용된다.
스트리밍 경로(POST /api/chat/stream)는 chat_orchestrator가 노드 함수를 직접 순서대로 호출하기 때문에
이 그래프 객체를 쓰지 않는다.
"""

from typing import Any, Dict, Literal

from app.services.ai.agent_state import AgentState


def should_route_from_supervisor(state: AgentState) -> Literal["dispatcher", "response"]:
    """
    supervisor 끝난 후 다음 목적지 결정.
    - "안녕하세요" 같은 질문은 에이전트 필요 없으니 바로 response로
    - 강습 검색, FAQ 같은 질문은 에이전트 써야 하니 dispatcher로
    """
    if state.get("routing_mode") == "direct_response":
        return "response"
    return "dispatcher"


def should_dispatch_agent(
    state: AgentState,
) -> Literal["lesson", "enrollment", "faq", "facility", "calendar", "aggregator"]:
    """
    dispatcher 끝난 후 다음에 실행할 에이전트 결정.
    - state에서 agent_plan이랑 current_agent_index 읽어서 지금 차례 에이전트 이름 반환
    - plan 다 소진했거나 알 수 없는 에이전트 이름이면 aggregator로 (방어 처리)
    """
    plan = state.get("agent_plan") or []
    idx = state.get("current_agent_index", 0)

    if idx >= len(plan):
        return "aggregator"  # 실행할 에이전트 없으면 aggregator로

    nxt = plan[idx]
    if nxt not in {"lesson", "enrollment", "faq", "facility", "calendar"}:
        return "aggregator"  # 알 수 없는 에이전트 이름이면 aggregator로

    return nxt  # type: ignore[return-value]


def should_continue_after_aggregator(
    state: AgentState,
) -> Literal["dispatcher", "reroute", "response"]:
    """
    aggregator 끝난 후 다음 목적지 결정. 세 가지 중 하나로 간다.
    1. 아직 실행할 에이전트 남아있으면 → dispatcher로 (멀티 에이전트 순차 실행)
    2. 실패했고 재시도 안 했으면 → reroute로 (Self-Correction)
    3. 완료됐거나 복구 불가능하면 → response로
    """
    plan = state.get("agent_plan") or []
    idx = state.get("current_agent_index", 0)

    if idx < len(plan):
        return "dispatcher"  # 아직 실행할 에이전트 남아있음

    if (
        state.get("routing_mode") == "single_agent"  # 단일 에이전트였고
        and not state.get("is_valid", False)          # 결과가 실패였고
        and state.get("rerouting_count", 0) == 0      # 아직 재시도 안 했으면
    ):
        return "reroute"

    return "response"


def build_multi_agent_graph():
    """
    [비스트리밍 전용] 노드와 엣지를 조립해서 컴파일된 LangGraph 그래프를 반환한다.
    chat_orchestrator의 chat() → _run_agent_graph() 경로에서만 사용. ainvoke()로 일괄 실행.
    스트리밍 경로는 이 그래프를 쓰지 않고 chat_orchestrator가 노드를 직접 호출한다.
    """
    # 함수 안에서 import하는 이유: 순환 임포트 방지.
    # 파일 로드 시점에 import하면 서로가 서로를 참조하는 문제가 생길 수 있어서
    # 함수가 실제로 호출되는 시점에 import한다.
    from langgraph.graph import END, StateGraph

    from app.services.ai.agent_nodes import response_node
    from app.services.ai.agents import (
        enrollment_agent,
        facility_agent,
        faq_agent,
        lesson_agent,
        calendar_agent,
    )
    from app.services.ai.orchestration_nodes import (
        aggregator_node,
        reroute_supervisor_node,
        supervisor_node,
    )

    # dispatcher는 아무것도 안 하는 빈 노드.
    # LangGraph는 add_conditional_edges를 노드에만 붙일 수 있어서
    # "어느 에이전트로 갈지" 분기 함수를 붙이기 위한 자리 역할만 한다.
    async def _dispatcher_passthrough(state: AgentState) -> Dict[str, Any]:
        return {}

    g = StateGraph(AgentState)

    # 노드 등록
    g.add_node("supervisor", supervisor_node)
    g.add_node("dispatcher", _dispatcher_passthrough)
    g.add_node("lesson", lesson_agent)
    g.add_node("enrollment", enrollment_agent)
    g.add_node("faq", faq_agent)
    g.add_node("facility", facility_agent)
    g.add_node("calendar", calendar_agent)
    g.add_node("aggregator", aggregator_node)
    g.add_node("reroute_supervisor", reroute_supervisor_node)
    g.add_node("response", response_node)

    # 시작점: 질문 들어오면 supervisor부터 실행
    g.set_entry_point("supervisor")

    # supervisor 끝나면 → direct_response면 response로, 아니면 dispatcher로
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
            "facility": "facility",
            "calendar": "calendar",
            "aggregator": "aggregator",
        },
    )

    # 개별 도메인 서브에이전트 실행 완료 후 검증(Aggregator) 단계 강제 연결
    for agent_name in ("lesson", "enrollment", "faq", "facility", "calendar"):
        g.add_edge(agent_name, "aggregator")

    g.add_conditional_edges(
        "aggregator",
        should_continue_after_aggregator,
        {
            "dispatcher": "dispatcher",
            "reroute": "reroute_supervisor",
            "response": "response",
        },
    )

    g.add_edge("reroute_supervisor", "dispatcher")
    g.add_edge("response", END)

    # 조립된 워크플로우를 컴파일하여 실행용 세션으로 반환
    return g.compile()

