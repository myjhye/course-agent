"""
LangGraph 에이전트 그래프 구성.

노드와 엣지를 조립하여 실행 가능한 그래프를 만든다.
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import (
    router_node,
    validator_node,
    response_node,
)


def should_use_tool(state: AgentState) -> Literal["tool_executor", "response"]:
    """Router 결과에 따라 다음 노드를 결정한다."""
    if state["intent"] == "general_inquiry":
        return "response"
    return "tool_executor"


def should_retry_or_respond(state: AgentState) -> Literal["tool_executor", "response"]:
    """Validator 결과에 따라 재시도 또는 응답 생성을 결정한다."""
    if state.get("is_valid", False):
        return "response"

    retry_count = state.get("retry_count", 0)
    if retry_count > 0 and retry_count <= 2 and state.get("retry_strategy"):
        return "tool_executor"

    return "response"


def build_agent_graph():
    """
    LangGraph 상태 머신을 구성한다.

    주의: tool_executor 노드는 DB 세션이 필요하기 때문에
    실제 실행 시점에는 chat_service 쪽에서 별도로 래핑해서 추가한다.
    여기서는 router / validator / response 노드와 구조만 정의한다.
    """

    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    # "tool_executor" 노드는 실행 시점에 추가
    graph.add_node("validator", validator_node)
    graph.add_node("response", response_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        should_use_tool,
        {"tool_executor": "tool_executor", "response": "response"},
    )

    graph.add_edge("tool_executor", "validator")

    graph.add_conditional_edges(
        "validator",
        should_retry_or_respond,
        {"tool_executor": "tool_executor", "response": "response"},
    )

    graph.add_edge("response", END)

    return graph

