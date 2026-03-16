"""
LangGraph 에이전트 그래프 구성.

노드와 엣지를 조립하여 실행 가능한 그래프를 만든다.

이 모듈은 "상태 머신의 뼈대"만 정의하고, 실제 ToolExecutor 노드는
DB 세션이 필요한 chat_service 쪽에서 주입하는 식으로 분리되어 있다.
이렇게 분리해 두면:
- 그래프 정의는 순수(pure)하게 유지되어 테스트/리팩터링이 쉽고,
- DB / 외부 리소스 의존성은 실행 레이어에서만 관리할 수 있다.
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


def build_agent_graph():
    """
    LangGraph 상태 머신을 구성한다.

    이 함수는 "어떤 노드가 어떤 순서/조건으로 실행되는지"만 정의하고,
    실제 ToolExecutor 노드는 DB 세션이 필요한 chat_service 쪽에서 주입된다.

    이렇게 레이어를 나누는 이유:
    - 이 모듈은 순수한 그래프 정의만 담고 있어, 유닛 테스트나 시뮬레이션이 쉽다.
    - DB·외부 리소스에 대한 의존성은 실행 레이어(chat_service)에만 두어, 환경 설정이 단순해진다.
    """

    # AgentState 타입을 사용하는 LangGraph 상태 머신 인스턴스를 만든다.
    graph = StateGraph(AgentState)

    # Router 노드는 항상 그래프의 첫 진입점이므로 여기서 고정으로 추가한다.
    graph.add_node("router", router_node)

    # ToolExecutor 노드는 DB 세션이 필요해 이 모듈에서는 추가하지 않는다.
    # 대신 Validator/Response는 언제나 동일한 순서로 호출되므로 여기서 미리 정의해 둔다.
    graph.add_node("validator", validator_node)
    graph.add_node("response", response_node)

    # 상태 머신의 시작점을 Router로 지정한다.
    graph.set_entry_point("router")

    # Router가 끝난 뒤, intent에 따라 ToolExecutor 또는 Response로 분기한다.
    # 이 분기 로직은 should_use_tool에서 관리해, Router와 그래프 정의를 느슨하게 결합한다.
    graph.add_conditional_edges(
        "router",
        should_use_tool,
        {"tool_executor": "tool_executor", "response": "response"},
    )

    # ToolExecutor는 항상 Validator로 이어진다.
    # Validator가 결과의 유효성을 검사하고 재시도 여부를 결정한다.
    graph.add_edge("tool_executor", "validator")

    # Validator가 끝난 뒤, 재시도할지 바로 Response로 갈지를 should_retry_or_respond가 결정한다.
    graph.add_conditional_edges(
        "validator",
        should_retry_or_respond,
        {"tool_executor": "tool_executor", "response": "response"},
    )

    # Response 노드가 실행되면 상태 머신은 종료(END) 상태로 이동한다.
    graph.add_edge("response", END)

    return graph

