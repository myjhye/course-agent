"""
수강 관리 서브에이전트.

두 가지 작업을 내부에서 분기해 처리한다:
- 추천 요청: get_recommendations
- 수강 현황 조회: get_my_enrollments

재시도 전략(relax_args):
- 수강/추천 모두 student_name 하나만 받으므로 완화할 인자가 없다.
  대신 1회차 재시도에서 도구를 스위칭한다
  (예: 추천 결과가 없으면 수강 현황으로 폴백).
"""

from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agents.base import make_subagent
from app.services.ai.tool_executor import ToolExecutor


RECOMMEND_KEYWORDS = ("추천", "뭐 들", "맞는", "괜찮은", "어떤 강습")


def _pick_tool(user_message: str) -> str:
    msg = user_message or ""
    if any(kw in msg for kw in RECOMMEND_KEYWORDS):
        return "get_recommendations"
    return "get_my_enrollments"


async def _extract(state: AgentState) -> Dict[str, Any]:
    return {
        "student_name": state.get("student_name"),
        "_tool": _pick_tool(state.get("user_message", "")),
    }


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    db = state.get("_db")
    if db is None:
        raise ValueError("enrollment_agent requires state['_db']")
    tool = args.get("_tool", "get_my_enrollments")
    payload = {k: v for k, v in args.items() if k != "_tool"}
    executor = ToolExecutor(db, trace_id=state.get("trace_id"))
    return await executor.execute(tool, payload)


def _validate(result: Dict[str, Any]) -> bool:
    return bool(result.get("success")) and bool(result.get("data"))


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    # 1회차: 도구 스위칭 (추천 ↔ 수강현황)
    current = args.get("_tool", "get_my_enrollments")
    switched = (
        "get_my_enrollments"
        if current == "get_recommendations"
        else "get_recommendations"
    )
    return {**args, "_tool": switched}


enrollment_agent = make_subagent(
    name="enrollment",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=1,  # 도구가 2개뿐이라 1회 스위칭이면 충분
)
