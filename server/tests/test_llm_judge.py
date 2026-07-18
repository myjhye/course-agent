"""
LLM-as-Judge 회귀 테스트.

정답 케이스(질문 + 원본 문서 + 기대되는 좋은/나쁜 답변)를 미리 만들어두고,
judge_answer가 좋은 답변엔 높은 점수를, 나쁜 답변(환각·무관 답변)엔 낮은 점수를
정확히 매기는지 검증한다.

이 테스트가 통과한다는 건 "채점 로직 자체가 신뢰할 만하다"는 뜻이고,
이게 확인돼야 실제 프로덕션 답변 평가에 이 judge를 믿고 쓸 수 있다.
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

from app.services.ai.llm_judge import judge_answer


SOURCE_DOC = (
    "환불 규정 및 절차 안내: 수강 시작 후 7일 이내이고 진도율이 10% 미만일 경우 "
    "전액 환불이 가능합니다. 전체 과정의 1/3이 경과하기 전까지는 수강료의 2/3를 "
    "환불받을 수 있으며, 1/2 경과 전까지는 1/2을 환불받을 수 있습니다. "
    "그 이후에는 환불이 불가합니다."
)


@pytest.mark.asyncio
async def test_judge_scores_faithful_answer_high():
    """참고 문서 내용을 정확히 반영한 답변은 faithfulness가 높게 나와야 한다."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY 환경변수가 설정되지 않아 통합 테스트를 스킵합니다.")

    question = "환불 규정이 어떻게 되나요?"
    good_answer = (
        "수강 시작 후 7일 이내이고 진도율 10% 미만이면 전액 환불이 가능합니다. "
        "이후에는 진행 정도에 따라 2/3 또는 1/2 환불이 가능하며, 그 이후엔 환불이 어렵습니다."
    )

    result = await judge_answer(question, SOURCE_DOC, good_answer)

    assert result["success"] is True
    assert result["faithfulness"] >= 4  # 원본 내용을 정확히 반영했으므로 높은 점수 기대
    assert result["relevance"] >= 4      # 질문에 정확히 답했으므로 높은 점수 기대


@pytest.mark.asyncio
async def test_judge_scores_hallucinated_answer_low():
    """참고 문서에 없는 내용을 지어낸 답변은 faithfulness가 낮게 나와야 한다."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY 환경변수가 설정되지 않아 통합 테스트를 스킵합니다.")

    question = "환불 규정이 어떻게 되나요?"
    hallucinated_answer = (
        "환불은 언제든 100% 가능하며, 수강 완료 후에도 별도 신청 없이 자동으로 "
        "환불 처리됩니다. 추가로 위약금 없이 즉시 계좌로 입금됩니다."
    )

    result = await judge_answer(question, SOURCE_DOC, hallucinated_answer)

    assert result["success"] is True
    assert result["faithfulness"] <= 2  # 원본에 없는 내용을 지어냈으므로 낮은 점수 기대


@pytest.mark.asyncio
async def test_judge_scores_irrelevant_answer_low():
    """질문과 무관한 답변은 relevance가 낮게 나와야 한다."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY 환경변수가 설정되지 않아 통합 테스트를 스킵합니다.")

    question = "환불 규정이 어떻게 되나요?"
    irrelevant_answer = (
        "저희 수영장은 50m 레인 3개를 보유하고 있으며, 매일 오전 6시부터 개장합니다."
    )

    result = await judge_answer(question, SOURCE_DOC, irrelevant_answer)

    assert result["success"] is True
    assert result["relevance"] <= 2  # 질문과 무관하므로 낮은 점수 기대


@pytest.mark.asyncio
async def test_judge_returns_success_false_on_api_failure(monkeypatch):
    """OpenAI API 호출 자체가 실패해도 예외를 던지지 않고 success=False로 반환해야 한다."""
    from app.services.ai import llm_judge as judge_module

    class _BrokenClient:
        class chat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    raise RuntimeError("simulated API failure")

    monkeypatch.setattr(judge_module, "get_openai_client", lambda: _BrokenClient())

    result = await judge_answer("질문", "문서", "답변")
    assert result["success"] is False
    assert "error" in result
