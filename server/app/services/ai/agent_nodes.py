"""
LangGraph 에이전트 노드 함수들.

각 함수는 AgentState를 받아 부분적으로 업데이트된 dict를 반환한다.
LangGraph가 이를 기존 상태에 merge한다.
"""

import json
from typing import Dict, Any, Optional, AsyncGenerator

from app.services.ai.agent_state import AgentState
from app.services.ai.llm_client import get_openai_client
from app.services.ai.tool_executor import ToolExecutor
from app.services.ai.langfuse_client import get_langfuse


def _get_trace():
    """
    Langfuse 클라이언트를 반환한다.

    - 설정이 없으면 None
    - 각 노드는 state["trace_id"]를 metadata로만 활용한다.
    """
    return get_langfuse()


# ============================================================
# 1. Router 노드: 의도 분류
# ============================================================

ROUTER_SYSTEM_PROMPT = """사용자의 메시지를 분석하여 의도를 분류하세요.

반드시 아래 5가지 중 하나만 JSON으로 응답하세요:

1. "search_lessons" - 특정 종목/조건으로 **강습 목록을 검색**하려는 경우
   예: "수영 강습 알려줘", "초급 요가 있어?", "골프 배우고 싶어", "테니스 강습 추천해줘"
   **단, 아래는 search_lessons가 아님 → faq_inquiry로 분류:**
   - "~해도 괜찮을까?", "~할 수 있을까?", "~해도 되나요?" 같은 **정보/안내를 묻는 질문**
   - 종목이 언급되더라도 "물이 무서운데 수영 배울 수 있어?", "허리 아픈데 요가 해도 될까?"처럼 **가능 여부·조건·우려**를 물을 때
   → 이런 질문은 강습 검색이 아니라 faq_inquiry(지식/FAQ 검색)로 분류하세요.
   
2. "get_recommendations" - 특정 종목 없이 일반적인 추천을 요청하는 경우
   예: "추천해줘", "뭐 들을까", "나한테 맞는 강습"
   
3. "manage_enrollment" - 수강 현황 조회, 수강 관련 문의
   예: "내 수강 현황", "지금 뭐 듣고 있어", "수강 중인 강습"
   
4. "faq_inquiry" - **정보·안내·가능 여부**를 묻는 질문 (환불/결제/이용 방법 포함)
   예: "환불 어떻게 해?", "결제 방법", "수료증", "물 무서운데 수영 배울 수 있어?", "허리 아픈데 요가 해도 될까?", "운동 초보인데 PT 받을 수 있어?"
   
5. "general_inquiry" - 인사, 감사, 잡담 등 Tool이 필요 없는 경우
   예: "안녕", "고마워", "오늘 날씨 좋다"

{"intent": "분류결과"}"""


async def router_node(state: AgentState) -> Dict[str, Any]:
    """
    사용자 의도를 LangGraph 파이프라인의 5가지 분기 중 하나로 분류한다.

    이 단계에서 intent를 잘못 분류하면 이후 Tool 선택과 재시도 전략이 모두 틀어지므로,
    Langfuse generation으로 별도 관측을 남겨 나중에 "왜 이 의도로 갔는지"를 추적할 수 있게 한다.
    """

    client = get_openai_client()
    trace = _get_trace()

    try:
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": state["user_message"]},
        ]

        if trace:
            # Router 단계도 별도 generation으로 남겨, 잘못된 의도 분류 문제를 나중에 분석할 수 있게 한다
            obs_kwargs: Dict[str, Any] = {
                "as_type": "generation",
                "name": "router",
                "model": "gpt-4o-mini",
                "input": {
                    "system": ROUTER_SYSTEM_PROMPT,
                    "user": state["user_message"],
                },
            }
            trace_id = state.get("trace_id")
            if trace_id:
                obs_kwargs["metadata"] = {"trace_id": trace_id}

            with trace.start_as_current_observation(**obs_kwargs) as gen:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0,
                    max_tokens=50,
                    response_format={"type": "json_object"},
                )

                tokens = (
                    response.usage.total_tokens
                    if getattr(response, "usage", None)
                    else 0
                )
                result = json.loads(response.choices[0].message.content)

                gen.update(
                    output=result,
                    usage_details={"total_tokens": tokens},
                )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0,
                max_tokens=50,
                response_format={"type": "json_object"},
            )
            tokens = (
                response.usage.total_tokens
                if getattr(response, "usage", None)
                else 0
            )
            result = json.loads(response.choices[0].message.content)

        # LLM이 JSON으로 반환한 payload에서 의도 문자열만 꺼낸다.
        # 혹시라도 스키마가 깨지거나 키가 없을 경우를 대비해 general_inquiry로 폴백한다.
        intent = result.get("intent", "general_inquiry")

        valid_intents = {
            "search_lessons",
            "get_recommendations",
            "manage_enrollment",
            "faq_inquiry",
            "general_inquiry",
        }
        # 모델이 오타나 예상치 못한 문자열을 반환하는 경우가 있어,
        # 사전에 허용된 intent 집합에 없으면 안전하게 general_inquiry로 강제한다.
        if intent not in valid_intents:
            intent = "general_inquiry"

        return {
            "intent": intent,
            "total_tokens": state.get("total_tokens", 0) + tokens,
        }

    except Exception as e:
        print(f"[Router] 에러: {e}")
        return {
            "intent": "general_inquiry",
            "error": str(e),
        }


# ============================================================
# 2. Tool Executor 노드: 의도에 따라 Tool 실행
# ============================================================

async def tool_executor_node(state: AgentState, db) -> Dict[str, Any]:
    """
    Router가 분류한 의도에 따라 적절한 비즈니스 도구(강습 검색, FAQ 검색 등)를 호출한다.

    LangGraph의 Tool 호출을 한 곳에서 중앙집중적으로 관리함으로써:
    - 어떤 intent가 어떤 도구로 매핑되는지 한눈에 파악할 수 있고,
    - 재시도 전략(retry_strategy)에 따라 인자를 어떻게 완화/변형하는지도 한 곳에서 제어할 수 있다.
    """

    # ToolExecutor에 trace_id를 넘겨두면, 내부에서 호출하는 RAG/DB 로직이
    # 같은 Langfuse Trace 아래에 묶여 end-to-end 호출 경로를 재현할 수 있다.
    executor = ToolExecutor(db, trace_id=state.get("trace_id"))
    client = get_openai_client()
    intent = state["intent"]
    student_name = state.get("student_name")
    retry_count = state.get("retry_count", 0)

    # intent마다 전혀 다른 도구와 인자 스키마를 사용하므로, 여기서 명시적으로 분기해준다.
    if intent == "search_lessons":
        tool_name = "search_lessons"
        tool_args = await _extract_search_args(client, state)

        # 재시도 시 필터 완화:
        # 첫 시도에서 조건을 너무 빡세게 걸어 결과가 없으면, difficulty/target_audience를 풀어
        # "아무 강습도 못 찾았다" 보다는 "조건을 조금 완화한 대안"을 제시하는 것이 UX 상 낫기 때문이다.
        if retry_count > 0 and state.get("retry_strategy") == "relax_filters":
            tool_args = {
                "sport_type": tool_args.get("sport_type"),
                "keyword": tool_args.get("keyword"),
            }

    elif intent == "get_recommendations":
        tool_name = "get_recommendations"
        tool_args = {"student_name": student_name}

    elif intent == "manage_enrollment":
        tool_name = "get_my_enrollments"
        tool_args = {"student_name": student_name}

    elif intent == "faq_inquiry":
        tool_name = "search_faq"
        tool_args = await _extract_faq_keyword(client, state)

    else:
        # general_inquiry — Tool 실행 불필요:
        # 간단한 인사/감사/잡담에는 DB/RAG를 호출하지 않고 곧바로 Response 노드에서 답을 생성해
        # 토큰과 레이턴시를 모두 절감한다.
        return {
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
        }

    if student_name and tool_name in ("get_my_enrollments", "get_recommendations"):
        # Router/LLM가 인자에서 student_name을 누락해도,
        # 이미 인증된 세션이라면 도구 인자에 강제로 주입해 "내 수강 현황"이 항상 로그인 사용자 기준이 되게 한다.
        tool_args["student_name"] = student_name

    trace = _get_trace()

    if trace:
        # 각 툴 실행을 별도 span으로 남기는 이유:
        # - 어떤 intent/도구 조합이 자주 실패하거나 느린지 Langfuse에서 바로 파악할 수 있고,
        # - 특정 도구의 인자 설계가 잘못돼 있는지를 end-to-end Trace에서 역추적할 수 있다.
        span_kwargs: Dict[str, Any] = {
            "as_type": "span",
            "name": "tool_executor",
            "input": {
                "tool_name": tool_name,
                "tool_args": tool_args,
            },
        }
        trace_id = state.get("trace_id")
        if trace_id:
            span_kwargs["metadata"] = {"trace_id": trace_id}

        try:
            # Langfuse 관측이 활성화된 경우: 툴 실행 전체를 하나의 span으로 감싸고 결과를 output에 기록한다.
            with trace.start_as_current_observation(**span_kwargs) as span:
                try:
                    tool_result = await executor.execute(tool_name, tool_args)
                except Exception as e:
                    print(f"[ToolExecutor] {tool_name} 실행 에러: {e}")
                    tool_result = {"success": False, "error": str(e)}

                span.update(output=tool_result)
        except Exception:
            # Langfuse SDK나 네트워크 문제로 관측이 실패해도, 실제 비즈니스 로직이 멈추면 안 되기 때문에
            # 동일한 툴 실행을 관측 없이 한 번 더 시도한다.
            try:
                tool_result = await executor.execute(tool_name, tool_args)
            except Exception as e:
                print(f"[ToolExecutor] {tool_name} 실행 에러: {e}")
                tool_result = {"success": False, "error": str(e)}
    else:
        try:
            tool_result = await executor.execute(tool_name, tool_args)
        except Exception as e:
            print(f"[ToolExecutor] {tool_name} 실행 에러: {e}")
            tool_result = {"success": False, "error": str(e)}

    # 한 번의 채팅에서 어떤 도구들이 몇 번 호출됐는지 추후 분석/로그를 위해 누적한다.
    tools_used = list(state.get("tools_used", []))
    tools_used.append(tool_name)

    # iteration 별 툴 결과를 키(`tool_name_1`, `tool_name_2`) 형식으로 저장해,
    # "첫 검색 vs 재검색" 결과를 Langfuse/대시보드에서 비교 분석하기 쉽게 한다.
    all_tool_results = dict(state.get("all_tool_results", {}))
    iteration = retry_count + 1
    all_tool_results[f"{tool_name}_{iteration}"] = tool_result

    return {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "tool_result": tool_result,
        "tools_used": tools_used,
        "all_tool_results": all_tool_results,
    }


async def _extract_search_args(client, state: AgentState) -> Dict[str, Any]:
    """
    사용자 메시지에서 강습 검색용 구조화 인자(sport_type, difficulty 등)를 LLM으로 추출한다.

    자연어("초급 수영 있어?")를 그대로 DB 쿼리 조건으로 쓰기 어렵기 때문에,
    고정된 enum/키워드로 정규화해 search_lessons 도구가 안정적으로 동작하도록 한다.
    LLM 실패 시에는 원문을 keyword로만 넘겨 최소한의 검색은 시도한다.
    """

    # DB/API에서 사용하는 값(sport_type enum, difficulty 등)과 매핑되도록
    # 프롬프트에 허용 값 목록을 명시해 LLM이 임의 문자열을 만들지 않게 한다.
    prompt = f"""사용자 메시지에서 강습 검색 조건을 추출하세요.

메시지: "{state['user_message']}"

JSON으로 응답 (해당 없는 필드는 null):
{{
  "sport_type": "swimming|tennis|golf|fitness|yoga|pilates" 또는 null,
  "difficulty": "beginner|elementary|intermediate|advanced" 또는 null,
  "target_audience": "adult|child|senior" 또는 null,
  "keyword": "추가 키워드" 또는 null
}}"""

    trace = _get_trace()

    try:
        if trace:
            # 인자 추출도 "어떤 입력→어떤 인자"가 나왔는지" Langfuse에서 재현 가능하게 generation으로 남긴다.
            obs_kwargs: Dict[str, Any] = {
                "as_type": "generation",
                "name": "extract_search_args",
                "model": "gpt-4o-mini",
                "input": {"prompt": prompt},
            }
            trace_id = state.get("trace_id")
            if trace_id:
                obs_kwargs["metadata"] = {"trace_id": trace_id}

            with trace.start_as_current_observation(**obs_kwargs) as gen:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=100,
                    response_format={"type": "json_object"},
                )
                tokens = (
                    response.usage.total_tokens
                    if getattr(response, "usage", None)
                    else 0
                )
                args = json.loads(response.choices[0].message.content)
                # null/빈 값은 DB 필터에 넣지 않아 "조건 없음"으로 해석되게 한다.
                cleaned = {k: v for k, v in args.items() if v is not None}

                gen.update(
                    output=cleaned,
                    usage_details={"total_tokens": tokens},
                )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            args = json.loads(response.choices[0].message.content)
            cleaned = {k: v for k, v in args.items() if v is not None}

        return cleaned
    except Exception:
        # 파싱/LLM 오류 시 원문을 keyword로 넘겨, 최소한 ILIKE 폴백이라도 동작하게 한다.
        return {"keyword": state["user_message"]}


async def _extract_faq_keyword(client, state: AgentState) -> Dict[str, Any]:
    """
    사용자 메시지에서 RAG 벡터 검색에 잘 맞는 짧은 문장(keyword)을 LLM으로 추출한다.

    "환불은 어떻게 받나요?" 같은 말을 그대로 임베딩해도 되지만,
    불필요한 존댓말/접속사를 줄이고 핵심만 남기면 knowledge_chunks와의 유사도가 올라가
    FAQ 매칭 품질이 좋아진다. 실패 시 원문을 keyword로 쓴다.
    """

    prompt = f"""사용자 질문에서 벡터 검색에 사용할 핵심 문장을 추출하세요.

메시지: "{state['user_message']}"

규칙:
- 질문의 핵심 의미를 담은 짧은 문장으로 변환
- 불필요한 접속사, 감탄사, 존댓말 표현은 제거
- 의미가 보존된다면 동의어/유사어를 적절히 사용해도 좋음

JSON으로 응답:
{{"keyword": "검색 최적화된 문장"}}"""

    trace = _get_trace()

    try:
        if trace:
            obs_kwargs: Dict[str, Any] = {
                "as_type": "generation",
                "name": "extract_faq_keyword",
                "model": "gpt-4o-mini",
                "input": {"prompt": prompt},
            }
            trace_id = state.get("trace_id")
            if trace_id:
                obs_kwargs["metadata"] = {"trace_id": trace_id}

            with trace.start_as_current_observation(**obs_kwargs) as gen:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=80,
                    response_format={"type": "json_object"},
                )
                tokens = (
                    response.usage.total_tokens
                    if getattr(response, "usage", None)
                    else 0
                )
                payload = json.loads(response.choices[0].message.content)

                gen.update(
                    output=payload,
                    usage_details={"total_tokens": tokens},
                )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=80,
                response_format={"type": "json_object"},
            )
            payload = json.loads(response.choices[0].message.content)

        return payload
    except Exception:
        return {"keyword": state["user_message"]}


# ============================================================
# 3. Validator 노드: 결과 검증 + Self-Correction
# ============================================================

async def validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Tool 실행 결과가 "충분한지" 검사하고, 부족하면 재시도 전략(retry_strategy)을 세팅한다.

    이 노드가 is_valid=False + retry_strategy를 반환하면 agent_graph의 should_retry_or_respond가
    ToolExecutor로 다시 보내고, tool_executor_node는 retry_strategy에 따라 인자를 완화해 재실행한다.
    Validator는 "재시도할지 말지"만 결정하고, 실제 재시도 횟수 상한(MAX_TOOL_CALLS)은 그래프 쪽에서 막는다.
    """

    tool_result = state.get("tool_result") or {}
    retry_count = state.get("retry_count", 0)
    intent = state["intent"]

    # 도구가 예외 없이 끝났고, 비즈니스상 의미 있는 데이터가 있으면 "유효"로 본다.
    is_success = bool(tool_result.get("success"))
    has_data = bool(tool_result.get("data"))

    trace = _get_trace()

    def _result(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not trace:
            return payload

        # Validator 판단 자체도 span으로 남겨, "왜 재시도로 갔는지/왜 포기했는지"를 Trace에서 볼 수 있게 한다.
        span_kwargs: Dict[str, Any] = {
            "as_type": "span",
            "name": "validator",
            "input": {
                "intent": intent,
                "retry_count": retry_count,
                "tool_result_success": is_success,
                "has_data": has_data,
            },
        }
        trace_id = state.get("trace_id")
        if trace_id:
            span_kwargs["metadata"] = {"trace_id": trace_id}

        try:
            with trace.start_as_current_observation(**span_kwargs) as span:
                span.update(output=payload)
        except Exception:
            return payload

        return payload

    # 도구가 성공했고 데이터도 있으면 재시도할 이유가 없으므로 is_valid=True만 반환한다.
    if is_success and has_data:
        return _result(
            {
                "is_valid": True,
            }
        )

    # 이미 2번 재시도했으면 더 이상 완화하지 않고 포기한다. agent_graph의 MAX_TOOL_CALLS와 맞춰 둔다.
    if retry_count >= 2:
        return _result(
            {
                "is_valid": False,
            }
        )

    # 강습 검색 실패 시: difficulty/target_audience를 빼고 sport_type+keyword만으로 다시 검색하게 한다.
    if intent == "search_lessons":
        return _result(
            {
                "is_valid": False,
                "retry_count": retry_count + 1,
                "retry_strategy": "relax_filters",
            }
        )

    # FAQ 검색 실패 시: 추가 재시도 없이 바로 Response로 넘어간다.
    # 벡터 검색/RAG 결과가 없다는 사실을 사용자에게 정직하게 안내하는 편이
    # 임의로 키워드를 바꿔 재검색하는 것보다 예측 가능하고 안전한 UX를 만든다.
    if intent == "faq_inquiry":
        return _result(
            {
                "is_valid": False,
            }
        )

    # 그 외 intent(추천/수강현황 등)는 재시도 전략을 두지 않고, 결과 없음으로 Response로 넘긴다.
    return _result(
        {
            "is_valid": False,
        }
    )


# ============================================================
# 4. Response 노드: 최종 응답 생성
# ============================================================

async def response_node(state: AgentState) -> Dict[str, Any]:
    """
    Tool 결과(또는 general_inquiry일 때는 그냥 대화)를 바탕으로 최종 자연어 응답을 한 번에 생성한다.

    비스트리밍 채팅 경로에서만 쓰인다. 스트리밍 경로는 response_node_stream을 사용한다.
    """

    client = get_openai_client()
    intent = state["intent"]
    student_name = state.get("student_name")

    # 수강생 이름이 있으면 LLM이 이름을 붙여 말하도록 하고, 없으면 익명 안내를 넣는다.
    system_prompt = _build_response_prompt(student_name)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    # 이전 대화 맥락을 넣어 주면, "아까 말한 수영 강습이요" 같은 후속 질문에도 대응할 수 있다.
    for msg in state.get("chat_history", []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_content = f"사용자 질문: {state['user_message']}"

    # general_inquiry가 아니고 도구를 썼다면, 도구 결과를 LLM에 넘겨 그걸 요약/안내하게 한다.
    if intent != "general_inquiry" and state.get("tool_result") is not None:
        tool_result = state["tool_result"] or {}
        user_content += (
            f"\n\n[도구 실행 결과]\n"
            f"도구: {state.get('tool_name')}\n"
            f"결과: {json.dumps(tool_result, ensure_ascii=False)}"
        )

        # 결과가 없거나 실패했을 때는 LLM에게 "검색 없음"을 명시해, 거짓 정보를 만들지 않게 한다.
        if not tool_result.get("success") or not tool_result.get("data"):
            user_content += (
                "\n\n주의: 검색 결과가 없습니다. "
                "사용자에게 친절하게 안내하고 대안을 제시해주세요."
            )

    messages.append({"role": "user", "content": user_content})

    trace = _get_trace()

    try:
        if trace:
            obs_kwargs: Dict[str, Any] = {
                "as_type": "generation",
                "name": "response",
                "model": "gpt-4o-mini",
                "input": {"messages": messages},
            }
            trace_id = state.get("trace_id")
            if trace_id:
                obs_kwargs["metadata"] = {"trace_id": trace_id}

            with trace.start_as_current_observation(**obs_kwargs) as gen:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1500,
                )

                content = (
                    response.choices[0].message.content
                    or "죄송합니다. 응답 생성에 실패했습니다."
                )
                tokens = (
                    response.usage.total_tokens
                    if getattr(response, "usage", None)
                    else 0
                )

                gen.update(
                    output=content,
                    usage_details={"total_tokens": tokens},
                )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
            )

            content = (
                response.choices[0].message.content
                or "죄송합니다. 응답 생성에 실패했습니다."
            )
            tokens = (
                response.usage.total_tokens
                if getattr(response, "usage", None)
                else 0
            )

        return {
            "response": content,
            "total_tokens": state.get("total_tokens", 0) + tokens,
        }

    except Exception as e:
        print(f"[Response] 에러: {e}")
        return {
            "response": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "error": str(e),
        }


def _build_response_prompt(student_name: Optional[str]) -> str:
    """
    Response 노드에서 쓰는 시스템 프롬프트를 만든다.

    student_name이 있으면 "현재 수강생"으로 넣어 LLM이 이름을 쓰게 하고,
    없으면 익명임을 알려 과도한 개인화를 막는다.
    """

    if student_name:
        name_part = (
            f"\n현재 수강생: {student_name}\n"
            "이 이름을 자연스럽게 사용하되, 과하게 반복하지 마세요."
        )
    else:
        name_part = "\n수강생 이름이 확인되지 않았습니다."

    return f"""당신은 스포츠 강습 플랫폼 'Course Agent'의 AI 상담사입니다.
{name_part}

## 응답 규칙
- 친근하고 격려하는 톤, 필요시 이모지 사용 가능
- 강습 정보는 구조화하여 보기 쉽게 (강습명, 종목, 난이도, 강사명 등)
- 검색 결과가 없으면 솔직하게 말하고, 다른 종목/난이도 등 대안 제시
- 마무리 문장으로 추가 도움을 제안
- 도구 실행 결과의 JSON을 그대로 보여주지 말고, 자연스러운 한국어 문장으로 설명
"""


async def response_node_stream(state: AgentState) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Response 노드의 스트리밍 버전. OpenAI stream=True로 토큰을 받아 {"type": "token", "content": "..."} 형태로 yield한다.

    chat_service._run_agent_graph_stream_inner가 이 제너레이터를 소비하면서
    각 토큰을 SSE event로 프론트에 넘기므로, 사용자는 글자가 차례로 타이핑되는 것처럼 보인다.
    """

    client = get_openai_client()
    intent = state["intent"]
    student_name = state.get("student_name")

    system_prompt = _build_response_prompt(student_name)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    for msg in state.get("chat_history", []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_content = f"사용자 질문: {state['user_message']}"

    if intent != "general_inquiry" and state.get("tool_result") is not None:
        tool_result = state["tool_result"] or {}
        user_content += (
            f"\n\n[도구 실행 결과]\n"
            f"도구: {state.get('tool_name')}\n"
            f"결과: {json.dumps(tool_result, ensure_ascii=False)}"
        )

        if not tool_result.get("success") or not tool_result.get("data"):
            user_content += (
                "\n\n주의: 검색 결과가 없습니다. "
                "사용자에게 친절하게 안내하고 대안을 제시해주세요."
            )

    messages.append({"role": "user", "content": user_content})

    trace = _get_trace()

    try:
        obs_ctx = None
        if trace:
            obs_kwargs: Dict[str, Any] = {
                "as_type": "generation",
                "name": "response_stream",
                "model": "gpt-4o-mini",
                "input": {"messages": messages},
            }
            trace_id = state.get("trace_id")
            if trace_id:
                obs_kwargs["metadata"] = {"trace_id": trace_id}

            obs_ctx = trace.start_as_current_observation(**obs_kwargs)

        # Langfuse가 없을 때는 context manager가 필요 없으므로, 아무 것도 하지 않는 _Noop을 쓴다.
        if obs_ctx is not None:
            ctx = obs_ctx
        else:
            class _Noop:
                def __enter__(self_nonlocal):
                    return None

                def __exit__(self_nonlocal, exc_type, exc, tb):
                    return False

            ctx = _Noop()

        with ctx as gen:
            # stream=True로 하면 응답이 한 번에 오지 않고 청크 단위로 온다.
            # stream_options={"include_usage": True}를 넣어야 마지막 청크에 token 사용량이 포함된다.
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                stream=True,
                stream_options={"include_usage": True},
            )

            full_content = ""
            total_tokens = 0

            for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                delta = choice.delta if choice else None

                if delta and delta.content:
                    text = delta.content
                    full_content += text
                    # 이 토큰을 chat_service가 SSE "token" 이벤트로 프론트에 보낸다.
                    yield {"type": "token", "content": text}

                # usage는 stream 끝에 한 번만 오므로, 오면 total_tokens를 갱신한다.
                if getattr(chunk, "usage", None):
                    total_tokens = chunk.usage.total_tokens or 0

            if gen is not None:
                try:
                    gen.update(
                        output=full_content,
                        usage_details={"total_tokens": total_tokens},
                    )
                except Exception:
                    pass

            if total_tokens:
                yield {"type": "usage", "total_tokens": total_tokens}

    except Exception as e:
        print(f"[Response Stream] 에러: {e}")
        # 스트리밍 중 예외가 나도 클라이언트에는 에러 메시지 한 조각이라도 보내서 연결이 빈 응답으로 끝나지 않게 한다.
        yield {
            "type": "token",
            "content": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        }

