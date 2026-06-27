"""
서브에이전트 공통 팩토리 (make_subagent).
인자 추출 -> 도구 실행 -> 결과 검증 -> (실패 시) 인자 완화 및 재시도 순서의 공통 파이프라인을 제공한다.
"""

from typing import Callable, Awaitable, Any, Dict

from app.services.ai.agent_state import AgentState

# ExtractFn: 사용자 입력(AgentState)에서 도구 실행에 필요한 파라미터를 LLM 등을 통해 추출하는 비동기 함수
ExtractFn = Callable[[AgentState], Awaitable[Dict[str, Any]]]

# ExecuteFn: 추출된 파라미터와 상태를 바탕으로 로컬 DB 쿼리, RAG 검색, 외부 MCP 등의 실제 도구를 실행하는 비동기 함수
ExecuteFn = Callable[[Dict[str, Any], AgentState], Awaitable[Dict[str, Any]]]

# ValidateFn: 도구 실행 결과 데이터가 유효한지(예: 검색 결과 0건 여부, 신뢰성 검증 등) 판단하는 함수
ValidateFn = Callable[[Dict[str, Any]], bool]

# RelaxFn: 검증 실패 시, 재시도 회차에 맞게 입력 파라미터를 완화(필터 조건 해제 등)해 주는 완화 함수
RelaxFn = Callable[[Dict[str, Any], int], Dict[str, Any]]


def make_subagent(
    name: str,
    extract_args: ExtractFn,
    execute_tool: ExecuteFn,
    validate: ValidateFn,
    relax_args: RelaxFn,
    max_retries: int = 2,
):
    """
    개별 도메인 에이전트(lesson, enrollment, faq, facility, calendar)의 공통 노드 함수를 생성한다.
    생성된 함수는 LangGraph 노드로 등록 가능하며, 최종 결과는 state.agent_outputs[name]에 저장된다.
    """

    async def agent_node(state: AgentState) -> Dict[str, Any]:
        # 1. 사용자 메시지로부터 도구 실행을 위한 인자 추출 (LLM 호출)
        try:
            args = await extract_args(state)
        except Exception as e:
            print(f"[{name}] extract_args 에러: {e}")
            args = {}

        # 2. 실행 및 검증 재시도 루프 (최대 max_retries회 수행)
        result: Dict[str, Any] = {"success": False, "data": None, "error": "not_executed"}
        attempts = 0
        last_args = args
        execution_count = 0

        while attempts <= max_retries:
            try:
                result = await execute_tool(last_args, state)
                execution_count += 1
            except ValueError as e:
                # DB 세션 누락 등 코드 레벨의 치명적인 계약 위반은 재시도하지 않고 그대로 상위 에러 전파
                if "requires state['_db']" in str(e):
                    raise
                print(f"[{name}] execute_tool 에러 (attempt {attempts}): {e}")
                result = {"success": False, "data": None, "error": str(e)}
                execution_count += 1
            except Exception as e:
                print(f"[{name}] execute_tool 에러 (attempt {attempts}): {e}")
                result = {"success": False, "data": None, "error": str(e)}
                execution_count += 1

            # 검증을 만족하면(is_valid=True) 재시도 루프 즉시 종료
            if validate(result):
                break

            attempts += 1
            if attempts > max_retries:
                break

            # 다음 루프 돌기 전 완화 함수(relax_args)를 타서 검색 조건을 단순화
            try:
                last_args = relax_args(last_args, attempts)
            except Exception as e:
                print(f"[{name}] relax_args 에러: {e}")
                break

        # 3. LangGraph 전역 상태 업데이트를 위한 출력 데이터 구성
        is_ok = validate(result)

        # 개별 에이전트들의 실행 이력을 관리하기 위해 agent_outputs 딕셔너리에 추가
        outputs = dict(state.get("agent_outputs", {}))
        outputs[name] = {
            **result,
            "failure_reason": None if is_ok else "결과 없음 또는 검증 실패",
            "attempts": execution_count,
        }

        # 실행된 에이전트 목록 히스토리 기록
        tools_used = list(state.get("tools_used", []))
        tools_used.append(name)

        # response_node 및 response_node_stream 등 기존 비-멀티에이전트 호환성을 위한 반환 처리
        return {
            "agent_outputs": outputs,
            "tools_used": tools_used,
            "tool_name": name,
            "tool_args": last_args,
            "tool_result": result,
        }

    agent_node.__name__ = f"{name}_agent"
    return agent_node

