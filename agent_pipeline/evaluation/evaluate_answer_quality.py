from __future__ import annotations

import re
import sys
import time
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
from agent_pipeline.evaluation.common import (
    ANSWER_OUTPUT_PATH,
    BENCHMARK_PATH,
    ensure_data_dir,
    load_json,
    mean,
    percentile,
    save_json,
)
from agent_pipeline.evaluation.llm_judge import judge_supported_answer


SECTION_HEADINGS = ("Answer", "Reporting Period", "Resources", "Evidence")


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


def resources_present(text: str, expected_resources: list[dict[str, Any]]) -> bool:
    normalized = text.casefold()
    for resource in expected_resources:
        company = str(resource["company"]).casefold()
        source_file = str(resource["source_file"]).casefold()
        page = str(resource["page"]).casefold()
        if company not in normalized or source_file not in normalized or page not in normalized:
            return False
    return True


def format_compliant(answer: str) -> bool:
    sections = parse_sections(answer)
    return all(heading in sections for heading in ("Answer", "Resources", "Evidence"))


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
    sections = parse_sections(generated_answer)
    result: dict[str, Any] = {
        "case_id": case["case_id"],
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

    expected_resources = case.get("expected_resources") or []
    judge_scores = judge_supported_answer(
        question=case["question"],
        gold_answer=case["gold_answer"],
        expected_resources=expected_resources,
        generated_answer=generated_answer,
        settings=settings,
    )
    rule_based_format = 1.0 if format_compliant(generated_answer) else 0.0
    rule_based_resources = 1.0 if resources_present(generated_answer, expected_resources) else 0.0

    result["metrics"] = {
        "format_compliance_rule": rule_based_format,
        "resource_presence_rule": rule_based_resources,
        "llm_correctness": judge_scores["correctness"],
        "llm_groundedness": judge_scores["groundedness"],
        "llm_citation_accuracy": judge_scores["citation_accuracy"],
        "llm_completeness": judge_scores["completeness"],
        "llm_format_compliance": judge_scores["format_compliance"],
        "llm_notes": judge_scores["notes"],
        "llm_answer_quality_mean": round(
            mean(
                [
                    judge_scores["correctness"],
                    judge_scores["groundedness"],
                    judge_scores["citation_accuracy"],
                    judge_scores["completeness"],
                    judge_scores["format_compliance"],
                ]
            )
            or 0.0,
            6,
        ),
    }
    return result


def summarize(case_results: list[dict[str, Any]]) -> dict[str, Any]:
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
        "format_compliance_rule_rate": round(
            mean([result["metrics"]["format_compliance_rule"] for result in supported]) or 0.0,
            6,
        ),
        "resource_presence_rule_rate": round(
            mean([result["metrics"]["resource_presence_rule"] for result in supported]) or 0.0,
            6,
        ),
        "llm_correctness_mean": round(
            mean([result["metrics"]["llm_correctness"] for result in supported]) or 0.0,
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
        "llm_format_compliance_mean": round(
            mean([result["metrics"]["llm_format_compliance"] for result in supported]) or 0.0,
            6,
        ),
        "llm_answer_quality_mean": round(
            mean([result["metrics"]["llm_answer_quality_mean"] for result in supported]) or 0.0,
            6,
        ),
    }
    return summary


def main() -> int:
    ensure_data_dir()
    benchmark = load_json(BENCHMARK_PATH)
    settings = load_answer_generation_settings()
    results = [evaluate_case(case, settings) for case in benchmark["cases"]]

    output = {
        "summary": summarize(results),
        "cases": results,
    }
    save_json(output, ANSWER_OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
