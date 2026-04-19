"""
FAQ 서브에이전트.

RAG 기반 지식 청크 검색(search_faq)을 수행한다.
기존 agent_nodes._extract_faq_keyword를 재사용해 검색 최적 문장을 추출한다.

재시도 전략:
- 기존 코드에서 FAQ는 이미 벡터 검색 + ILIKE 폴백을 내장하고 있어
  에이전트 레벨 재시도가 큰 효과가 없다. max_retries=0으로 설정.
"""

from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import _extract_faq_keyword
from app.services.ai.agents.base import make_subagent
from app.services.ai.llm_client import get_openai_client
from app.services.ai.tool_executor import ToolExecutor


async def _extract(state: AgentState) -> Dict[str, Any]:
    client = get_openai_client()
    return await _extract_faq_keyword(client, state)


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    db = state.get("_db")
    if db is None:
        raise ValueError("faq_agent requires state['_db']")
    executor = ToolExecutor(db, trace_id=state.get("trace_id"))
    return await executor.execute("search_faq", args)


def _validate(result: Dict[str, Any]) -> bool:
    return bool(result.get("success")) and bool(result.get("data"))


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    # 재시도 안 함 (max_retries=0). 형식상 남겨둔다.
    return args


faq_agent = make_subagent(
    name="faq",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=0,
)
