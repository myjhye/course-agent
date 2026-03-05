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
    """사용자 의도를 분류한다."""

    client = get_openai_client()
    trace = _get_trace()

    try:
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": state["user_message"]},
        ]

        if trace:
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

        intent = result.get("intent", "general_inquiry")

        valid_intents = {
            "search_lessons",
            "get_recommendations",
            "manage_enrollment",
            "faq_inquiry",
            "general_inquiry",
        }
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
    Router가 분류한 의도에 따라 적절한 Tool을 실행한다.
    기존 ToolExecutor를 그대로 활용한다.
    """

    executor = ToolExecutor(db, trace_id=state.get("trace_id"))
    client = get_openai_client()
    intent = state["intent"]
    student_name = state.get("student_name")
    retry_count = state.get("retry_count", 0)

    # 의도별 Tool 매핑 + LLM으로 인자 추출
    if intent == "search_lessons":
        tool_name = "search_lessons"
        tool_args = await _extract_search_args(client, state)

        # 재시도 시 필터 완화
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
        # general_inquiry — Tool 실행 불필요
        return {
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
        }

    # student_name 자동 주입 (신뢰도 보강)
    if student_name and tool_name in ("get_my_enrollments", "get_recommendations"):
        tool_args["student_name"] = student_name

    # Tool 실행 + Langfuse span 기록
    trace = _get_trace()

    if trace:
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
            with trace.start_as_current_observation(**span_kwargs) as span:
                try:
                    tool_result = await executor.execute(tool_name, tool_args)
                except Exception as e:
                    print(f"[ToolExecutor] {tool_name} 실행 에러: {e}")
                    tool_result = {"success": False, "error": str(e)}

                span.update(output=tool_result)
        except Exception:
            # 관측 실패 시에는 기존 로직만 수행
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

    # 사용한 Tool 기록
    tools_used = list(state.get("tools_used", []))
    tools_used.append(tool_name)

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
    """사용자 메시지에서 강습 검색 인자를 추출한다."""

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
        return {"keyword": state["user_message"]}


async def _extract_faq_keyword(client, state: AgentState) -> Dict[str, Any]:
    """
    사용자 메시지에서 벡터 검색에 최적화된 FAQ/플랫폼 질문 문장을 추출한다.
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
    """Tool 결과를 검증하고, 실패 시 재시도 전략을 결정한다."""

    tool_result = state.get("tool_result") or {}
    retry_count = state.get("retry_count", 0)
    intent = state["intent"]

    is_success = bool(tool_result.get("success"))
    has_data = bool(tool_result.get("data"))

    trace = _get_trace()

    def _result(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not trace:
            return payload

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

    if is_success and has_data:
        return _result(
            {
                "is_valid": True,
            }
        )

    if retry_count >= 2:
        return _result(
            {
                "is_valid": False,
            }
        )

    if intent == "search_lessons":
        return _result(
            {
                "is_valid": False,
                "retry_count": retry_count + 1,
                "retry_strategy": "relax_filters",
            }
        )

    if intent == "faq_inquiry":
        return _result(
            {
                "is_valid": False,
                "retry_count": retry_count + 1,
                "retry_strategy": "broaden_keyword",
            }
        )

    return _result(
        {
            "is_valid": False,
        }
    )


# ============================================================
# 4. Response 노드: 최종 응답 생성
# ============================================================

async def response_node(state: AgentState) -> Dict[str, Any]:
    """Tool 결과를 바탕으로 최종 사용자 응답을 생성한다."""

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
    """응답 생성용 시스템 프롬프트."""

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
    Response 노드의 스트리밍 버전.
    OpenAI의 stream=True를 사용하여 토큰 단위로 yield한다.
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
                    yield {"type": "token", "content": text}

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
        yield {
            "type": "token",
            "content": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        }

