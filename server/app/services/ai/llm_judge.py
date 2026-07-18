"""
LLM-as-Judge 평가 파이프라인.

RAG 답변의 품질을 GPT-4o-mini로 채점하고, Langfuse에 점수를 기록한다.

평가 축 2가지:
- faithfulness (충실도): 답변이 참고 문서(RAG 소스)의 내용과 일치하는지, 없는 사실을 지어내지 않았는지
- relevance (연관성): 답변이 사용자 질문에 실제로 답하고 있는지

두 축을 분리한 이유:
- 충실도는 높은데 연관성이 낮을 수 있다 (문서 내용은 정확히 인용했지만 질문과 무관한 부분을 답함)
- 연관성은 높은데 충실도가 낮을 수 있다 (질문엔 잘 답한 것처럼 보이지만 없는 사실을 지어냄, 즉 환각)
  두 경우를 하나의 점수로 뭉치면 "왜 낮은 점수가 나왔는지" 구분이 안 된다.
"""
import json
from typing import Any, Dict, Optional

from app.services.ai.llm_client import get_openai_client
from app.services.ai.langfuse_client import get_langfuse


JUDGE_MODEL = "gpt-4o-mini"

_JUDGE_PROMPT = """당신은 AI 상담 챗봇의 답변 품질을 평가하는 엄격한 심사관입니다.
아래 정보를 보고 두 가지 기준으로 답변을 1~5점으로 채점하세요.

[사용자 질문]
{question}

[참고 문서 (RAG로 검색된 원본 소스)]
{source_document}

[챗봇 답변]
{answer}

평가 기준:

1. faithfulness (충실도, 1~5점)
   - 답변이 참고 문서에 있는 내용만을 근거로 작성되었는가
   - 참고 문서에 없는 사실을 지어내지 않았는가 (환각 여부)
   - 5점: 문서 내용과 완전히 일치, 지어낸 내용 없음
   - 3점: 대체로 일치하지만 일부 세부사항이 부정확하거나 누락됨
   - 1점: 참고 문서와 무관한 내용을 지어냄

2. relevance (연관성, 1~5점)
   - 답변이 사용자 질문에 실제로 답하고 있는가
   - 5점: 질문의 핵심에 정확히 답함
   - 3점: 질문과 관련은 있지만 핵심을 완전히 다루지 못함
   - 1점: 질문과 무관한 답변

반드시 아래 JSON 형식으로만 응답하세요.
{{
  "faithfulness": <1~5 정수>,
  "faithfulness_reason": "<한 줄 이유>",
  "relevance": <1~5 정수>,
  "relevance_reason": "<한 줄 이유>"
}}"""


async def judge_answer(
    question: str,
    source_document: str,
    answer: str,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    답변 하나를 GPT-4o-mini로 채점한다.

    Args:
        question: 사용자 질문
        source_document: RAG로 검색된 원본 문서 (충실도 평가의 기준점)
        answer: 챗봇이 실제로 생성한 답변
        trace_id: 있으면 원래 요청의 trace와 같은 흐름으로 Langfuse에 묶어서 기록

    Returns:
        {"faithfulness": int, "relevance": int, ...} 형식.
        평가 자체가 실패하면 success=False와 함께 반환한다 (예외를 던지지 않음).
    """
    client = get_openai_client()
    trace = get_langfuse()

    prompt = _JUDGE_PROMPT.format(
        question=question,
        source_document=source_document,
        answer=answer,
    )

    async def _call() -> Dict[str, Any]:
        response = await client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # 채점은 일관성이 중요하므로 0
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content)

        # 방어적 검증: LLM이 범위를 벗어난 값을 줄 수 있으므로 clamp
        faithfulness = max(1, min(5, int(payload.get("faithfulness", 1))))
        relevance = max(1, min(5, int(payload.get("relevance", 1))))

        return {
            "success": True,
            "faithfulness": faithfulness,
            "faithfulness_reason": payload.get("faithfulness_reason", ""),
            "relevance": relevance,
            "relevance_reason": payload.get("relevance_reason", ""),
        }

    if not trace:
        try:
            return await _call()
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Langfuse generation으로 채점 과정 자체도 기록 (채점 프롬프트, 채점 결과, 토큰 사용량)
    obs_kwargs: Dict[str, Any] = {
        "as_type": "generation",
        "name": "llm_judge",
        "model": JUDGE_MODEL,
        "input": {"question": question, "answer": answer},
    }
    if trace_id:
        obs_kwargs["metadata"] = {"trace_id": trace_id}

    try:
        with trace.start_as_current_observation(**obs_kwargs) as gen:
            result = await _call()
            gen.update(output=result)

            # 채점 결과를 Langfuse Score로도 별도 기록
            # (Score는 대시보드에서 시간에 따른 품질 추이를 그래프로 볼 수 있게 해줌)
            if result.get("success") and trace_id:
                trace.score(
                    trace_id=trace_id,
                    name="faithfulness",
                    value=result["faithfulness"],
                    comment=result.get("faithfulness_reason"),
                )
                trace.score(
                    trace_id=trace_id,
                    name="relevance",
                    value=result["relevance"],
                    comment=result.get("relevance_reason"),
                )

            return result
    except Exception as e:
        # Langfuse 기록이 실패해도 채점 자체는 시도 (관측 실패가 평가를 막으면 안 됨)
        try:
            return await _call()
        except Exception as e2:
            return {"success": False, "error": str(e2)}
