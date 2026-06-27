"""
Facility 서브에이전트.
사용자 입력에서 지역(시도/시군구) 및 체육시설 유형을 LLM으로 추출하여,
전국 체육시설 API를 중개하는 facility MCP 서버의 search_facilities 도구를 호출한다.
"""

import json
from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agents.base import make_subagent
from app.services.ai.llm_client import get_openai_client
from app.services.ai.mcp_client import facility_mcp_client


async def _extract_facility_args(client, state: AgentState) -> Dict[str, Any]:
    """
    사용자 대화 내용에서 체육시설 API 쿼리에 사용할 필터링 값들을 추출한다.
    - sido: 공공데이터 검색용 정규 시도명 풀네임 (예: 서울 -> 서울특별시)
    - sigungu: 구/군명
    - facility_type: 체육시설 업종 유형
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
        # null이거나 빈 문자열인 필드는 딕셔너리에서 제외 처리
        return {k: v for k, v in args.items() if v not in (None, "", "null")}
    except Exception:
        return {}


async def _extract(state: AgentState) -> Dict[str, Any]:
    # OpenAI 클라이언트를 사용하여 체육시설 필터 인자 추출 진행
    client = get_openai_client()
    return await _extract_facility_args(client, state)


async def _call_facility_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    FastMCP 클라이언트를 통해 외부 시설 검색 API를 직접 호출한다.
    FastMCP 라이브러리의 버전 및 응답 형식(dict, text 필드, structured_content 등)에 구애받지 않도록
    다양한 객체 구조를 시도하여 방어적으로 JSON 데이터를 언팩한다.
    """
    result = await facility_mcp_client.call_tool("search_facilities", args)

    # 1) 응답이 이미 dict 형식인 경우 바로 반환
    if isinstance(result, dict):
        data: Any = result
    else:
        # 2) 객체 속성에 'data' 또는 'structured_content'가 포함된 경우
        data = getattr(result, "data", None)
        if data is None:
            data = getattr(result, "structured_content", None)
        # 3) fastmcp의 TextContent 리스트 구조를 띠고 있는 경우 텍스트를 파싱
        if data is None:
            content = getattr(result, "content", None) or []
            if content and hasattr(content[0], "text"):
                data = json.loads(content[0].text)

    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected MCP response shape: {type(data).__name__}")

    return data


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    # 추출한 검색 조건을 통해 MCP 도구를 실행하고 결과를 래핑하여 반환
    _ = state
    data = await _call_facility_tool(args)
    return {"success": True, "data": data}


def _validate(result: Dict[str, Any]) -> bool:
    """
    체육시설 검색 결과에 대한 최종 검증을 수행한다.
    조회는 성공했으나 반환된 시설 목록(items)이 비어있다면, 사용자에게 보여줄 데이터가
    실질적으로 없으므로 실패(False)로 판단하여 1차 에이전트 실패 -> lesson 폴백을 작동시킨다.
    """
    if not bool(result.get("success")):
        return False
    data = result.get("data") or {}
    if not isinstance(data, dict):
        return False
    items = data.get("items") or []
    return len(items) > 0


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    # max_retries=0 으로 재시도를 타지 않으므로 기본 인자를 그대로 바이패스함
    _ = retry_idx
    return args


# Facility 서브에이전트 노드 정의
# 공공데이터 API 검색 특성상 인자 완화 재시도보다는 빠른 실패 후 lesson 폴백이 유연하므로 max_retries=0으로 고정한다.
facility_agent = make_subagent(
    name="facility",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=0,
)


