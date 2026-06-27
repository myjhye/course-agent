"""
Supervisor 및 Rerouting 오케스트레이션 노드 정의.
사용자 요청을 해석하여 최적의 서브에이전트 실행 계획을 수립하고, 실행 결과의 유효성 검증 및 실패 시의 대체 라우팅을 관리한다.
"""

import json
from typing import Any, Dict, List

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import _get_trace
from app.services.ai.llm_client import get_openai_client


# Supervisor LLM(GPT-4o-mini)에 인스트럭션으로 전송될 시스템 프롬프트.
# 입력 인텐트에 따라 적합한 서브에이전트 목록을 도출하고 단일(single_agent), 멀티(multi_agent), 직접 응답(direct_response) 모드를 정의한다.
_SUPERVISOR_PROMPT = """당신은 Course Agent의 Supervisor 에이전트입니다.
사용자 메시지를 분석해 어떤 서브에이전트가 응답에 필요한지 결정하세요.

에이전트 역할

lesson: Course Agent 플랫폼의 강습 검색·상세 (강습 목록, 시간표, 강사 정보)
enrollment: 로그인 사용자의 수강 신청 처리, 수강 신청 성공 결과 보고, 내 수강 목록/출석률 조회 또는 플랫폼 추천 강습 조회
faq: 환불/결제/이용 방법/가능 여부 등 정보성 질문 (RAG)
facility: 근처 공공 체육시설 검색 (지역·좌표 기반, 외부 API)
calendar: 구글 캘린더 일정 관리 (구글 캘린더에 예약 등록, 일정 생성, 캘린더 조회, 또는 내일/금주의 스케줄 확인)

분류 기준

direct_response: 인사·감사·잡담 — Tool 불필요, 바로 답변
single_agent: 하나의 에이전트로 답변 가능
multi_agent: 두 영역 이상의 정보가 동시에 필요한 경우
예시: "강남에서 수영 배우고 싶은데 근처 수영장도 알려줘"
→ ["lesson", "facility"]
주의: "내 수강 현황 보여주고 다음 단계 추천해줘"는 enrollment 하나로 처리 가능 → single_agent

판단 시 유의 (중요)

1. "캘린더", "일정", "스케줄", "달력", "예약 확인/등록" 등의 단어가 메시지에 포함되거나, 특정 일시(예: '내일 10시', '금요일 3시')를 지정해 일정을 기록/조회하려는 흐름은 반드시 calendar 에이전트로 라우팅하세요.
   - 예: "내일 일정 알려줘", "내일 스케줄 확인해줘", "금요일 3시에 테니스 일정 등록해줘" -> calendar 단일 에이전트
2. 단순히 플랫폼 내 특정 스포츠 강습 과목을 신청/등록하려는 질문(예: '수영 초급반 등록해줘', '수강 신청해줘')은 enrollment 에이전트로 보냅니다.
3. "~해도 될까?", "~할 수 있나?" 같은 규정 가능 여부 질문은 faq로 분류 (강습 검색 아님)
4. 종목 + 지역이 함께 나오고 "근처", "주변", "어디", "가까운" 등이 있으면 공공 체육시설 검색 에이전트(facility)가 필요할 수 있음

출력 형식
반드시 아래 JSON만 응답하세요.
{
  "mode": "single_agent" | "multi_agent" | "direct_response",
  "agents": ["lesson", "facility", "calendar"],
  "reason": "판단 이유 한 줄"
}

mode가 direct_response면 agents는 빈 배열 []
agents는 실행 순서대로 작성
같은 에이전트를 중복 포함하지 말 것
"""


async def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    사용자 입력 메시지를 분석하여 실행할 서브에이전트 목록과 동작 모드 계획을 수립한다.
    - LLM 호출을 통해 JSON 형태로 모드(mode) 및 대상 에이전트 목록(agents)을 추론한다.
    - 획득한 결과에 대해 유효한 모드 검증 및 대상 서브에이전트 유효성 필터링을 방어적으로 수행한다.
    - Langfuse 모니터링을 위해 generation 관측치를 기록한다.
    """
    client = get_openai_client()
    trace = _get_trace()
    prompt = _SUPERVISOR_PROMPT

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": state["user_message"]},
    ]

    try:
        if trace:
            # Langfuse가 활성화된 경우 생성(generation) 정보 및 메타데이터 트래킹 수행
            obs_kwargs: Dict[str, Any] = {
                "as_type": "generation",
                "name": "supervisor",
                "model": "gpt-4o-mini",
                "input": {
                    "system": prompt,
                    "user": state["user_message"],
                },
            }
            trace_id = state.get("trace_id")
            if trace_id:
                obs_kwargs["metadata"] = {"trace_id": trace_id}

            with trace.start_as_current_observation(**obs_kwargs) as gen:
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0,
                    max_tokens=200,
                    response_format={"type": "json_object"},
                )
                tokens = (
                    response.usage.total_tokens
                    if getattr(response, "usage", None)
                    else 0
                )
                payload = json.loads(response.choices[0].message.content)
                gen.update(output=payload, usage_details={"total_tokens": tokens})
        else:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            tokens = (
                response.usage.total_tokens
                if getattr(response, "usage", None)
                else 0
            )
            payload = json.loads(response.choices[0].message.content)

        mode = payload.get("mode", "direct_response")
        agents: List[str] = payload.get("agents") or []
        reason = payload.get("reason")

        # 허용 모드 값에 대한 무결성 보정
        valid_modes = {"single_agent", "multi_agent", "direct_response"}
        if mode not in valid_modes:
            mode = "direct_response"

        # 사전에 약속된 서브에이전트 화이트리스트
        valid_agents = {"lesson", "enrollment", "faq", "facility", "calendar"}

        # 중복 에이전트 제거 및 유효하지 않은 임의의 텍스트가 섞여 들어오는 것을 방지
        seen = set()
        filtered: List[str] = []
        for a in agents:
            if a in valid_agents and a not in seen:
                filtered.append(a)
                seen.add(a)
        agents = filtered

        # 동작 모드 유형별 무결성 강제 매핑 규칙 적용
        if mode == "direct_response":
            agents = []
        elif mode == "single_agent":
            agents = agents[:1]
            if not agents:
                mode = "direct_response"
        elif mode == "multi_agent":
            if len(agents) < 2:
                mode = "single_agent" if agents else "direct_response"
                if mode == "single_agent":
                    agents = agents[:1]

        # 디스패치 노드에서 처리할 전역 에이전트 실행 계획 세팅
        return {
            "routing_mode": mode,
            "agent_plan": agents,
            "current_agent_index": 0,
            "agent_outputs": {},
            "handoff_reason": reason,
            "rerouting_count": 0,
            "total_tokens": state.get("total_tokens", 0) + tokens,
        }

    except Exception as e:
        print(f"[Supervisor] 에러: {e}")
        return {
            "routing_mode": "direct_response",
            "agent_plan": [],
            "current_agent_index": 0,
            "agent_outputs": {},
            "handoff_reason": None,
            "rerouting_count": 0,
            "total_tokens": state.get("total_tokens", 0),
            "error": str(e),
        }


def aggregator_node(state: AgentState) -> Dict[str, Any]:
    """
    서브에이전트 동작이 끝난 직후 실행되어, 각 에이전트의 실행 결과를 취합하고 성공/실패 여부를 판정한다.
    - 성공 판정 기준: success=True 이며 data 필드 내 실제 결과가 존재할 것.
    - 멀티 에이전트 모드일 경우 실행 계획 중 하나라도 유효한 결과를 가지면 전체 흐름을 성공(is_valid=True)으로 취급한다.
    - 단일 에이전트 모드일 경우 방금 실행된 에이전트의 성공 여부로 판정한다.
    - 응답 생성 노드(response_node)에 연계할 '대표 결과(main_result)'를 선정하며, 유효한 결과가 없다면 최종 실패한 결과의 에러 정보를 할당한다.
    """
    plan = state.get("agent_plan") or []
    idx = state.get("current_agent_index", 0)
    outputs = state.get("agent_outputs") or {}
    mode = state.get("routing_mode", "single_agent")

    just_ran = plan[idx] if idx < len(plan) else None

    # 성공 조건 검증 헬퍼
    def _is_agent_valid(name: str) -> bool:
        r = outputs.get(name) or {}
        return bool(r.get("success")) and bool(r.get("data"))

    # 멀티에이전트와 단일 에이전트 시나리오별 성공 여부 식별
    if mode == "multi_agent":
        is_valid = any(_is_agent_valid(n) for n in plan[: idx + 1])
    else: 
        is_valid = _is_agent_valid(just_ran) if just_ran else False

    # 여러 실행 이력 중 최종적으로 유효한 가장 마지막 결과물을 사용자 응답 연계용 메인으로 지정
    main_name = None
    main_result = None
    for n in reversed(plan[: idx + 1]):
        if _is_agent_valid(n):
            main_name = n
            main_result = outputs[n]
            break
    if main_name is None and just_ran:
        # 매칭되는 유효 데이터가 전부 없더라도 실패 이유 가이드를 생성하기 위해 최종 실행 정보를 바인딩
        main_name = just_ran
        main_result = outputs.get(just_ran)

    # Langfuse 수집 기능 등록
    trace = _get_trace()
    if trace:
        try:
            span_kwargs: Dict[str, Any] = {
                "as_type": "span",
                "name": "aggregator",
                "input": {
                    "mode": mode,
                    "plan": plan,
                    "current_index": idx,
                    "just_ran": just_ran,
                },
            }
            trace_id = state.get("trace_id")
            if trace_id:
                span_kwargs["metadata"] = {"trace_id": trace_id}
            with trace.start_as_current_observation(**span_kwargs) as span:
                span.update(
                    output={
                        "is_valid": is_valid,
                        "main_agent": main_name,
                        "next_index": idx + 1,
                    }
                )
        except Exception:
            pass

    return {
        "current_agent_index": idx + 1,
        "is_valid": is_valid,
        "tool_name": main_name,
        "tool_result": main_result,
    }


# 단일 서브에이전트 실행 결과가 실패(is_valid=False)했을 때, 교차 재시도를 수행할 대체 서브에이전트 매핑 테이블.
# 예: 강습(lesson) 실패 시 faq로 전환, 수강 조회/추천(enrollment) 및 체육시설(facility) 등 실패 시 lesson으로 전환.
_REROUTE_MAP = {
    "lesson": "faq",
    "faq": "lesson",
    "enrollment": "lesson",
    "facility": "lesson",
    "calendar": "lesson",
}


def reroute_supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    1차 서브에이전트 실행이 실패한 경우, 사전에 정의된 재라우팅 맵(_REROUTE_MAP)을 기반으로 대체 에이전트를 자동 편성한다.
    - 무한 루프를 방지하기 위해 이미 실행을 시도했던 에이전트는 제외한다.
    - 대체 에이전트가 존재하고 실행 이력이 없다면 실행 계획(agent_plan) 뒤에 덧붙이고, 실행 인덱스(current_agent_index)를 업데이트하여 재시도를 진행한다.
    """
    plan = state.get("agent_plan") or []
    outputs = state.get("agent_outputs") or {}
    current_count = state.get("rerouting_count", 0)

    tried = set(outputs.keys())
    last_agent = plan[-1] if plan else None
    next_agent = _REROUTE_MAP.get(last_agent) if last_agent else None

    # 매핑 데이터가 부재하거나 이미 교차 실행을 수행한 이력이 있으면 재라우팅 실패 처리 및 대기
    if next_agent is None or next_agent in tried:
        result: Dict[str, Any] = {
            "rerouting_count": current_count + 1,
            "rerouted_from": last_agent,
        }
    else:
        # 신규 폴백 에이전트를 추가로 지정하고 인덱스 갱신을 통해 라우팅 제어권 전환
        new_plan = list(plan) + [next_agent]
        result = {
            "agent_plan": new_plan,
            "current_agent_index": len(plan),
            "rerouting_count": current_count + 1,
            "rerouted_from": last_agent,
        }

    # Langfuse 수집 기능 등록
    trace = _get_trace()
    if trace:
        try:
            span_kwargs: Dict[str, Any] = {
                "as_type": "span",
                "name": "reroute_supervisor",
                "input": {
                    "last_agent": last_agent,
                    "tried": list(tried),
                    "rerouting_count": current_count,
                },
            }
            trace_id = state.get("trace_id")
            if trace_id:
                span_kwargs["metadata"] = {"trace_id": trace_id}
            with trace.start_as_current_observation(**span_kwargs) as span:
                span.update(
                    output={
                        "next_agent": next_agent
                        if next_agent is not None and next_agent not in tried
                        else None,
                        "gave_up": next_agent is None or next_agent in tried,
                    }
                )
        except Exception:
            pass

    return result

