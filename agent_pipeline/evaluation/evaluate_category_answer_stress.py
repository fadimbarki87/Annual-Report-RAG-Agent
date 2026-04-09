from __future__ import annotations

import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from agent_pipeline.answer_generation.answer_generator import answer_question
from agent_pipeline.answer_generation.scope_guard import (
    NO_STRONG_ANSWER_RESPONSE,
    UNSUPPORTED_RESPONSE,
)
from agent_pipeline.answer_generation.settings import load_answer_generation_settings
from agent_pipeline.evaluation.category_llm_judge import judge_supported_answer
from agent_pipeline.evaluation.common import (
    CATEGORY_ANSWER_OUTPUT_PATH,
    CATEGORY_BENCHMARK_PATH,
    ensure_data_dir,
    load_json,
    mean,
    percentile,
    save_json,
)
from agent_pipeline.retrieval.document_registry import document_info


def parse_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^(Answer|Reporting Period|Resources|Evidence)\s*$", text))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[heading] = text[start:end].strip()
    return sections


def format_compliant(answer: str) -> bool:
    sections = parse_sections(answer)
    return all(heading in sections for heading in ("Answer", "Resources", "Evidence"))


def resources_present(answer: str) -> bool:
    sections = parse_sections(answer)
    resources = sections.get("Resources", "").strip()
    evidence = sections.get("Evidence", "").strip()
    return bool(resources and evidence and resources.casefold() != "none" and evidence.casefold() != "none")


def supported_nonrefusal(answer: str) -> bool:
    normalized = answer.strip()
    return normalized not in {
        UNSUPPORTED_RESPONSE,
        NO_STRONG_ANSWER_RESPONSE,
        "I do not find sufficient data in the documents to compute this.",
        "I only have data from the 2024 annual reports unless prior-year information is explicitly stated in them.",
    }


def expected_documents_present(answer: str, expected_document_ids: list[str]) -> bool:
    if not expected_document_ids:
        return True
    normalized = answer.casefold()
    for document_id in expected_document_ids:
        info = document_info(document_id)
        if info is None:
            continue
        if info.company_name.casefold() not in normalized and info.source_file.casefold() not in normalized:
            return False
    return True


def evaluate_case(case: dict[str, Any], settings: Any) -> dict[str, Any]:
    start = time.perf_counter()
    generated_answer = answer_question(
        question=case["question"],
        company_filters=case.get("company_filters") or [],
        chunk_types=case.get("chunk_types") or [],
        settings=settings,
    )
    elapsed = time.perf_counter() - start

    expectation = case["answer_expectation"]
    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "category_id": case["category_id"],
        "category_name": case["category_name"],
        "question": case["question"],
        "answer_expectation": expectation,
        "latency_seconds": round(elapsed, 3),
        "generated_answer": generated_answer,
    }

    if expectation == "unsupported":
        result["metrics"] = {
            "exact_refusal_match": 1.0 if generated_answer.strip() == UNSUPPORTED_RESPONSE else 0.0
        }
        return result

    if expectation == "no_strong_answer":
        result["metrics"] = {
            "exact_refusal_match": 1.0 if generated_answer.strip() == NO_STRONG_ANSWER_RESPONSE else 0.0
        }
        return result

    if not supported_nonrefusal(generated_answer):
        result["metrics"] = {
            "format_compliance_rule": 0.0,
            "resource_presence_rule": 0.0,
            "expected_document_presence_rule": 0.0,
            "supported_nonrefusal_rule": 0.0,
            "llm_relevance": 0.0,
            "llm_groundedness": 0.0,
            "llm_citation_accuracy": 0.0,
            "llm_completeness": 0.0,
            "llm_instruction_following": 0.0,
            "llm_notes": "Supported case was refused.",
            "llm_answer_quality_mean": 0.0,
        }
        return result

    judge_scores = judge_supported_answer(
        question=case["question"],
        expected_document_ids=case.get("expected_document_ids") or [],
        generated_answer=generated_answer,
        settings=settings,
    )
    result["metrics"] = {
        "format_compliance_rule": 1.0 if format_compliant(generated_answer) else 0.0,
        "resource_presence_rule": 1.0 if resources_present(generated_answer) else 0.0,
        "expected_document_presence_rule": 1.0
        if expected_documents_present(generated_answer, case.get("expected_document_ids") or [])
        else 0.0,
        "supported_nonrefusal_rule": 1.0,
        "llm_relevance": judge_scores["relevance"],
        "llm_groundedness": judge_scores["groundedness"],
        "llm_citation_accuracy": judge_scores["citation_accuracy"],
        "llm_completeness": judge_scores["completeness"],
        "llm_instruction_following": judge_scores["instruction_following"],
        "llm_notes": judge_scores["notes"],
        "llm_answer_quality_mean": round(
            mean(
                [
                    judge_scores["relevance"],
                    judge_scores["groundedness"],
                    judge_scores["citation_accuracy"],
                    judge_scores["completeness"],
                    judge_scores["instruction_following"],
                ]
            )
            or 0.0,
            6,
        ),
    }
    return result


def summarize_group(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [result["latency_seconds"] for result in case_results]
    supported = [result for result in case_results if result["answer_expectation"] == "supported"]
    unsupported = [result for result in case_results if result["answer_expectation"] == "unsupported"]
    no_strong = [result for result in case_results if result["answer_expectation"] == "no_strong_answer"]

    summary: dict[str, Any] = {
        "case_count": len(case_results),
        "supported_case_count": len(supported),
        "unsupported_case_count": len(unsupported),
        "no_strong_answer_case_count": len(no_strong),
        "mean_latency_seconds": round(mean(latencies) or 0.0, 3),
        "p95_latency_seconds": round(percentile(latencies, 0.95) or 0.0, 3),
        "unsupported_refusal_accuracy": round(
            mean([result["metrics"]["exact_refusal_match"] for result in unsupported]) or 0.0,
            6,
        ),
        "no_strong_answer_accuracy": round(
            mean([result["metrics"]["exact_refusal_match"] for result in no_strong]) or 0.0,
            6,
        ),
        "supported_format_compliance_rate": round(
            mean([result["metrics"]["format_compliance_rule"] for result in supported]) or 0.0,
            6,
        ),
        "supported_resource_presence_rate": round(
            mean([result["metrics"]["resource_presence_rule"] for result in supported]) or 0.0,
            6,
        ),
        "supported_expected_document_presence_rate": round(
            mean([result["metrics"]["expected_document_presence_rule"] for result in supported]) or 0.0,
            6,
        ),
        "supported_nonrefusal_rate": round(
            mean([result["metrics"]["supported_nonrefusal_rule"] for result in supported]) or 0.0,
            6,
        ),
        "llm_relevance_mean": round(
            mean([result["metrics"]["llm_relevance"] for result in supported]) or 0.0,
            6,
        ),
        "llm_groundedness_mean": round(
            mean([result["metrics"]["llm_groundedness"] for result in supported]) or 0.0,
            6,
        ),
        "llm_citation_accuracy_mean": round(
            mean([result["metrics"]["llm_citation_accuracy"] for result in supported]) or 0.0,
            6,
        ),
        "llm_completeness_mean": round(
            mean([result["metrics"]["llm_completeness"] for result in supported]) or 0.0,
            6,
        ),
        "llm_instruction_following_mean": round(
            mean([result["metrics"]["llm_instruction_following"] for result in supported]) or 0.0,
            6,
        ),
        "llm_answer_quality_mean": round(
            mean([result["metrics"]["llm_answer_quality_mean"] for result in supported]) or 0.0,
            6,
        ),
    }
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


def load_existing_partial_results() -> list[dict[str, Any]]:
    if not CATEGORY_ANSWER_OUTPUT_PATH.exists():
        return []

    try:
        existing = load_json(CATEGORY_ANSWER_OUTPUT_PATH)
    except Exception:
        return []

    cases = existing.get("cases")
    if not isinstance(cases, list):
        return []

    valid_results: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        if "case_id" not in case or "generated_answer" not in case or "metrics" not in case:
            continue
        valid_results.append(case)

    return valid_results


def main() -> int:
    ensure_data_dir()
    benchmark = load_json(CATEGORY_BENCHMARK_PATH)
    settings = load_answer_generation_settings()
    results = load_existing_partial_results()
    completed_case_ids = {result["case_id"] for result in results}

    for case in benchmark["cases"]:
        if case["case_id"] in completed_case_ids:
            continue
        results.append(evaluate_case(case, settings))
        save_json({"summary": {}, "by_category": [], "cases": results}, CATEGORY_ANSWER_OUTPUT_PATH)

    output = {
        "summary": summarize_group(results),
        "by_category": summarize_by_category(results),
        "cases": results,
    }
    save_json(output, CATEGORY_ANSWER_OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
