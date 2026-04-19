"""
멀티에이전트 LangGraph 분기 조건 및 그래프 빌더.

Supervisor → dispatcher → 서브에이전트(lesson/enrollment/faq) → Aggregator
→ (필요 시) reroute_supervisor → dispatcher → 추가 에이전트 → Aggregator → Response
흐름을 `build_multi_agent_graph()`로 조립한다. 비스트리밍 실행은 chat_service가 이 빌더를 사용한다.
"""

from typing import Any, Dict, Literal

from app.services.ai.agent_state import AgentState


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
) -> Literal["dispatcher", "reroute", "response"]:
    """
    Aggregator 이후 분기.

    1) agent_plan에 다음 에이전트가 남아 있으면 dispatcher로 (multi_agent 순차)
    2) single_agent에서 실패했고 아직 재라우팅 기회가 있으면 reroute
    3) 그 외는 response로
    """
    plan = state.get("agent_plan") or []
    idx = state.get("current_agent_index", 0)

    if idx < len(plan):
        return "dispatcher"

    if (
        state.get("routing_mode") == "single_agent"
        and not state.get("is_valid", False)
        and state.get("rerouting_count", 0) == 0
    ):
        return "reroute"

    return "response"


def build_multi_agent_graph():
    """
    Supervisor + 서브에이전트 + Aggregator 기반 멀티에이전트 그래프.

    dispatcher는 상태를 변경하지 않는 passthrough로,
    조건부 엣지를 통해 실제 에이전트 노드로 라우팅하는 역할만 한다.
    """
    from langgraph.graph import END, StateGraph

    from app.services.ai.agent_nodes import response_node
    from app.services.ai.agents import enrollment_agent, faq_agent, lesson_agent
    from app.services.ai.supervisor_node import (
        aggregator_node,
        reroute_supervisor_node,
        supervisor_node,
    )

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
    g.add_node("reroute_supervisor", reroute_supervisor_node)
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

    return g.compile()
