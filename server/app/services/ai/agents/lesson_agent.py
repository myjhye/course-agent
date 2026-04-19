"""
강습 검색 서브에이전트.

Course Agent 플랫폼의 강습 DB를 검색한다.
기존 agent_nodes._extract_search_args를 재사용해 자연어 → 구조화 인자로 변환 후
ToolExecutor.execute("search_lessons", ...)를 호출한다.

재시도 전략(relax_args):
- 1회차 재시도: difficulty, target_audience 제거 (sport_type + keyword만 유지)
- 2회차 재시도: keyword만 유지
"""

from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import _extract_search_args
from app.services.ai.agents.base import make_subagent
from app.services.ai.llm_client import get_openai_client
from app.services.ai.tool_executor import ToolExecutor


async def _extract(state: AgentState) -> Dict[str, Any]:
    client = get_openai_client()
    return await _extract_search_args(client, state)


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    db = state.get("_db")
    if db is None:
        raise ValueError("lesson_agent requires state['_db']")
    executor = ToolExecutor(db, trace_id=state.get("trace_id"))
    return await executor.execute("search_lessons", args)


def _validate(result: Dict[str, Any]) -> bool:
    return bool(result.get("success")) and bool(result.get("data"))


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    if retry_idx == 1:
        # difficulty, target_audience 제거
        return {
            "sport_type": args.get("sport_type"),
            "keyword": args.get("keyword"),
        }
    # retry_idx >= 2: keyword만
    return {"keyword": args.get("keyword") or args.get("sport_type")}


lesson_agent = make_subagent(
    name="lesson",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=2,
)
