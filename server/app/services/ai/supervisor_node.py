"""
- supervisor_node: 사용자 질문을 분석해서 어떤 에이전트를 실행할지 계획 수립
- aggregator_node: 에이전트 실행 결과를 수집하고 성공/실패 판정
- reroute_supervisor_node: 실패 시 다른 에이전트로 재시도 (1회)
"""

import json
from typing import Any, Dict, List

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import _get_trace
from app.services.ai.llm_client import get_openai_client


_SUPERVISOR_PROMPT = """당신은 Course Agent의 Supervisor 에이전트입니다.
사용자 메시지를 분석해 어떤 서브에이전트가 응답에 필요한지 결정하세요.

에이전트 역할

lesson: Course Agent 플랫폼의 강습 검색·상세 (강습 목록, 시간표, 강사 정보)
enrollment: 로그인 사용자의 수강 현황 조회 또는 맞춤 추천
faq: 환불/결제/이용 방법/가능 여부 등 정보성 질문 (RAG)
facility: 근처 공공 체육시설 검색 (지역·좌표 기반, 외부 API)

분류 기준

direct_response: 인사·감사·잡담 — Tool 불필요, 바로 답변
single_agent: 하나의 에이전트로 답변 가능
multi_agent: 두 영역 이상의 정보가 동시에 필요한 경우
예시: "강남에서 수영 배우고 싶은데 근처 수영장도 알려줘"
→ ["lesson", "facility"]
주의: "내 수강 현황 보여주고 다음 단계 추천해줘"는 enrollment 하나로 처리 가능 → single_agent

판단 시 유의

"~해도 될까?", "~할 수 있나?" 같은 가능 여부 질문은 faq로 분류 (강습 검색 아님)
종목 + 지역이 함께 나오고 "근처", "주변", "어디", "가까운" 등이 있으면 공공 체육시설 검색 에이전트가 필요할 수 있음
단순 "추천해줘"는 enrollment (플랫폼 내 추천)
"근처 수영장", "가까운 체육관" 등은 공공 체육시설 검색 에이전트

출력 형식
반드시 아래 JSON만 응답하세요.
{
  "mode": "single_agent" | "multi_agent" | "direct_response",
  "agents": ["lesson", "facility"],
  "reason": "판단 이유 한 줄"
}

mode가 direct_response면 agents는 빈 배열 []
agents는 실행 순서대로 작성
같은 에이전트를 중복 포함하지 말 것
"""


async def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    사용자 메시지를 분석해 실행할 에이전트 계획을 결정한다.
    Langfuse generation으로 관측한다 (기존 router_node와 동일 패턴).

    실패 시 direct_response로 폴백해 파이프라인이 멈추지 않게 한다.
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

        # 파싱 및 검증
        mode = payload.get("mode", "direct_response")
        agents: List[str] = payload.get("agents") or []
        reason = payload.get("reason")

        valid_modes = {"single_agent", "multi_agent", "direct_response"}
        if mode not in valid_modes:
            mode = "direct_response"

        valid_agents = {"lesson", "enrollment", "faq", "facility"}

        # 중복 제거 + 허용 에이전트만 필터
        seen = set()
        filtered: List[str] = []
        for a in agents:
            if a in valid_agents and a not in seen:
                filtered.append(a)
                seen.add(a)
        agents = filtered

        # 무결성 체크
        if mode == "direct_response":
            agents = []
        elif mode == "single_agent":
            agents = agents[:1]  # 1개만
            if not agents:
                mode = "direct_response"
        elif mode == "multi_agent":
            if len(agents) < 2:
                # LLM이 multi라면서 1개 이하면 single로 강등
                mode = "single_agent" if agents else "direct_response"
                if mode == "single_agent":
                    agents = agents[:1]

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
    서브에이전트 실행 직후 호출된다.
    - 방금 실행된 에이전트 결과를 확인하고 is_valid 판정
    - current_agent_index를 1 증가시켜 다음 에이전트로 진행하거나 종료
    - response_node 하위 호환을 위해 tool_name, tool_result를 "메인 결과"로 재정리

    멀티모드 is_valid 정책:
    - single_agent: 방금 실행한 에이전트 결과가 유효하면 True
    - multi_agent: 지금까지 실행된 에이전트 중 하나라도 유효하면 True
                   (빈약한 에이전트가 있어도 다른 에이전트 결과로 답변 가능)
    """
    plan = state.get("agent_plan") or []
    idx = state.get("current_agent_index", 0)
    outputs = state.get("agent_outputs") or {}
    mode = state.get("routing_mode", "single_agent")

    # 방금 실행된 에이전트 이름
    just_ran = plan[idx] if idx < len(plan) else None

    # is_valid 계산
    def _is_agent_valid(name: str) -> bool:
        r = outputs.get(name) or {}
        return bool(r.get("success")) and bool(r.get("data"))

    if mode == "multi_agent":
        is_valid = any(_is_agent_valid(n) for n in plan[: idx + 1])
    else:
        is_valid = _is_agent_valid(just_ran) if just_ran else False

    # response_node 하위 호환:
    # 여러 에이전트가 실행되었을 때 tool_name/tool_result를 어느 것으로 둘지가 애매하다.
    # 정책: 유효한 결과 중 "가장 마지막에 실행된" 에이전트의 결과를 메인으로 삼는다.
    # (사용자 관점에서 최종적으로 보완된 정보가 가장 유용하다는 가정)
    main_name = None
    main_result = None
    for n in reversed(plan[: idx + 1]):
        if _is_agent_valid(n):
            main_name = n
            main_result = outputs[n]
            break
    if main_name is None and just_ran:
        # 유효한 결과가 없으면 방금 실행한 것의 실패 결과라도 담는다 (사용자에게 '결과 없음' 안내 생성용)
        main_name = just_ran
        main_result = outputs.get(just_ran)

    # Langfuse span (선택적)
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


_REROUTE_MAP = {
    "lesson": "faq",
    "faq": "lesson",
    "enrollment": "lesson",
    "facility": "lesson",
}


def reroute_supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    aggregator에서 is_valid=False로 넘어온 single_agent 케이스를 받아
    다른 에이전트로 재라우팅한다.

    설계:
    - 고정 매핑(_REROUTE_MAP)으로 다음 에이전트 결정 (LLM 호출 없음)
    - 매핑 결과가 이미 실행된 에이전트거나 없으면 재라우팅 포기(rerouting_count만 증가)
    - agent_plan에 새 에이전트를 추가하고 current_agent_index를 맞춤

    Langfuse span으로 관측한다 (왜 이 에이전트로 넘어갔는지 디버깅 가능하도록).
    """
    plan = state.get("agent_plan") or []
    outputs = state.get("agent_outputs") or {}
    current_count = state.get("rerouting_count", 0)

    tried = set(outputs.keys())

    last_agent = plan[-1] if plan else None

    next_agent = _REROUTE_MAP.get(last_agent) if last_agent else None

    if next_agent is None or next_agent in tried:
        result: Dict[str, Any] = {
            "rerouting_count": current_count + 1,
            "rerouted_from": last_agent,
        }
    else:
        new_plan = list(plan) + [next_agent]
        result = {
            "agent_plan": new_plan,
            "current_agent_index": len(plan),
            "rerouting_count": current_count + 1,
            "rerouted_from": last_agent,
        }

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
