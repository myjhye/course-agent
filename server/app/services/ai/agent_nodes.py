"""
에이전트별 추론/검색 결과를 수집하고 가공하여
사용자 친화적인 최종 자연어 답변을 비스트리밍 또는 스트리밍 방식으로 생성한다.
"""

import json
from typing import Dict, Any, Optional, AsyncGenerator

from app.services.ai.agent_state import AgentState
from app.services.ai.llm_client import get_openai_client
from app.services.ai.langfuse_client import get_langfuse


def _get_trace():
    """Langfuse 모니터링 클라이언트 인스턴스를 반환한다 (미설정 시 None)."""
    return get_langfuse()


async def _extract_search_args(client, state: AgentState) -> Dict[str, Any]:
    """
    사용자의 자연어 질문으로부터 강습 검색 조건(종목, 난이도, 대상, 키워드)을 추출하여 구조화된 사전 형식으로 반환한다.
    - lesson_agent가 DB 조회를 수행하기 전에 호출하여 필터링 인자를 표준화한다.
    """
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
            # 관측 가능하도록 Langfuse Generation 계측 시작
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
                response = await client.chat.completions.create(
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
            response = await client.chat.completions.create(
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
        # LLM 파싱 예외 시 원본 메시지를 키워드로 할당하여 최소한의 와일드카드 매칭 유도
        return {"keyword": state["user_message"]}


async def _extract_faq_keyword(client, state: AgentState) -> Dict[str, Any]:
    """
    RAG 벡터 유사도 검색의 검색 정확도를 높이기 위해, 자연어 질문에서 접속사와 존댓말을 정제한 핵심 검색 질의문을 추출한다.
    - faq_agent가 RAG 검색을 시작하기 전에 키워드를 최적화하는 데 활용한다.
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
                response = await client.chat.completions.create(
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
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=80,
                response_format={"type": "json_object"},
            )
            payload = json.loads(response.choices[0].message.content)

        return payload
    except Exception:
        # LLM 파싱 예외 발생 시 질문 원문 자체를 검색 키워드로 폴백 처리
        return {"keyword": state["user_message"]}


async def response_node(state: AgentState) -> Dict[str, Any]:
    """
    비스트리밍 방식으로 에이전트의 검색 성과물을 취합하여 사용자에게 제시할 최종 자연어 응답을 일괄 생성한다.
    - 이전 대화 맥락(chat_history)을 반영하여 일관된 답변 흐름을 유지한다.
    """
    client = get_openai_client()
    intent = state["intent"]
    student_name = state.get("student_name")

    system_prompt = _build_response_prompt(student_name)
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    for msg in state.get("chat_history", []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_content = f"사용자 질문: {state['user_message']}"

    # 서브에이전트가 탐색한 결과 세트가 존재하면 시스템 지침과 함께 LLM에 동적으로 바인딩
    if intent != "general_inquiry":
        mode = state.get("routing_mode", "single_agent")
        agent_outputs = state.get("agent_outputs") or {}

        if mode == "multi_agent" and agent_outputs:
            user_content += "\n\n[도구 실행 결과 (멀티 에이전트)]\n"
            for agent_name, out in agent_outputs.items():
                if out.get("success") and out.get("failure_reason") is None:
                    user_content += (
                        f"- 에이전트: {agent_name}\n"
                        f"  결과: {json.dumps(out, ensure_ascii=False)}\n\n"
                    )
        elif state.get("tool_result") is not None:
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
                response = await client.chat.completions.create(
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
            response = await client.chat.completions.create(
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
    최종 자연어 답변 생성을 위한 상담사 페르소나 및 응답 규칙 정의 시스템 프롬프트를 동적으로 조립한다.
    - 세션 정보에 수강생의 실명이 존재할 경우 프롬프트에 동적으로 개인화 지침을 주입한다.
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
- 전달받은 모든 [도구 실행 결과] 또는 [도구 실행 결과 (멀티 에이전트)] 데이터를 절대로 생략하거나 무시하지 말고 응답에 유기적이고 충실하게 포함시키세요.
- 실제 강습 목록 데이터(예: 'lesson' 결과 등)가 제공되었다면, 절대로 일반론이나 형식적인 말로 때우지 말고 제공된 실제 강습 항목(강습명, 종목, 난이도, 강사명 등)을 일일이 매치하여 보기 쉽게 구조화해 나열해야 합니다.
- RAG FAQ 정보(예: 'faq' 결과 등)가 주어지면 규정 내용을 명확하고 상세하게 안내하세요.
- FAQ 검색 결과 항목 중 "image_url" 필드가 있는 경우에만 답변 본문 하단에 마크다운 이미지 태그 `![설명](이미지_URL)` 를 삽입하세요. image_url이 없는 항목이라면 절대로 이미지 링크를 만들지 마세요.
- 검색 결과가 없으면 솔직하게 말하고, 다른 종목/난이도 등 대안 제시
- 마무리 문장으로 추가 도움을 제안
- 도구 실행 결과의 JSON을 그대로 보여주지 말고, 자연스러운 한국어 문장으로 설명
"""


async def response_node_stream(state: AgentState) -> AsyncGenerator[Dict[str, Any], None]:
    """
    스트리밍(SSE) 방식으로 청크 토큰을 실시간 생성하여 chat_orchestrator에 제공하는 비동기 제너레이터 노드.
    - OpenAI 스트림 API의 chunk 단위 토큰과 최종 usage 메트릭을 yield한다.
    """
    client = get_openai_client()
    intent = state["intent"]
    student_name = state.get("student_name")

    system_prompt = _build_response_prompt(student_name)
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    for msg in state.get("chat_history", []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_content = f"사용자 질문: {state['user_message']}"

    if intent != "general_inquiry":
        mode = state.get("routing_mode", "single_agent")
        agent_outputs = state.get("agent_outputs") or {}

        if mode == "multi_agent" and agent_outputs:
            user_content += "\n\n[도구 실행 결과 (멀티 에이전트)]\n"
            for agent_name, out in agent_outputs.items():
                if out.get("success") and out.get("failure_reason") is None:
                    user_content += (
                        f"- 에이전트: {agent_name}\n"
                        f"  결과: {json.dumps(out, ensure_ascii=False)}\n\n"
                    )
        elif state.get("tool_result") is not None:
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
            stream = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                stream=True,
                stream_options={"include_usage": True},
            )

            full_content = ""
            total_tokens = 0

            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                delta = choice.delta if choice else None

                if delta and delta.content:
                    text = delta.content
                    full_content += text
                    # chat_orchestrator가 읽을 수 있도록 개별 텍스트 청크 방출
                    yield {"type": "token", "content": text}

                # 스트림 마지막에 정산되는 토큰 정보 수집
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

            # 누적 토큰 계측용 메트릭 방출
            if total_tokens:
                yield {"type": "usage", "total_tokens": total_tokens}

    except Exception as e:
        print(f"[Response Stream] 에러: {e}")
        yield {
            "type": "token",
            "content": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        }