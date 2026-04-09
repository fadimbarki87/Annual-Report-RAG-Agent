from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from agent_pipeline.retrieval.retrieval_service import retrieve_chunks  # noqa: E402


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "data"
OUTPUT_PATH = OUTPUT_DIR / "baseline_retrieval_diagnostics.json"
TOP_K = 20


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    company_filters: tuple[str, ...]
    expected_text_group: tuple[str, ...] = ()
    expected_text_groups: tuple[tuple[str, ...], ...] = ()
    chunk_types: tuple[str, ...] = ()

    def expected_groups(self) -> tuple[tuple[str, ...], ...]:
        if self.expected_text_groups:
            return self.expected_text_groups
        return (self.expected_text_group,)


CASES = [
    RetrievalCase(
        case_id="bmw_group_revenue_2024",
        query="What were BMW Group revenues in 2024?",
        company_filters=("bmw",),
        expected_text_group=("2024: € 142,380 million", "Group revenues"),
    ),
    RetrievalCase(
        case_id="bmw_automotive_ebit_margin_outlook",
        query="What EBIT margin does BMW expect for the Automotive segment?",
        company_filters=("bmw",),
        expected_text_group=("EBIT margin is expected to be in the range of 5% to 7%",),
    ),
    RetrievalCase(
        case_id="bmw_scope_3_target",
        query="What reduction target did BMW set for Scope 3 automobile emissions?",
        company_filters=("bmw",),
        expected_text_group=("reduction of 27.5%", "Scope 3"),
    ),
    RetrievalCase(
        case_id="volkswagen_2025_outlook",
        query="What does Volkswagen expect for sales revenue and operating return on sales in 2025?",
        company_filters=("volkswagen",),
        expected_text_group=(
            "sales revenue of the Volkswagen Group",
            "between 5.5% and 6.5%",
        ),
    ),
    RetrievalCase(
        case_id="bosch_free_cash_flow",
        query="What was Bosch Group free cash flow in 2024?",
        company_filters=("bosch",),
        expected_text_group=("positive free cash flow of 0.9 billion euros",),
    ),
    RetrievalCase(
        case_id="bosch_cash_flow_table_liquidity",
        query="What was Bosch liquidity at the end of the year in the 2024 cash flow statement?",
        company_filters=("bosch",),
        chunk_types=("table",),
        expected_text_group=("Liquidity at the end of the year", "8,223"),
    ),
    RetrievalCase(
        case_id="mercedes_industrial_free_cash_flow",
        query="What was Mercedes-Benz free cash flow of the industrial business in 2024?",
        company_filters=("mercedes",),
        expected_text_group=("free cash flow of the industrial business amounted to €9.2 billion",),
    ),
    RetrievalCase(
        case_id="mercedes_industrial_free_cash_flow_table",
        query="Which Mercedes-Benz table gives free cash flow of the industrial business for 2024?",
        company_filters=("mercedes",),
        chunk_types=("table",),
        expected_text_group=("Free cash flow of the industrial business", "9,152"),
    ),
    RetrievalCase(
        case_id="siemens_dividend_2024",
        query="What dividend did Siemens propose for fiscal 2024?",
        company_filters=("siemens",),
        expected_text_group=("dividend of €5.20",),
    ),
    RetrievalCase(
        case_id="siemens_digital_industries_order_backlog",
        query="What was Digital Industries' order backlog at the end of fiscal 2024?",
        company_filters=("siemens",),
        expected_text_group=("Digital Industries' order backlog amounted to €9 billion",),
    ),
    RetrievalCase(
        case_id="siemens_smart_infrastructure_order_backlog",
        query="What was Smart Infrastructure's order backlog at the end of fiscal 2024?",
        company_filters=("siemens",),
        expected_text_group=("Smart Infrastructure's order backlog was €18 billion",),
    ),
    RetrievalCase(
        case_id="cross_company_bmw_volkswagen_outlook",
        query="Compare BMW and Volkswagen outlook for 2025.",
        company_filters=("bmw", "volkswagen"),
        expected_text_groups=(
            ("Outlook for the BMW Group",),
            ("sales revenue of the Volkswagen Group",),
        ),
    ),
]


def normalize_for_match(text: Any) -> str:
    return " ".join(str(text or "").casefold().replace("\u00a0", " ").split())


def find_group_rank(
    results: list[Any],
    expected_snippets: tuple[str, ...],
) -> int | None:
    expected = [normalize_for_match(snippet) for snippet in expected_snippets]

    for index, result in enumerate(results, start=1):
        text = normalize_for_match(result.payload.get("text"))
        if all(snippet in text for snippet in expected):
            return index

    return None


def find_expected_ranks(
    results: list[Any],
    expected_groups: tuple[tuple[str, ...], ...],
) -> list[int | None]:
    return [find_group_rank(results, expected_group) for expected_group in expected_groups]


def evaluate_case(case: RetrievalCase) -> dict[str, Any]:
    start = time.perf_counter()
    results = retrieve_chunks(
        query=case.query,
        company_filters=list(case.company_filters),
        chunk_types=list(case.chunk_types),
        limit=TOP_K,
    )
    elapsed_seconds = time.perf_counter() - start

    expected_ranks = find_expected_ranks(results, case.expected_groups())
    found_ranks = [rank for rank in expected_ranks if rank is not None]
    expected_rank = max(found_ranks) if len(found_ranks) == len(expected_ranks) else None
    top_documents = [result.payload.get("document_id") for result in results[:5]]
    top_chunk_ids = [result.payload.get("chunk_id") for result in results[:5]]

    return {
        "case_id": case.case_id,
        "query": case.query,
        "company_filters": list(case.company_filters),
        "chunk_types": list(case.chunk_types),
        "latency_seconds": round(elapsed_seconds, 3),
        "result_count": len(results),
        "expected_match_rank": expected_rank,
        "expected_group_ranks": expected_ranks,
        "hit_at_1": expected_rank is not None and expected_rank <= 1,
        "hit_at_3": expected_rank is not None and expected_rank <= 3,
        "hit_at_5": expected_rank is not None and expected_rank <= 5,
        "hit_at_10": expected_rank is not None and expected_rank <= 10,
        "hit_at_20": expected_rank is not None and expected_rank <= 20,
        "top_documents": top_documents,
        "top_chunk_ids": top_chunk_ids,
    }


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def build_summary(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(case_results)
    latencies = [float(result["latency_seconds"]) for result in case_results]

    return {
        "case_count": total,
        "top_k": TOP_K,
        "mean_latency_seconds": round(mean(latencies) or 0.0, 3),
        "max_latency_seconds": max(latencies) if latencies else None,
        "hit_at_1_rate": sum(1 for result in case_results if result["hit_at_1"]) / total,
        "hit_at_3_rate": sum(1 for result in case_results if result["hit_at_3"]) / total,
        "hit_at_5_rate": sum(1 for result in case_results if result["hit_at_5"]) / total,
        "hit_at_10_rate": sum(1 for result in case_results if result["hit_at_10"]) / total,
        "hit_at_20_rate": sum(1 for result in case_results if result["hit_at_20"]) / total,
        "missed_case_ids": [
            result["case_id"]
            for result in case_results
            if result["expected_match_rank"] is None
        ],
    }


def save_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, indent=2)


def main() -> int:
    results: list[dict[str, Any]] = []

    for case in CASES:
        result = evaluate_case(case)
        results.append(result)
        rank = result["expected_match_rank"] or "miss"
        print(
            f"{case.case_id}: rank={rank} | "
            f"latency={result['latency_seconds']:.3f}s | "
            f"top={result['top_chunk_ids'][0] if result['top_chunk_ids'] else 'none'}"
        )

    output = {
        "summary": build_summary(results),
        "cases": results,
    }
    save_json(output, OUTPUT_PATH)
    print(f"\nSaved diagnostics to {OUTPUT_PATH}")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
