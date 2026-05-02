"""
GPT가 질문을 분석해서 어떤 에이전트를 실행할지 결정하고, 
결과를 수집해서 성공/실패를 판정하고, 
실패하면 다른 에이전트로 재시도

- supervisor_node: 사용자 질문을 분석해서 어떤 에이전트를 실행할지 계획 수립
- aggregator_node: 에이전트 실행 결과를 수집하고 성공/실패 판정
- reroute_supervisor_node: 실패 시 다른 에이전트로 재시도 (1회)
"""

import json
from typing import Any, Dict, List

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import _get_trace
from app.services.ai.llm_client import get_openai_client


# GPT-4o-mini에게 주는 지시문
# "너는 supervisor야. 사용자 질문 보고 어떤 에이전트를 써야 하는지 JSON으로 답해"
# GPT가 아래 형식으로 반환하면 supervisor_node가 읽어서 agent_plan을 만듦
#
# {
#   "mode": "single_agent",
#   "agents": ["lesson"],
#   "reason": "강습 검색 요청"
# }
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
    # 사용자 질문을 GPT-4o-mini로 분석해서 어떤 에이전트를 실행할지 계획 수립
    # 결과를 state에 저장해서 다음 노드(dispatcher)가 읽어감

    client = get_openai_client() # OpenAI 클라이언트 가져오기
    trace = _get_trace() # Langfuse 추적 객체 가져오기 (없으면 None)
    prompt = _SUPERVISOR_PROMPT # GPT에게 줄 지시문

    # GPT에게 보낼 메시지 구성
    messages = [
        {"role": "system", "content": prompt}, # 역할 지시
        {"role": "user", "content": state["user_message"]}, # 사용자 질문
    ]

    try:
        if trace:
            # Langfuse가 있으면 GPT 호출을 generation으로 기록
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
                    temperature=0, # 항상 일관된 판단
                    max_tokens=200, # JSON 짧으니까 200으로 충분
                    response_format={"type": "json_object"}, # JSON만 반환하도록 강제
                )
                tokens = (
                    response.usage.total_tokens
                    if getattr(response, "usage", None)
                    else 0
                )
                payload = json.loads(response.choices[0].message.content) # JSON 문자열 → 딕셔너리
                gen.update(output=payload, usage_details={"total_tokens": tokens}) # Langfuse에 결과 기록
        else:
            # Langfuse 없으면 그냥 GPT 호출만
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

        # GPT 응답에서 값 꺼내기
        mode = payload.get("mode", "direct_response") # "single_agent" | "multi_agent" | "direct_response"
        agents: List[str] = payload.get("agents") or [] # 실행할 에이전트 목록
        reason = payload.get("reason") # GPT가 설명한 판단 이유

        # mode가 허용된 값인지 확인. 이상한 값이면 direct_response로 강제
        valid_modes = {"single_agent", "multi_agent", "direct_response"}
        if mode not in valid_modes:
            mode = "direct_response"

        # 허용된 에이전트 목록
        valid_agents = {"lesson", "enrollment", "faq", "facility"}

        # 중복 제거 + 허용된 에이전트만 필터 (GPT가 잘못된 값 반환할 수 있어서 방어 처리)
        seen = set()
        filtered: List[str] = []
        for a in agents:
            if a in valid_agents and a not in seen:
                filtered.append(a)
                seen.add(a)
        agents = filtered

        # mode별 무결성 체크
        if mode == "direct_response":
            agents = [] # direct면 에이전트 필요 없음
        elif mode == "single_agent":
            agents = agents[:1]  # single이면 1개만
            if not agents:
                mode = "direct_response" # 에이전트가 없으면 direct로 강등
        elif mode == "multi_agent":
            if len(agents) < 2:
                # LLM이 multi라면서 1개 이하면 single로 강등
                mode = "single_agent" if agents else "direct_response"
                if mode == "single_agent":
                    agents = agents[:1]

        # 다음 노드들이 읽어갈 계획을 state에 저장
        return {
            "routing_mode": mode, # "single_agent" | "multi_agent" | "direct_response"
            "agent_plan": agents, # 실행할 에이전트 목록
            "current_agent_index": 0, # 현재 실행 중인 에이전트 인덱스 (0부터 시작)
            "agent_outputs": {}, # 각 에이전트 결과 저장용
            "handoff_reason": reason, # GPT가 설명한 판단 이유
            "rerouting_count": 0, # 재라우팅 횟수 (0=첫 실행)
            "total_tokens": state.get("total_tokens", 0) + tokens, # 총 토큰 사용량
        }

    except Exception as e:
        # 예외 발생 시 direct_response로 강제
        print(f"[Supervisor] 에러: {e}")
        return {
            "routing_mode": "direct_response", # 에러 발생 시 direct_response로 강제
            "agent_plan": [], # 에이전트 계획 비움
            "current_agent_index": 0, # 현재 실행 중인 에이전트 인덱스 초기화
            "agent_outputs": {}, # 각 에이전트 결과 비움
            "handoff_reason": None, # 판단 이유 비움
            "rerouting_count": 0, # 재라우팅 횟수 초기화
            "total_tokens": state.get("total_tokens", 0), # 총 토큰 사용량 유지
            "error": str(e), # 에러 메시지
        }


def aggregator_node(state: AgentState) -> Dict[str, Any]:
    # 에이전트 실행 직후 호출
    # 결과 수집 + 성공/실패 판정 + 인덱스 증가
    plan = state.get("agent_plan") or [] # 전체 실행 계획
    idx = state.get("current_agent_index", 0) # 현재 실행 중인 에이전트 인덱스
    outputs = state.get("agent_outputs") or {} # 지금까지 실행된 에이전트 결과들
    mode = state.get("routing_mode", "single_agent") # single / multi 구분

    # 방금 실행된 에이전트 이름 (예: "lesson")
    just_ran = plan[idx] if idx < len(plan) else None

    # 해당 에이전트 결과가 유효한지 확인
    # success=True + data가 있어야 유효
    def _is_agent_valid(name: str) -> bool:
        r = outputs.get(name) or {}
        return bool(r.get("success")) and bool(r.get("data"))

     # multi: 지금까지 실행된 에이전트 중 하나라도 유효하면 True (하나가 실패해도 다른 에이전트 결과로 답변 가능)
    if mode == "multi_agent":
        is_valid = any(_is_agent_valid(n) for n in plan[: idx + 1])
    # single: 방금 실행한 에이전트 결과만 판정
    else: 
        is_valid = _is_agent_valid(just_ran) if just_ran else False

    # 메인 결과 선정
    # 여러 에이전트가 실행됐을 때 response_node에 넘길 대표 결과 1개를 고름
    # 정책: 유효한 결과 중 가장 마지막에 실행된 에이전트 결과를 메인으로
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

    # Langfuse에 aggregator 실행 기록 (없으면 스킵)
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
            pass # Langfuse 오류가 메인 흐름을 막으면 안 되므로 무시

    return {
        "current_agent_index": idx + 1, # 인덱스 증가 → 다음 에이전트로 이동
        "is_valid": is_valid, # should_continue_after_aggregator가 읽어서 분기
        "tool_name": main_name, # response_node가 읽어서 응답 생성에 사용
        "tool_result": main_result, # response_node가 읽어서 응답 생성에 사용
    }


_REROUTE_MAP = {
    "lesson": "faq", # lesson 실패 → faq로 재시도
    "faq": "lesson", # faq 실패 → lesson으로 재시도
    "enrollment": "lesson", # enrollment 실패 → lesson으로 재시도
    "facility": "lesson", # facility 실패 → lesson으로 재시도
}


def reroute_supervisor_node(state: AgentState) -> Dict[str, Any]:
    # single_agent 실패 시 _REROUTE_MAP을 보고 다른 에이전트로 재시도
    # LLM 호출 없이 고정 매핑으로 결정 (빠르고 단순)
    plan = state.get("agent_plan") or [] # 현재 실행 계획
    outputs = state.get("agent_outputs") or {} # 지금까지 실행된 에이전트 결과들
    current_count = state.get("rerouting_count", 0) # 현재 재시도 횟수

    tried = set(outputs.keys()) # 이미 실행한 에이전트 목록 (같은 에이전트 중복 실행 방지)

    last_agent = plan[-1] if plan else None # 방금 실패한 에이전트 이름 (예: "lesson")

    next_agent = _REROUTE_MAP.get(last_agent) if last_agent else None # 매핑에서 다음 에이전트 결정 (예: "lesson" → "faq")

    # 매핑에 없거나 이미 실행한 에이전트면 재시도 포기
    # rerouting_count만 올리고 plan은 그대로 둠
    if next_agent is None or next_agent in tried:
        result: Dict[str, Any] = {
            "rerouting_count": current_count + 1,
            "rerouted_from": last_agent,
        }
    else:
        # 재시도할 에이전트를 plan 뒤에 추가
        # current_agent_index를 새 에이전트 위치로 맞춤
        new_plan = list(plan) + [next_agent]
        result = {
            "agent_plan": new_plan, # 예: ["lesson"] → ["lesson", "faq"]
            "current_agent_index": len(plan), # 새 에이전트 인덱스로 이동
            "rerouting_count": current_count + 1, # 재시도 횟수 증가
            "rerouted_from": last_agent, # 어디서 넘어왔는지 기록
        }

    # Langfuse에 reroute 실행 기록 (없으면 스킵)
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
            pass # Langfuse 오류가 메인 흐름을 막으면 안 되므로 무시

    return result
