"""
Calendar 서브에이전트.
구글 캘린더 MCP 서버의 create_calendar_event 및 list_calendar_events 도구를 호출합니다.
"""

import json
import datetime
from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agents.base import make_subagent
from app.services.ai.llm_client import get_openai_client
from app.services.ai.mcp_client import calendar_mcp_client


async def _extract_calendar_args(client, state: AgentState) -> Dict[str, Any]:
    """사용자 메시지에서 구글 캘린더 관리 인자를 LLM으로 추출합니다."""
    # LLM이 상대 일자(내일, 이번주 등)를 올바르게 판정하도록 현재 기준 시각을 제공합니다.
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prompt = f"""사용자 메시지에서 구글 캘린더 일정 관리 조건을 추출하세요.
현재 시스템 시간은 {now} 입니다. 이 기준을 참고해 상대적인 날짜/시간(예: '내일 10시', '이번주 수요일')을 절대적인 시간으로 변환해야 합니다.

메시지: "{state['user_message']}"

규칙:
1. action: 일정을 새로 생성/등록하는 의도이면 "create", 등록된 일정을 조회/확인하는 의도면 "list"로 분류하세요.
2. summary: 일정 제목 (예: "수영 강습 수강", "테니스장 예약"). action이 "list"일 때는 null로 하세요.
3. start_time: 일정 시작 시간. 반드시 아시아/서울 시간대 기준의 ISO 8601 형식으로 변환하세요 (예: "2026-05-15T10:00:00+09:00").
   - list 의도이며 기간이 애매한 경우 현재 시간의 날짜를 기준 범위의 시작으로 잡으세요.
4. end_time: 일정 종료 시간. 아시아/서울 시간대 기준의 ISO 8601 형식.
   - 단발성 일정 생성인 경우 시작 시간의 1시간 뒤를 기본값으로 계산하여 지정하세요.
5. description: 강습 강사명, 장소 등 일정 세부 사항. 없으면 null.

JSON으로 응답 (해당 없는 필드는 null):
{{
  "action": "create" 또는 "list",
  "summary": "일정 요약" 또는 null,
  "start_time": "ISO 8601 시각" 또는 null,
  "end_time": "ISO 8601 시각" 또는 null,
  "description": "상세 내용" 또는 null
}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        args = json.loads(response.choices[0].message.content)
        return {k: v for k, v in args.items() if v not in (None, "", "null")}
    except Exception:
        return {}


async def _extract(state: AgentState) -> Dict[str, Any]:
    client = get_openai_client()
    return await _extract_calendar_args(client, state)


async def _call_calendar_tool(args: Dict[str, Any]) -> str:
    """MCP 서버의 구글 캘린더 도구를 호출하고 결과를 텍스트로 파싱합니다."""
    action = args.get("action", "create")

    if action == "create":
        # 필수 인자 검증
        if not args.get("summary") or not args.get("start_time") or not args.get("end_time"):
            raise ValueError("일정 생성을 위해 제목(summary), 시작 시간(start_time), 종료 시간(end_time)이 필요합니다.")
        
        tool_args = {
            "summary": args["summary"],
            "start_time": args["start_time"],
            "end_time": args["end_time"],
            "description": args.get("description", "")
        }
        result = await calendar_mcp_client.call_tool("create_calendar_event", tool_args)
    else:
        tool_args = {}
        if args.get("start_time"):
            tool_args["time_min"] = args["start_time"]
        if args.get("end_time"):
            tool_args["time_max"] = args["end_time"]
        result = await calendar_mcp_client.call_tool("list_calendar_events", tool_args)

    # 응답 텍스트 추출 (fastmcp.Client 결과 객체 가공)
    if hasattr(result, "content") and result.content:
        text_val = ""
        for item in result.content:
            if hasattr(item, "text"):
                text_val += item.text
            elif hasattr(item, "value"):
                text_val += str(item.value)
        return text_val
    return str(result)


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    _ = state
    try:
        data = await _call_calendar_tool(args)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _validate(result: Dict[str, Any]) -> bool:
    """캘린더 작업 결과 유효성 판정."""
    return bool(result.get("success"))


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    _ = retry_idx
    return args


calendar_agent = make_subagent(
    name="calendar",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=0,
)
