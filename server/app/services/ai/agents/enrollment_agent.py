"""
수강 관리 서브에이전트.
회원별 수강 현황 조회(get_my_enrollments)와 맞춤 스포츠 강습 추천(get_recommendations) 두 가지 작업을 분기 처리한다.
LLM을 사용하여 사용자의 구체적인 의도(조회/추천)를 분류하고 도구를 실행한다.
"""

import json
from typing import Any, Dict

from app.services.ai.agent_state import AgentState
from app.services.ai.agents.base import make_subagent
from app.services.ai.llm_client import get_openai_client
from app.services.ai.tool_executor import ToolExecutor


async def _extract_enrollment_args(client, state: AgentState) -> Dict[str, Any]:
    """사용자 메시지로부터 수강 정보(조회 또는 추천) 요청 의도를 LLM으로 분류하여 도구를 픽업한다."""
    prompt = f"""사용자 메시지에서 수강 정보 관련 요청 의도를 분류하세요.

메시지: "{state['user_message']}"

규칙:
1. action: 새로운 운동 추천이나 수강 추천을 바라는 의도이면 "recommend"로 분류하세요. (예: "나한테 맞는 운동 알려줘", "다음 강습 추천해줘")
2. action: 본인의 현재 수강 현황이나 수강 목록을 확인하려는 의도이면 "list"로 분류하세요. (예: "수강 현황 보여줘", "내가 뭐 신청했지?")

JSON으로 응답:
{{
  "action": "recommend" 또는 "list"
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
        action = args.get("action", "list")
        tool = "get_recommendations" if action == "recommend" else "get_my_enrollments"
        return {
            "student_name": state.get("student_name"),
            "_tool": tool
        }
    except Exception as e:
        print(f"[enrollment] 의도 분류 LLM 호출 에러: {e}")
        return {
            "student_name": state.get("student_name"),
            "_tool": "get_my_enrollments"
        }


async def _extract(state: AgentState) -> Dict[str, Any]:
    # 현재 로그인 유저 정보와 대화 텍스트로부터 대상 도구(tool) 및 유저 식별자 추출
    client = get_openai_client()
    return await _extract_enrollment_args(client, state)


async def _execute(args: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    # DB 세션을 활용해 판정된 수강/추천 도구를 분기 실행 (DB 세션 필수)
    db = state.get("_db")
    if db is None:
        raise ValueError("enrollment_agent requires state['_db']")
    tool = args.get("_tool", "get_my_enrollments")
    payload = {k: v for k, v in args.items() if k != "_tool"}
    executor = ToolExecutor(db, trace_id=state.get("trace_id"))
    return await executor.execute(tool, payload)


def _validate(result: Dict[str, Any]) -> bool:
    # 수강 목록/추천 데이터 획득 성공 여부 및 결과 데이터 존재 검증
    return bool(result.get("success")) and bool(result.get("data"))


def _relax(args: Dict[str, Any], retry_idx: int) -> Dict[str, Any]:
    """
    검색 실패 시 인자를 완화하는 대신, 실행 도구 자체를 다른 성격의 도구로 스위칭(Cross-Fallback)하여 재시도한다.
    - 예: 추천 내역이 없으면 수강 현황 목록을 대신 보여주고, 반대로 수강 현황이 비어있으면 맞춤 강습 추천을 돌려준다.
    """
    current = args.get("_tool", "get_my_enrollments")
    switched = (
        "get_my_enrollments"
        if current == "get_recommendations"
        else "get_recommendations"
    )
    return {**args, "_tool": switched}


# 수강/추천 서브에이전트 노드 정의
# 스위칭 가능한 도구가 2개뿐이므로 교차 시도 1회(max_retries=1)로 재시도 상한을 설정
enrollment_agent = make_subagent(
    name="enrollment",
    extract_args=_extract,
    execute_tool=_execute,
    validate=_validate,
    relax_args=_relax,
    max_retries=1,
)


