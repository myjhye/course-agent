"""
멀티에이전트 LangGraph 분기 조건 및 그래프 빌더.

Supervisor → dispatcher → 서브에이전트(lesson/enrollment/faq) → Aggregator
→ (필요 시) reroute_supervisor → dispatcher → 추가 에이전트 → Aggregator → Response
흐름을 `build_multi_agent_graph()`로 조립한다. 비스트리밍 실행은 chat_service가 이 빌더를 사용한다.
"""

# LangGraph 타입 힌트 임포트
from typing import Any, Dict, Literal

# 그래프 전체가 공유하는 상태 객체 임포트
from app.services.ai.agent_state import AgentState


def should_route_from_supervisor(state: AgentState) -> Literal["dispatcher", "response"]:
    # supervisor 끝난 후 "에이전트 쓸 거야 말 거야" (2가지 선택: response, dispatcher)

    if state.get("routing_mode") == "direct_response":
        # "안녕하세요" 같은 질문은 에이전트 필요 없으니 바로 응답으로
        return "response"

    # routing_mode가 single_agent or multi_agent면
    # → 어느 에이전트로 갈지 결정하러 dispatcher로
    return "dispatcher"


def should_dispatch_agent(
    state: AgentState,
) -> Literal["lesson", "enrollment", "faq", "facility", "calendar", "aggregator"]:
    # dispatcher 이후 "그럼 어느 에이전트야" (6가지 선택: lesson, enrollment, faq, facility, calendar, aggregator)

    # supervisor가 써놓은 에이전트 실행 계획 읽기 (예: ["lesson", "faq"])
    plan = state.get("agent_plan") or []

    # 지금 몇 번째 에이전트를 실행할 차례인지 읽기
    idx = state.get("current_agent_index", 0)

    if idx >= len(plan):
        # 인덱스가 plan 범위를 벗어남 → 실행할 에이전트 없으니 aggregator로 (종료 경로)
        # 예: plan = ["lesson"], idx = 1 → 더 이상 할 게 없음
        return "aggregator"

    # plan에서 지금 실행할 에이전트 이름 꺼내기
    # 예: plan = ["lesson", "faq"], idx = 0 → nxt = "lesson"
    nxt = plan[idx]

    if nxt not in {"lesson", "enrollment", "faq", "facility", "calendar"}:
        # 꺼낸 이름이 알 수 없는 에이전트면 aggregator로 (방어 처리)
        # supervisor가 잘못된 이름을 써놨을 경우 대비
        return "aggregator"

    # 해당 에이전트 노드 이름 반환 → LangGraph가 그 노드로 이동
    return nxt  # type: ignore[return-value]


def should_continue_after_aggregator(
    state: AgentState,
) -> Literal["dispatcher", "reroute", "response"]:
    # aggregator 끝난 후 "계속 할 거야 끝낼 거야" (3가지 선택: dispatcher, reroute, response)

    # supervisor가 세운 계획 읽기 (예: ["lesson", "faq"])
    plan = state.get("agent_plan") or []

    # 지금까지 몇 번째 에이전트까지 실행했는지 읽기
    idx = state.get("current_agent_index", 0)

    if idx < len(plan):
        # 아직 실행 안 한 에이전트가 남아있으면 → dispatcher로 돌아가서 다음 에이전트 실행
        # 예: plan = ["lesson", "faq"], idx = 1 → faq 아직 안 했으니 계속
        return "dispatcher"

    if (
        state.get("routing_mode") == "single_agent"  # 에이전트 1개짜리 실행이었고 (multi면 재시도 안 함)
        and not state.get("is_valid", False)  # aggregator가 결과를 실패로 판정했고
        and state.get("rerouting_count", 0) == 0  # 아직 재시도를 한 번도 안 했으면 (무한루프 방지)
    ):
        # 세 조건 모두 충족 → 다른 에이전트로 재시도하러 reroute_supervisor로
        return "reroute"

    # plan 다 소진했고 + (성공했거나 or multi 실패거나 or 재시도 이미 했으면)
    # → 있는 결과로 최종 응답 생성
    return "response"


def build_multi_agent_graph():
    # 노드와 엣지를 조립해서 실행 가능한 그래프를 만드는 함수

    # LangGraph 그래프 클래스 임포트
    # 함수 안에서 임포트하는 이유: 이 파일 로드될 때 아래 파일들이 아직 준비 안 됐을 수 있어서
    # 함수가 실제로 호출될 때 임포트하면 그 시점엔 다 준비돼 있음
    from langgraph.graph import END, StateGraph

    from app.services.ai.agent_nodes import response_node

    # 5개 서브에이전트 함수 임포트
    from app.services.ai.agents import (
        enrollment_agent,
        facility_agent,
        faq_agent,
        lesson_agent,
        calendar_agent,
    )

    # supervisor, aggregator, reroute 함수 임포트
    from app.services.ai.routing_nodes import (
        aggregator_node,
        reroute_supervisor_node,
        supervisor_node,
    )

    # 아무것도 안 하는 빈 노드
    # LangGraph 규칙상 분기 함수는 노드에만 붙일 수 있음
    # dispatcher 노드가 없으면 should_dispatch_agent를 어디에도 붙일 수 없어서 존재
    async def _dispatcher_passthrough(state: AgentState) -> Dict[str, Any]:
        return {}

    # 그래프 생성. AgentState를 모든 노드가 공유하는 상태로 지정
    g = StateGraph(AgentState)

    # 노드 등록 (이름, 실행할 함수)
    # 이름은 엣지 연결할 때 사용, 함수는 해당 노드 실행될 때 호출됨
    g.add_node("supervisor", supervisor_node)  # 의도 판단, 계획 수립
    g.add_node("dispatcher", _dispatcher_passthrough)  # 분기점 역할만 하는 빈 노드
    g.add_node("lesson", lesson_agent)  # 강습 검색
    g.add_node("enrollment", enrollment_agent)  # 수강 현황
    g.add_node("faq", faq_agent)  # FAQ 검색
    g.add_node("facility", facility_agent)  # 체육시설 검색 (MCP)
    g.add_node("calendar", calendar_agent)  # 구글 캘린더 일정 관리 (MCP)
    g.add_node("aggregator", aggregator_node)  # 결과 수집 및 유효성 확인
    g.add_node("reroute_supervisor", reroute_supervisor_node)  # 실패 시 재계획
    g.add_node("response", response_node)  # 최종 응답 생성

    # 그래프 시작점 지정. 질문이 들어오면 supervisor부터 실행
    g.set_entry_point("supervisor")

    g.add_conditional_edges(
        "supervisor", # supervisor 노드 끝난 후
        should_route_from_supervisor,  # 이 함수가 방향 결정
        {
            "dispatcher": "dispatcher", # should_route_from_supervisor가 "dispatcher" 반환 → dispatcher 노드로
            "response": "response", # should_route_from_supervisor가 "response" 반환 → response 노드로
        },
    )

    g.add_conditional_edges(
        "dispatcher", # dispatcher 노드 끝난 후
        should_dispatch_agent,  # 이 함수가 방향 결정
        {
            "lesson": "lesson", # should_dispatch_agent가 "lesson" 반환 → lesson 노드로
            "enrollment": "enrollment", # should_dispatch_agent가 "enrollment" 반환 → enrollment 노드로
            "faq": "faq", # should_dispatch_agent가 "faq" 반환 → faq 노드로
            "facility": "facility", # should_dispatch_agent가 "facility" 반환 → facility 노드로
            "calendar": "calendar", # should_dispatch_agent가 "calendar" 반환 → calendar 노드로
            "aggregator": "aggregator", # should_dispatch_agent가 "aggregator" 반환 → aggregator 노드로
        },
    )

    # 5개 에이전트 → aggregator 고정 연결
    # 에이전트 실행 끝나면 항상 aggregator로 감. 조건 없음
    for agent_name in ("lesson", "enrollment", "faq", "facility", "calendar"):
        g.add_edge(agent_name, "aggregator")

    g.add_conditional_edges(
        "aggregator", # aggregator 노드 끝난 후
        should_continue_after_aggregator,  # 이 함수가 방향 결정
        {
            "dispatcher": "dispatcher", # should_continue_after_aggregator가 "dispatcher" 반환 → dispatcher 노드로 (plan 남음 → dispatcher)
            "reroute": "reroute_supervisor", # should_continue_after_aggregator가 "reroute" 반환 → reroute_supervisor 노드로 (실패 → reroute_supervisor)
            "response": "response", # should_continue_after_aggregator가 "response" 반환 → response 노드로 (완료 → response)
        },
    )
    
    g.add_edge("reroute_supervisor", "dispatcher") # 재계획 끝나면 항상 dispatcher로. 조건 없음
    g.add_edge("response", END) # 응답 생성 끝나면 그래프 종료

    # 등록한 노드와 엣지를 실행 가능한 그래프로 조립해서 반환
    # chat_service.py에서 이걸 가져다가 실행함
    return g.compile()
