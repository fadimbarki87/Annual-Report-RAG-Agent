from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from agent_pipeline.evaluation.common import (
    BENCHMARK_PATH,
    RETRIEVAL_OUTPUT_PATH,
    ensure_data_dir,
    load_json,
    mean,
    percentile,
    save_json,
)
from agent_pipeline.retrieval.retrieval_service import retrieve_chunks


K_VALUES = (1, 3, 5, 10)
SEARCH_LIMIT = 10


def hit_at_k(ranks: list[int], k: int) -> float:
    return 1.0 if any(rank <= k for rank in ranks) else 0.0


def recall_at_k(ranks: list[int], total_relevant: int, k: int) -> float:
    if total_relevant <= 0:
        return 0.0
    hits = sum(1 for rank in ranks if rank <= k)
    return hits / total_relevant


def reciprocal_rank(ranks: list[int], k: int) -> float:
    valid = [rank for rank in ranks if rank <= k]
    if not valid:
        return 0.0
    return 1.0 / min(valid)


def dcg_at_k(ranks: list[int], k: int) -> float:
    return sum(1.0 / math.log2(rank + 1) for rank in ranks if rank <= k)


def ideal_dcg(total_relevant: int, k: int) -> float:
    return sum(
        1.0 / math.log2(index + 2)
        for index in range(min(total_relevant, k))
    )


def ndcg_at_k(ranks: list[int], total_relevant: int, k: int) -> float:
    idcg = ideal_dcg(total_relevant, k)
    if idcg == 0:
        return 0.0
    return dcg_at_k(ranks, k) / idcg


def average_precision_at_k(ranks: list[int], total_relevant: int, k: int) -> float:
    if total_relevant <= 0:
        return 0.0

    score = 0.0
    hit_count = 0
    for position in sorted(rank for rank in ranks if rank <= k):
        hit_count += 1
        score += hit_count / position
    return score / total_relevant


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    relevant_chunk_ids = set(case.get("relevant_chunk_ids") or [])

    start = time.perf_counter()
    results = retrieve_chunks(
        query=case["question"],
        company_filters=case.get("company_filters") or [],
        chunk_types=case.get("chunk_types") or [],
        limit=SEARCH_LIMIT,
    )
    elapsed = time.perf_counter() - start

    retrieved_chunk_ids = [
        str(result.payload.get("chunk_id") or "")
        for result in results
    ]
    relevant_ranks = [
        index
        for index, chunk_id in enumerate(retrieved_chunk_ids, start=1)
        if chunk_id in relevant_chunk_ids
    ]

    total_relevant = len(relevant_chunk_ids)
    metrics: dict[str, Any] = {
        "latency_seconds": round(elapsed, 3),
        "relevant_chunk_count": total_relevant,
        "relevant_ranks": relevant_ranks,
        "retrieved_chunk_ids_top10": retrieved_chunk_ids[:10],
        "first_relevant_rank": min(relevant_ranks) if relevant_ranks else None,
    }

    for k in K_VALUES:
        metrics[f"hit_at_{k}"] = hit_at_k(relevant_ranks, k)
        metrics[f"recall_at_{k}"] = recall_at_k(relevant_ranks, total_relevant, k)
    metrics["mrr_at_10"] = reciprocal_rank(relevant_ranks, 10)
    metrics["ndcg_at_10"] = ndcg_at_k(relevant_ranks, total_relevant, 10)
    metrics["average_precision_at_10"] = average_precision_at_k(
        relevant_ranks,
        total_relevant,
        10,
    )

    return {
        "case_id": case["case_id"],
        "question": case["question"],
        "company_filters": case.get("company_filters") or [],
        "chunk_types": case.get("chunk_types") or [],
        "relevant_chunk_ids": sorted(relevant_chunk_ids),
        "metrics": metrics,
    }


def summarize(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [result["metrics"]["latency_seconds"] for result in case_results]
    summary: dict[str, Any] = {
        "case_count": len(case_results),
        "search_limit": SEARCH_LIMIT,
        "mean_latency_seconds": round(mean(latencies) or 0.0, 3),
        "p95_latency_seconds": round(percentile(latencies, 0.95) or 0.0, 3),
    }

    for k in K_VALUES:
        summary[f"hit_at_{k}"] = round(
            mean([result["metrics"][f"hit_at_{k}"] for result in case_results]) or 0.0,
            6,
        )
        summary[f"recall_at_{k}"] = round(
            mean(
                [result["metrics"][f"recall_at_{k}"] for result in case_results]
            )
            or 0.0,
            6,
        )

    summary["mrr_at_10"] = round(
        mean([result["metrics"]["mrr_at_10"] for result in case_results]) or 0.0,
        6,
    )
    summary["ndcg_at_10"] = round(
        mean([result["metrics"]["ndcg_at_10"] for result in case_results]) or 0.0,
        6,
    )
    summary["map_at_10"] = round(
        mean([result["metrics"]["average_precision_at_10"] for result in case_results])
        or 0.0,
        6,
    )
    return summary


def main() -> int:
    ensure_data_dir()
    benchmark = load_json(BENCHMARK_PATH)
    supported_cases = [
        case
        for case in benchmark["cases"]
        if case.get("answer_expectation") == "supported"
    ]

    results = [evaluate_case(case) for case in supported_cases]
    output = {
        "summary": summarize(results),
        "cases": results,
    }
    save_json(output, RETRIEVAL_OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
