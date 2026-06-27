"""
강습 검색 서브에이전트.
사용자 대화에서 강습 관련 조건들을 추출한 뒤, 로컬 데이터베이스의 강습 테이블을 조회(search_lessons)한다.
검색 결과가 빈 경우, 입력 조건을 점진적으로 넓혀서 다시 검색하도록 재시도(relax_args) 전략을 사용한다.
"""

from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import _extract_search_args
from app.services.ai.agents.base import make_subagent
from app.services.ai.llm_client import get_openai_client
from app.services.ai.tool_executor import ToolExecutor


async def _extract(state: AgentState) -> Dict[str, Any]:
    # 사용자 대화 내용에서 강습 쿼리용 필터 인자(과목, 강사, 난이도 등)를 LLM을 이용해 추출
    client = get_openai_client()
    return await _extract_search_args(client, state)


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    # 로컬 DB에 접속하여 강습 목록 검색 도구 실행 (DB 세션 필수)
    db = state.get("_db")
    if db is None:
        raise ValueError("lesson_agent requires state['_db']")
    executor = ToolExecutor(db, trace_id=state.get("trace_id"))
    return await executor.execute("search_lessons", args)


def _validate(result: Dict[str, Any]) -> bool:
    # 검색 성공 및 실제 매칭되는 강습 데이터 건수가 존재하면 유효(True)한 것으로 판단
    return bool(result.get("success")) and bool(result.get("data"))


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    """
    검색 결과가 부실하여 재시도할 때, 검색 쿼리 조건을 넓히는 완화(Relax) 알고리즘.
    - 1회차 재시도: 구체적인 '난이도(difficulty)' 및 '수강대상(target_audience)' 필터를 해제하여 넓게 조회
    - 2회차 재시도: 과목(sport_type) 필터마저 해제하고 자연어 검색 키워드(keyword) 기반 유사 검색으로 전체 조회
    """
    if retry_idx == 1:
        # difficulty, target_audience 제거
        return {
            "sport_type": args.get("sport_type"),
            "keyword": args.get("keyword"),
        }
    # retry_idx >= 2: keyword만 남겨 최대 범위로 유사도 매칭 수행
    return {"keyword": args.get("keyword") or args.get("sport_type")}


# 강습 서브에이전트 노드 정의
# 점진적으로 필터를 완화하여 최대 2회 재시도(max_retries=2)하도록 인프라 파이프라인 구성
lesson_agent = make_subagent(
    name="lesson",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=2,
)

