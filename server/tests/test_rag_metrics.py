"""
RAG 검색 IR 메트릭(Recall@K, MRR@K, NDCG@K) 골든셋 자동화 벤치마크 평가 테스트 수트.

golden_dataset.json(18개 질답 셋)을 로딩하여 6개 카테고리별 세부 지표 및 전체 평균을 산출하고,
마크다운 테이블 리포트(rag_evaluation_report.md)로 자동 저장한다.
"""

import json
import os
from pathlib import Path
import pytest
from dotenv import load_dotenv

load_dotenv()

from app.services.ai.rag_evaluator import (
    calculate_recall_at_k,
    calculate_mrr_at_k,
    calculate_ndcg_at_k,
    evaluate_golden_dataset,
)


GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
REPORT_OUTPUT_PATH = Path(__file__).parent / "rag_evaluation_report.md"


def test_rag_evaluator_math_correctness():
    """Recall@K, MRR@K, NDCG@K 계산 공식의 상한(1.0) 및 중복 매칭 제거 정합성을 단위 검증한다."""
    # 중복 문서가 연속으로 유입되는 경우의 모의 테스트: ["doc_A", "doc_A", "doc_C"]
    retrieved_with_duplicates = ["doc_A", "doc_A", "doc_C", "doc_D"]
    ground_truth_relevance = {"doc_A": 3, "doc_C": 2}
    ground_truth_ids = set(ground_truth_relevance.keys())

    # 중복 문서가 있어도 Recall@2는 doc_A 1개만 고유 카운트되어 1 / 2 = 0.5 (절대 1.0을 안 넘음)
    recall_at_2 = calculate_recall_at_k(retrieved_with_duplicates, ground_truth_ids, k=2)
    assert recall_at_2 == 0.5

    # Recall@3: doc_A, doc_C 2개 고유 카운트되어 2 / 2 = 1.0
    recall_at_3 = calculate_recall_at_k(retrieved_with_duplicates, ground_truth_ids, k=3)
    assert recall_at_3 == 1.0

    # NDCG@3도 동일 문서 중복 DCG 누적이 차단되어 1.0 이하로 캡(Cap) 씌워짐
    ndcg_at_3 = calculate_ndcg_at_k(retrieved_with_duplicates, ground_truth_relevance, k=3)
    assert 0.0 <= ndcg_at_3 <= 1.0

    print(f"\n[PASSED] 버그 정정 후 RAG 메트릭 단위 검증 (Recall@3: {recall_at_3}, MRR@3: {calculate_mrr_at_k(retrieved_with_duplicates, ground_truth_ids, 3)}, NDCG@3: {round(ndcg_at_3, 4)})")


@pytest.mark.asyncio
async def test_evaluate_full_golden_dataset():
    """
    golden_dataset.json(18개 쿼리) 전체를 순회하여
    K=3, 5, 10별 전체 평균 및 카테고리별 성적표를 실측하고 리포트를 파일로 영속 저장한다.
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY가 없어 통합 테스트를 스킵합니다.")

    assert GOLDEN_DATASET_PATH.exists(), f"골든셋 파일이 없습니다: {GOLDEN_DATASET_PATH}"
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        golden_dataset = json.load(f)

    from app.database import AsyncSessionLocal
    from app.services.ai.tool_executor import ToolExecutor

    async with AsyncSessionLocal() as db:
        executor = ToolExecutor(db)

        async def _search_fn(question: str):
            result = await executor.execute("search_faq", {"keyword": question})
            if result.get("success") and result.get("data"):
                return [item.get("title", "") for item in result.get("data", [])]
            return []

        # 골든셋 벤치마크 평가 구동
        summary_dict, report_md = await evaluate_golden_dataset(
            golden_dataset, _search_fn, k_values=[3, 5, 10]
        )

        # 마크다운 리포트 파일로 저장
        with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as rf:
            rf.write(report_md)

        # 콘솔에 요약 및 개별 질문 raw 표 출력
        print("\n" + report_md)

        # 1.0 초과 상한 검증: 18개 질문 전체의 Recall/MRR/NDCG가 모두 1.0 이하이어야 함
        for r in summary_dict["details"]:
            m = r["metrics"]
            for k in [3, 5, 10]:
                assert m[f"recall@{k}"] <= 1.0, f"QID {r['id']} Recall@{k}가 1.0 초과: {m[f'recall@{k}']}"
                assert m[f"mrr@{k}"] <= 1.0, f"QID {r['id']} MRR@{k}가 1.0 초과: {m[f'mrr@{k}']}"
                assert m[f"ndcg@{k}"] <= 1.0, f"QID {r['id']} NDCG@{k}가 1.0 초과: {m[f'ndcg@{k}']}"
