"""
supervisor, aggregator, reroute_supervisor 노드 함수 정의.

- supervisor_node     : 사용자 질문 분석 → 어떤 에이전트를 실행할지 계획 수립
- aggregator_node     : 에이전트 결과 수집 → 성공/실패 판정
- reroute_supervisor_node : 실패 시 다른 에이전트로 재시도 결정 (1회)
"""

import json
from typing import Any, Dict, List

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import _get_trace
from app.services.ai.llm_client import get_openai_client


# supervisor가 GPT에게 넘기는 시스템 프롬프트.
# 사용자 질문을 보고 어떤 에이전트를 써야 하는지 JSON으로 반환하도록 지시한다.
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
    사용자 질문을 GPT-4o-mini로 분석해서 어떤 에이전트를 실행할지 계획을 수립한다.
    결과를 state에 저장하면 dispatcher가 읽어서 에이전트를 순서대로 실행한다.

    GPT 응답에 허용되지 않은 에이전트 이름이나 잘못된 mode가 오면 방어 처리로 걸러낸다.
    예외 발생 시 direct_response로 강제해서 에러가 사용자에게 노출되지 않게 한다.
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
            # Langfuse에 supervisor LLM 호출 기록 (어떤 질문이 어떤 계획으로 이어졌는지 추적)
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
                    temperature=0,       # 항상 일관된 판단
                    max_tokens=200,      # JSON 짧으니까 200으로 충분
                    response_format={"type": "json_object"},  # JSON만 반환하도록 강제
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

        # 허용되지 않은 mode면 direct_response로 강제
        valid_modes = {"single_agent", "multi_agent", "direct_response"}
        if mode not in valid_modes:
            mode = "direct_response"

        # 허용된 에이전트 이름만 통과. GPT가 잘못된 이름을 반환할 수 있어서 방어 처리
        valid_agents = {"lesson", "enrollment", "faq", "facility", "calendar"}
        seen = set()
        filtered: List[str] = []
        for a in agents:
            if a in valid_agents and a not in seen:
                filtered.append(a)
                seen.add(a)
        agents = filtered

        # mode별 무결성 보정
        if mode == "direct_response":
            agents = []  # direct면 에이전트 필요 없음
        elif mode == "single_agent":
            agents = agents[:1]  # single이면 1개만
            if not agents:
                mode = "direct_response"  # 에이전트 없으면 direct로 강등
        elif mode == "multi_agent":
            if len(agents) < 2:
                # multi라면서 에이전트가 1개 이하면 single로 강등
                mode = "single_agent" if agents else "direct_response"
                if mode == "single_agent":
                    agents = agents[:1]

        return {
            "routing_mode": mode,        # dispatcher가 읽어서 분기
            "agent_plan": agents,        # 실행할 에이전트 목록. 예: ["lesson", "faq"]
            "current_agent_index": 0,    # 첫 번째 에이전트부터 시작
            "agent_outputs": {},         # 에이전트 결과 저장용 초기화
            "handoff_reason": reason,    # GPT가 설명한 판단 이유
            "rerouting_count": 0,        # 재라우팅 횟수 초기화
            "total_tokens": state.get("total_tokens", 0) + tokens,
        }

    except Exception as e:
        # 예외 발생 시 direct_response로 강제. 에러가 사용자에게 노출되지 않게 한다
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
    에이전트 실행이 끝날 때마다 호출된다.
    결과를 수집하고 is_valid를 판정한 뒤 current_agent_index를 올린다.

    성공 기준: success=True이고 data가 있어야 유효.
    - 싱글 에이전트: 방금 실행한 에이전트 결과만 판정
    - 멀티 에이전트: 지금까지 실행된 에이전트 중 하나라도 유효하면 True
      (lesson 성공, facility 실패여도 lesson 결과로 답변할 수 있어서)
    """
    plan = state.get("agent_plan") or []
    idx = state.get("current_agent_index", 0)
    outputs = state.get("agent_outputs") or {}
    mode = state.get("routing_mode", "single_agent")

    just_ran = plan[idx] if idx < len(plan) else None

    def _is_agent_valid(name: str) -> bool:
        r = outputs.get(name) or {}
        return bool(r.get("success")) and bool(r.get("data"))

    if mode == "multi_agent":
        is_valid = any(_is_agent_valid(n) for n in plan[: idx + 1])
    else:
        is_valid = _is_agent_valid(just_ran) if just_ran else False

    # response_node에 넘길 대표 결과 선정. 유효한 결과 중 가장 마지막에 실행된 것
    main_name = None
    main_result = None
    for n in reversed(plan[: idx + 1]):
        if _is_agent_valid(n):
            main_name = n
            main_result = outputs[n]
            break
            
    if main_name is None and just_ran:
        # 매칭되는 유효 데이터가 전부 없더라도 실패 이유 생성을 위해 최종 실행 정보를 넘겨준다
        main_name = just_ran
        main_result = outputs.get(just_ran)

    # Langfuse에 aggregator 실행 기록
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


# 1차 에이전트 실행이 실패했을 때, 교차 재시도할 에이전트 매핑
_REROUTE_MAP = {
    "lesson": "faq",
    "faq": "lesson",
    "enrollment": "lesson",
    "facility": "lesson",
    "calendar": "lesson",
}


def reroute_supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    1차 에이전트 실행이 실패한 경우, 다른 에이전트로 교차 재시도를 결정한다.
    - 무한 루프를 방지하기 위해 이미 실행을 시도했던 에이전트는 제외한다.
    - 대체 에이전트가 존재하고 실행 이력이 없다면 실행 계획(agent_plan) 뒤에 덧붙이고, 인덱스를 조정한다.
    """
    plan = state.get("agent_plan") or []
    outputs = state.get("agent_outputs") or {}
    current_count = state.get("rerouting_count", 0)

    tried = set(outputs.keys())
    last_agent = plan[-1] if plan else None
    next_agent = _REROUTE_MAP.get(last_agent) if last_agent else None

    # 이미 실행해 본 에이전트거나 매핑이 없으면 재시도 포기
    if next_agent is None or next_agent in tried:
        result: Dict[str, Any] = {
            "rerouting_count": current_count + 1,
            "rerouted_from": last_agent,
        }
    else:
        # 계획 뒤에 새 에이전트를 추가하고, 인덱스를 그 에이전트 위치로 조정
        new_plan = list(plan) + [next_agent]
        result = {
            "agent_plan": new_plan,
            "current_agent_index": len(plan),
            "rerouting_count": current_count + 1,
            "rerouted_from": last_agent,
        }

    # Langfuse에 reroute_supervisor 실행 기록
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


