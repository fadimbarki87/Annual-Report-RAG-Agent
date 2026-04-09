from __future__ import annotations

import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from agent_pipeline.evaluation.common import (
    CATEGORY_BENCHMARK_PATH,
    CATEGORY_RETRIEVAL_OUTPUT_PATH,
    ensure_data_dir,
    load_json,
    mean,
    percentile,
    save_json,
)
from agent_pipeline.retrieval.retrieval_service import retrieve_chunks


SEARCH_LIMIT = 10
K_VALUES = (1, 3, 5, 10)


def document_recall_at_k(
    retrieved_document_ids: list[str],
    expected_document_ids: list[str],
    k: int,
) -> float:
    if not expected_document_ids:
        return 0.0
    top_k = {
        document_id
        for document_id in retrieved_document_ids[:k]
        if document_id
    }
    hits = sum(1 for document_id in expected_document_ids if document_id in top_k)
    return hits / len(expected_document_ids)


def top1_expected_document_hit(
    retrieved_document_ids: list[str],
    expected_document_ids: list[str],
) -> float:
    if not expected_document_ids or not retrieved_document_ids:
        return 0.0
    return 1.0 if retrieved_document_ids[0] in set(expected_document_ids) else 0.0


def purity_at_k(
    retrieved_document_ids: list[str],
    expected_document_ids: list[str],
    k: int,
) -> float:
    if not expected_document_ids:
        return 0.0
    top_k = [document_id for document_id in retrieved_document_ids[:k] if document_id]
    if not top_k:
        return 0.0
    expected = set(expected_document_ids)
    return sum(1 for document_id in top_k if document_id in expected) / len(top_k)


def chunk_type_coverage_at_k(
    retrieved_chunk_types: list[str],
    expected_chunk_types: list[str],
    k: int,
) -> float:
    if not expected_chunk_types:
        return 0.0
    top_k = {chunk_type for chunk_type in retrieved_chunk_types[:k] if chunk_type}
    hits = sum(1 for chunk_type in expected_chunk_types if chunk_type in top_k)
    return hits / len(expected_chunk_types)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    results = retrieve_chunks(
        query=case["question"],
        company_filters=case.get("company_filters") or [],
        chunk_types=case.get("chunk_types") or [],
        limit=SEARCH_LIMIT,
    )
    elapsed = time.perf_counter() - start

    retrieved_document_ids = [
        str(result.payload.get("document_id") or "")
        for result in results
    ]
    retrieved_chunk_types = [
        str(result.payload.get("chunk_type") or "")
        for result in results
    ]
    expected_document_ids = list(case.get("expected_document_ids") or [])
    expected_chunk_types = list(case.get("expected_chunk_types") or [])
    top_scores = [float(result.score) for result in results]

    metrics: dict[str, Any] = {
        "latency_seconds": round(elapsed, 3),
        "result_count": len(results),
        "top_score": round(top_scores[0], 6) if top_scores else None,
        "mean_top3_score": round(mean(top_scores[:3]) or 0.0, 6),
        "top1_expected_document_hit": top1_expected_document_hit(
            retrieved_document_ids,
            expected_document_ids,
        ),
        "purity_at_5": round(
            purity_at_k(retrieved_document_ids, expected_document_ids, 5),
            6,
        ),
        "retrieved_document_ids_top10": retrieved_document_ids[:10],
        "retrieved_chunk_types_top10": retrieved_chunk_types[:10],
    }

    for k in K_VALUES:
        metrics[f"expected_document_recall_at_{k}"] = round(
            document_recall_at_k(retrieved_document_ids, expected_document_ids, k),
            6,
        )

    if expected_chunk_types:
        for k in (3, 5, 10):
            metrics[f"expected_chunk_type_coverage_at_{k}"] = round(
                chunk_type_coverage_at_k(retrieved_chunk_types, expected_chunk_types, k),
                6,
            )

    return {
        "case_id": case["case_id"],
        "category_id": case["category_id"],
        "category_name": case["category_name"],
        "question": case["question"],
        "company_filters": case.get("company_filters") or [],
        "expected_document_ids": expected_document_ids,
        "expected_chunk_types": expected_chunk_types,
        "metrics": metrics,
    }


def summarize_group(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [result["metrics"]["latency_seconds"] for result in case_results]
    top_scores = [
        result["metrics"]["top_score"]
        for result in case_results
        if result["metrics"]["top_score"] is not None
    ]
    summary: dict[str, Any] = {
        "case_count": len(case_results),
        "mean_latency_seconds": round(mean(latencies) or 0.0, 3),
        "p95_latency_seconds": round(percentile(latencies, 0.95) or 0.0, 3),
        "mean_top_score": round(mean(top_scores) or 0.0, 6),
        "top1_expected_document_hit_rate": round(
            mean(
                [result["metrics"]["top1_expected_document_hit"] for result in case_results]
            )
            or 0.0,
            6,
        ),
        "purity_at_5_mean": round(
            mean([result["metrics"]["purity_at_5"] for result in case_results]) or 0.0,
            6,
        ),
    }

    for k in K_VALUES:
        summary[f"expected_document_recall_at_{k}_mean"] = round(
            mean(
                [result["metrics"][f"expected_document_recall_at_{k}"] for result in case_results]
            )
            or 0.0,
            6,
        )

    chunk_type_cases = [
        result for result in case_results if result.get("expected_chunk_types")
    ]
    if chunk_type_cases:
        for k in (3, 5, 10):
            summary[f"expected_chunk_type_coverage_at_{k}_mean"] = round(
                mean(
                    [
                        result["metrics"].get(f"expected_chunk_type_coverage_at_{k}", 0.0)
                        for result in chunk_type_cases
                    ]
                )
                or 0.0,
                6,
            )

    return summary


def summarize_by_category(case_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    category_names: dict[str, str] = {}

    for result in case_results:
        category_id = result["category_id"]
        grouped[category_id].append(result)
        category_names[category_id] = result["category_name"]

    summaries: list[dict[str, Any]] = []
    for category_id, results in grouped.items():
        summaries.append(
            {
                "category_id": category_id,
                "category_name": category_names[category_id],
                "summary": summarize_group(results),
            }
        )

    summaries.sort(key=lambda item: item["category_name"])
    return summaries


def main() -> int:
    ensure_data_dir()
    benchmark = load_json(CATEGORY_BENCHMARK_PATH)
    supported_cases = [
        case
        for case in benchmark["cases"]
        if case.get("answer_expectation") == "supported"
    ]

    results: list[dict[str, Any]] = []
    for case in supported_cases:
        results.append(evaluate_case(case))
        save_json({"summary": {}, "by_category": [], "cases": results}, CATEGORY_RETRIEVAL_OUTPUT_PATH)

    output = {
        "summary": summarize_group(results),
        "by_category": summarize_by_category(results),
        "cases": results,
    }
    save_json(output, CATEGORY_RETRIEVAL_OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
