"""
RAG 검색 랭킹 평가 지표 파이프라인 (Retrieval Metrics Evaluator).

Recall@K, MRR@K, NDCG@K 메트릭의 중복 문서 매칭 및 상한(1.0) 초과 버그를 정정하여
표준 IR 벤치마크 평가 계산을 수행하고, 개별 질문 Raw 테이블 및 분석 리포트를 생성한다.
"""

import math
from typing import Any, Dict, List, Set, Tuple


def calculate_recall_at_k(
    retrieved_ids: List[str], ground_truth_ids: Set[str], k: int
) -> float:
    """
    Recall@K 계산.
    상위 K개 검색 결과 내 고유(Unique)하게 적중한 정답 문서 비율.
    (반드시 0.0 <= Recall@K <= 1.0 상한 보장)
    """
    if not ground_truth_ids:
        return 0.0
    cutoff = retrieved_ids[:k]
    # 중복 매칭 제거: 상위 K개 결과 중 적중한 고유 정답 문서 셋
    unique_hits = set(doc_id for doc_id in cutoff if doc_id in ground_truth_ids)
    recall = len(unique_hits) / len(ground_truth_ids)
    return min(1.0, recall)


def calculate_mrr_at_k(
    retrieved_ids: List[str], ground_truth_ids: Set[str], k: int
) -> float:
    """
    MRR@K (Mean Reciprocal Rank @ K) 계산.
    첫 번째 정답 문서가 등장한 순위의 역수 (1/rank).
    (반드시 0.0 <= MRR@K <= 1.0 상한 보장)
    """
    if not ground_truth_ids:
        return 0.0
    cutoff = retrieved_ids[:k]
    for idx, doc_id in enumerate(cutoff, start=1):
        if doc_id in ground_truth_ids:
            return 1.0 / idx
    return 0.0


def calculate_ndcg_at_k(
    retrieved_ids: List[str],
    ground_truth_relevance: Dict[str, int],
    k: int,
) -> float:
    """
    NDCG@K (Normalized Discounted Cumulative Gain @ K) 계산.
    정답 문서 관련도 점수(0~3점) 기반 가중 할인 랭킹 평가.
    (동일 정답 문서의 중복 DCG 누적을 차단하고 0.0 <= NDCG@K <= 1.0 보장)
    """
    if not ground_truth_relevance:
        return 0.0

    cutoff = retrieved_ids[:k]
    dcg = 0.0
    seen_ids = set()

    for idx, doc_id in enumerate(cutoff, start=1):
        if doc_id in ground_truth_relevance and doc_id not in seen_ids:
            rel = ground_truth_relevance[doc_id]
            if rel > 0:
                dcg += (2**rel - 1) / math.log2(idx + 1)
                seen_ids.add(doc_id)  # 중복 문서 재누적 차단

    ideal_relevances = sorted(ground_truth_relevance.values(), reverse=True)[:k]
    idcg = 0.0
    for idx, rel in enumerate(ideal_relevances, start=1):
        if rel > 0:
            idcg += (2**rel - 1) / math.log2(idx + 1)

    if idcg == 0.0:
        return 0.0

    ndcg = dcg / idcg
    return min(1.0, ndcg)


async def evaluate_golden_dataset(
    dataset: List[Dict[str, Any]],
    search_fn,
    k_values: List[int] = [3, 5, 10],
) -> Tuple[Dict[str, Any], str]:
    """
    골든셋 전체를 순회하면서 RAG 2-Stage 검색 결과의 전체 평균 및 카테고리별 성적표를 산출하고,
    18개 질답 전체 Raw 데이터와 마크다운 리포트를 생성한다.
    """
    results_by_query: List[Dict[str, Any]] = []
    category_map: Dict[str, List[Dict[str, Any]]] = {}

    for item in dataset:
        qid = item["id"]
        cat = item["category"]
        question = item["question"]
        gt_relevance = item.get("ground_truth_relevance", {})
        gt_ids = set(gt_relevance.keys())

        # 검색 실행
        retrieved_titles = await search_fn(question)

        # 타이틀 매칭 처리 (동일 키워드 중복 매칭 방지)
        retrieved_matched_ids = []
        for title in retrieved_titles:
            matched = False
            for gt_key in gt_ids:
                if gt_key in title:
                    retrieved_matched_ids.append(gt_key)
                    matched = True
                    break
            if not matched:
                retrieved_matched_ids.append("unmatched_doc")

        # 개별 질문 메트릭 계산
        item_metrics: Dict[str, float] = {}
        for k in k_values:
            item_metrics[f"recall@{k}"] = round(
                calculate_recall_at_k(retrieved_matched_ids, gt_ids, k), 4
            )
            item_metrics[f"mrr@{k}"] = round(
                calculate_mrr_at_k(retrieved_matched_ids, gt_ids, k), 4
            )
            item_metrics[f"ndcg@{k}"] = round(
                calculate_ndcg_at_k(retrieved_matched_ids, gt_relevance, k), 4
            )

        # 원인 분석 (점수가 낮거나 Negative 케이스)
        failure_analysis = "정상 노출"
        if cat == "negative":
            hits = sum(1 for tid in retrieved_matched_ids[:5] if tid != "unmatched_doc")
            if hits == 0:
                failure_analysis = "성공: 정답 없음(Negative) 정상 격리 (Hits=0)"
            else:
                failure_analysis = "한계: DB 무관 문서가 오탈자 유사도로 오유입됨"
        elif item_metrics.get("mrr@3", 0) == 0:
            failure_analysis = "한계: 키워드 유사도 부족 또는 2-Stage Rerank 상위 3위 컷오프 밖으로 랭킹 밀림"
        elif item_metrics.get("recall@3", 0) < 0.5:
            failure_analysis = "한계: 복수 정답 중 일부 청크만 3위 안에 진입 (Top-N 컷오프 제한)"

        record = {
            "id": qid,
            "category": cat,
            "question": question,
            "retrieved_titles": retrieved_titles[:4],
            "metrics": item_metrics,
            "analysis": failure_analysis,
            "is_negative": cat == "negative",
        }
        results_by_query.append(record)

        if cat not in category_map:
            category_map[cat] = []
        category_map[cat].append(record)

    # ── 전체 및 카테고리별 평균 산출 ──
    def _compute_averages(records: List[Dict[str, Any]]) -> Dict[str, float]:
        valid_records = [r for r in records if not r["is_negative"]]
        if not valid_records:
            return {f"{m}@{k}": 0.0 for m in ["recall", "mrr", "ndcg"] for k in k_values}

        averages = {}
        for k in k_values:
            for metric in ["recall", "mrr", "ndcg"]:
                key = f"{metric}@{k}"
                total = sum(r["metrics"][key] for r in valid_records)
                averages[key] = round(total / len(valid_records), 4)
        return averages

    overall_averages = _compute_averages(results_by_query)
    category_averages = {
        cat: _compute_averages(recs) for cat, recs in category_map.items()
    }

    # ── 마크다운 테이블 리포트 생성 ──
    md = []
    md.append("# 📊 [RAG Benchmark] 골든셋 랭킹 평가 최종 리포트 (버그 수정판)\n")
    md.append(f"- **총 평가 질문 수**: {len(dataset)}개 (6개 카테고리 각 3개씩)")
    md.append("- **평가 파이프라인**: PostgreSQL `pgvector` + `Cohere Rerank v3` 2-Stage Retrieval")
    md.append("- **수정 사항**: 중복 문서 매칭 카운트 제거 및 Recall/NDCG 상한(1.0) 보장 알고리즘 적용\n")

    md.append("## 1. 전체 골든셋 평균 지표 (Overall Metrics)")
    md.append("| Metric | K=3 | K=5 | K=10 |")
    md.append("|---|---|---|---|")
    md.append(f"| **Mean Recall@K** | {overall_averages['recall@3']} | {overall_averages['recall@5']} | {overall_averages['recall@10']} |")
    md.append(f"| **Mean MRR@K** | {overall_averages['mrr@3']} | {overall_averages['mrr@5']} | {overall_averages['mrr@10']} |")
    md.append(f"| **Mean NDCG@K** | {overall_averages['ndcg@3']} | {overall_averages['ndcg@5']} | {overall_averages['ndcg@10']} |\n")

    md.append("## 2. 카테고리별 세부 성적표 (Category-wise Metrics)")
    md.append("| Category | Questions | Mean Recall@3 | Mean MRR@3 | Mean NDCG@3 |")
    md.append("|---|---|---|---|---|")
    for cat, recs in category_map.items():
        avg = category_averages[cat]
        md.append(f"| **{cat}** | {len(recs)}개 | {avg['recall@3']} | {avg['mrr@3']} | {avg['ndcg@3']} |")
    md.append("")

    md.append("## 3. 18개 질문 전체 Raw 데이터 및 원인 분석 (Raw Items Table)")
    md.append("| ID | Category | 질문 | 검색된 Top 3 문서 | Recall@3 | MRR@3 | NDCG@3 | 원인 분석 및 한계점 |")
    md.append("|---|---|---|---|---|---|---|---|")
    for r in results_by_query:
        titles_str = ", ".join(r["retrieved_titles"][:3])
        m = r["metrics"]
        md.append(f"| {r['id']} | {r['category']} | {r['question']} | {titles_str} | {m['recall@3']} | {m['mrr@3']} | {m['ndcg@3']} | {r['analysis']} |")

    report_content = "\n".join(md)
    summary_dict = {
        "total_questions": len(dataset),
        "category_counts": {cat: len(recs) for cat, recs in category_map.items()},
        "overall_averages": overall_averages,
        "category_averages": category_averages,
        "details": results_by_query,
    }

    return summary_dict, report_content
