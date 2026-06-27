"""
FAQ 서브에이전트.
RAG 기반 FAQ 지식 검색(search_faq)을 수행한다.
(자체 벡터 검색 및 ILIKE 폴백을 내장하고 있어 재시도는 생략함)
"""

from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import _extract_faq_keyword
from app.services.ai.agents.base import make_subagent
from app.services.ai.llm_client import get_openai_client
from app.services.ai.tool_executor import ToolExecutor


async def _extract(state: AgentState) -> Dict[str, Any]:
    # 사용자 메시지로부터 RAG 검색용 최적 키워드/문장 추출
    client = get_openai_client()
    return await _extract_faq_keyword(client, state)


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    # RAG 기반 FAQ 검색 도구 실행 (DB 세션 필수)
    db = state.get("_db")
    if db is None:
        raise ValueError("faq_agent requires state['_db']")
    executor = ToolExecutor(db, trace_id=state.get("trace_id"))
    return await executor.execute("search_faq", args)


def _validate(result: Dict[str, Any]) -> bool:
    # 검색 성공 여부 및 결과 데이터 존재 검증
    return bool(result.get("success")) and bool(result.get("data"))


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    # 재시도하지 않으므로 기존 인자 반환 (max_retries=0)
    return args


# FAQ 서브에이전트 노드 생성
faq_agent = make_subagent(
    name="faq",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=0,
)

