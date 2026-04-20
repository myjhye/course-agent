"""
Facility 서브에이전트.

사용자 메시지에서 지역(sido/sigungu)·시설유형을 추출해 facility MCP 서버의
search_facilities 도구를 호출한다. MCP 호출 실패 시 예외를 raise해서
make_subagent의 표준 실패 경로로 빠지게 한다 (is_valid=False → 재라우팅).

MVP 범위:
- 좌표(user_lat/user_lng)는 넘기지 않음 — 거리 정렬 생략
- 시도명만 추출 가능하면 시군구 없이도 호출
"""

import json
from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agents.base import make_subagent
from app.services.ai.llm_client import get_openai_client
from app.services.ai.mcp_client import facility_mcp_client


async def _extract_facility_args(client, state: AgentState) -> Dict[str, Any]:
    """
    사용자 메시지에서 facility 검색 인자를 LLM으로 추출한다.

    규칙:
    - sido는 한국 표준 시도명 ("서울특별시", "경기도" 등 풀네임)
    - sigungu는 "강남구", "고양시 덕양구"처럼 KSPO 원본 포맷
    - facility_type은 자주 나오는 KSPO 유형명 ("수영장", "체력단련장", ...)
    - 추출 불가능한 필드는 null
    """
    prompt = f"""사용자 메시지에서 체육시설 검색 조건을 추출하세요.

메시지: "{state['user_message']}"

규칙:
- sido: 시도 풀네임 (예: "서울특별시", "경기도", "부산광역시")
- sigungu: 시군구명 (예: "강남구", "고양시 덕양구")
- facility_type: 시설유형 (예: "수영장", "체력단련장", "골프연습장", "테니스장")

JSON으로 응답 (해당 없는 필드는 null):
{{
  "sido": "서울특별시" 또는 null,
  "sigungu": "강남구" 또는 null,
  "facility_type": "수영장" 또는 null
}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
            response_format={"type": "json_object"},
        )
        args = json.loads(response.choices[0].message.content)
        return {k: v for k, v in args.items() if v not in (None, "", "null")}
    except Exception:
        return {}


async def _extract(state: AgentState) -> Dict[str, Any]:
    client = get_openai_client()
    return await _extract_facility_args(client, state)


async def _call_facility_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP 서버의 search_facilities 도구를 호출한다.
    fastmcp.Client 응답 구조 차이를 고려해 방어적으로 언팩한다.
    """
    result = await facility_mcp_client.call_tool("search_facilities", args)

    if isinstance(result, dict):
        data: Any = result
    else:
        data = getattr(result, "data", None)
        if data is None:
            data = getattr(result, "structured_content", None)
        if data is None:
            content = getattr(result, "content", None) or []
            if content and hasattr(content[0], "text"):
                data = json.loads(content[0].text)

    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected MCP response shape: {type(data).__name__}")

    return data


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    _ = state
    data = await _call_facility_tool(args)
    return {"success": True, "data": data}


def _validate(result: Dict[str, Any]) -> bool:
    """
    facility 결과 유효성 판정.
    - result.success=True 이고 data.items가 비어 있지 않으면 유효
    """
    if not bool(result.get("success")):
        return False
    data = result.get("data") or {}
    if not isinstance(data, dict):
        return False
    items = data.get("items") or []
    return len(items) > 0


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    _ = retry_idx
    return args


facility_agent = make_subagent(
    name="facility",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=0,
)
