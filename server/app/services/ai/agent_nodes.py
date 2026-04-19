"""
멀티에이전트 그래프에서 쓰는 응답 노드 및 공용 헬퍼.

- response_node / response_node_stream: 최종 자연어 응답 (비스트리밍 / 스트리밍)
- _extract_search_args, _extract_faq_keyword: 서브에이전트(lesson/faq)에서 재사용
- _get_trace: Langfuse 클라이언트 (supervisor 등과 공유)
"""

import json
from typing import Dict, Any, Optional, AsyncGenerator

from app.services.ai.agent_state import AgentState
from app.services.ai.llm_client import get_openai_client
from app.services.ai.langfuse_client import get_langfuse


def _get_trace():
    """Langfuse 클라이언트 반환. 설정 없으면 None."""
    return get_langfuse()


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
                # null/빈 값은 DB 필터에 넣지 않아 "조건 없음"으로 해석되게 한다.
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
        return {"keyword": state["user_message"]}


# ============================================================
# Response 노드: 최종 응답 생성
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
                    text = delta.content    # "안", "녕", "하" 토큰 조각
                    full_content += text    # 전체 텍스트에 누적
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