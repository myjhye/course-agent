"""
서브에이전트 공통 팩토리.

모든 서브에이전트(lesson / enrollment / faq / facility)는 동일한 패턴으로 동작한다:
  1. extract_args: 사용자 메시지에서 도구 인자를 추출 (LLM 호출)
  2. execute_tool: 추출된 인자로 실제 도구 실행 (DB/RAG/외부 API)
  3. validate: 결과가 충분한지 판단
  4. (부실한 경우) 인자를 완화해 재시도 (max_retries까지)

이 공통 로직을 make_subagent 팩토리가 제공하고,
각 에이전트는 3개의 콜백 함수만 넘기면 된다.
"""

from typing import Callable, Awaitable, Any, Dict

from app.services.ai.agent_state import AgentState


ExtractFn = Callable[[AgentState], Awaitable[Dict[str, Any]]]
ExecuteFn = Callable[[Dict[str, Any], AgentState], Awaitable[Dict[str, Any]]]
ValidateFn = Callable[[Dict[str, Any]], bool]
RelaxFn = Callable[[Dict[str, Any], int], Dict[str, Any]]
# RelaxFn: (기존 args, 재시도 회차) -> 완화된 args
# 재시도 회차에 따라 다르게 완화할 수 있도록 회차를 함께 받는다.


def make_subagent(
    name: str,
    extract_args: ExtractFn,
    execute_tool: ExecuteFn,
    validate: ValidateFn,
    relax_args: RelaxFn,
    max_retries: int = 2,
):
    """
    서브에이전트 노드 함수를 생성한다.

    반환된 함수는 LangGraph 노드로 바로 등록 가능하며,
    실행 결과를 state.agent_outputs[name]에 누적한다.

    Args:
        name: 에이전트 이름 ("lesson" | "enrollment" | "faq" | "facility")
        extract_args: 사용자 메시지 → 도구 인자 추출 비동기 함수
        execute_tool: 인자 + state → 도구 실행 결과 비동기 함수
                      반환 형식: {"success": bool, "data": Any, "error"?: str, ...}
        validate: 도구 결과 → 유효성 판단 함수
        relax_args: 재시도 시 인자 완화 함수 (args, retry_idx) -> args
        max_retries: 최대 재시도 횟수 (기본 2)

    Returns:
        async (state: AgentState) -> dict: LangGraph 노드 함수
    """

    async def agent_node(state: AgentState) -> Dict[str, Any]:
        # 1) 인자 추출
        try:
            args = await extract_args(state)
        except Exception as e:
            print(f"[{name}] extract_args 에러: {e}")
            args = {}

        # 2) 실행 + 재시도 루프
        result: Dict[str, Any] = {"success": False, "data": None, "error": "not_executed"}
        attempts = 0
        last_args = args
        execution_count = 0

        while attempts <= max_retries:
            try:
                result = await execute_tool(last_args, state)
                execution_count += 1
            except Exception as e:
                print(f"[{name}] execute_tool 에러 (attempt {attempts}): {e}")
                result = {"success": False, "data": None, "error": str(e)}
                execution_count += 1

            if validate(result):
                break

            attempts += 1
            if attempts > max_retries:
                break

            # 재시도 전 인자 완화
            try:
                last_args = relax_args(last_args, attempts)
            except Exception as e:
                print(f"[{name}] relax_args 에러: {e}")
                break

        # 3) state에 병합할 출력 구성
        is_ok = validate(result)

        outputs = dict(state.get("agent_outputs", {}))
        outputs[name] = {
            **result,
            "failure_reason": None if is_ok else "결과 없음 또는 검증 실패",
            "attempts": execution_count,
        }

        tools_used = list(state.get("tools_used", []))
        tools_used.append(name)

        # 기존 코드와의 하위 호환:
        # response_node/response_node_stream이 state["tool_name"], state["tool_result"]를 참조하므로
        # 현재 에이전트 결과를 이 필드에도 함께 실어준다.
        # (멀티에이전트 모드에서 여러 에이전트가 실행되면 마지막 에이전트 결과가 들어가지만,
        #  Step 4에서 aggregator가 재정리한다. 이번 스텝에서는 단순 채움만 한다.)
        return {
            "agent_outputs": outputs,
            "tools_used": tools_used,
            "tool_name": name,
            "tool_args": last_args,
            "tool_result": result,
        }

    agent_node.__name__ = f"{name}_agent"
    return agent_node
