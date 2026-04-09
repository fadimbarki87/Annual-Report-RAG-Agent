from __future__ import annotations

import json
import logging
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw_azure"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PDF_DIR = BASE_DIR / "data" / "pdfs"
OUTPUT_PATH = PROCESSED_DIR / "parsing_quality_evaluation.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def list_processed_files() -> list[Path]:
    if not PROCESSED_DIR.exists():
        return []

    return sorted(
        path
        for path in PROCESSED_DIR.iterdir()
        if path.is_file() and path.name.endswith("_processed.json")
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_json(data: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, indent=2)


def collapse_whitespace(text: Any) -> str:
    if text is None:
        return ""

    text = str(text).replace("\u00a0", " ").replace("\u00ad", "")
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(text: Any) -> str:
    return collapse_whitespace(text).casefold()


def tokenize(text: Any) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return normalized.split()


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def agreement_rate(expected: int | None, actual: int | None) -> float | None:
    if expected is None or actual is None:
        return None
    if expected == actual:
        return 1.0
    if expected == 0 or actual == 0:
        return 0.0
    return round(min(expected, actual) / max(expected, actual), 6)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 6)

    ordered = sorted(values)
    index = (len(ordered) - 1) * pct
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    value = ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction
    return round(value, 6)


def count_non_empty_raw_lines(raw_pages: list[dict[str, Any]]) -> int:
    count = 0
    for page in raw_pages:
        for line in page.get("lines", []) or []:
            if collapse_whitespace(line.get("content", "")):
                count += 1
    return count


def count_processed_items(pages: list[dict[str, Any]], key: str) -> int:
    total = 0
    for page in pages:
        total += len(page.get(key, []) or [])
    return total


def get_result_root(raw_doc: dict[str, Any]) -> dict[str, Any]:
    for key in ("result", "analyzeResult"):
        value = raw_doc.get(key)
        if isinstance(value, dict):
            return value
    return raw_doc


def optional_structure_counts(document: dict[str, Any]) -> dict[str, int]:
    return {
        "paragraphs": len(document.get("paragraphs", []) or []),
        "sections": len(document.get("sections", []) or []),
        "styles": len(document.get("styles", []) or []),
        "figures": len(document.get("figures", []) or []),
    }


def find_matching_raw_file(processed_path: Path) -> Path | None:
    base_name = processed_path.stem.removesuffix("_processed")
    preferred = RAW_DIR / f"{base_name}_layout.json"
    if preferred.exists():
        return preferred

    candidates = sorted(RAW_DIR.glob(f"{base_name}*.json"))
    return candidates[0] if candidates else None


def find_matching_pdf_file(processed_doc: dict[str, Any], processed_path: Path) -> Path | None:
    source_file = collapse_whitespace(processed_doc.get("source_file"))
    if source_file:
        candidate = PDF_DIR / source_file
        if candidate.exists():
            return candidate

    base_name = processed_path.stem.removesuffix("_processed")
    candidate = PDF_DIR / f"{base_name}.pdf"
    if candidate.exists():
        return candidate

    return None


def extract_pdf_page_tokens(pdf_path: Path) -> list[list[str]]:
    page_tokens: list[list[str]] = []
    with fitz.open(pdf_path) as document:
        for page in document:
            page_tokens.append(tokenize(page.get_text("text")))
    return page_tokens


def processed_page_tokens(processed_doc: dict[str, Any]) -> list[list[str]]:
    pages = processed_doc.get("pages", []) or []
    page_tokens: list[list[str]] = []

    for page in pages:
        clean_lines = page.get("clean_lines", []) or []
        text = "\n".join(
            collapse_whitespace(line.get("text", ""))
            for line in clean_lines
            if collapse_whitespace(line.get("text", ""))
        )
        page_tokens.append(tokenize(text))

    return page_tokens


def token_overlap_counts(reference_tokens: list[str], hypothesis_tokens: list[str]) -> tuple[int, int, int]:
    reference_counter = Counter(reference_tokens)
    hypothesis_counter = Counter(hypothesis_tokens)
    matched = sum(
        min(reference_counter[token], hypothesis_counter[token])
        for token in reference_counter.keys() | hypothesis_counter.keys()
    )
    return matched, len(reference_tokens), len(hypothesis_tokens)


def levenshtein_distance(reference_tokens: list[str], hypothesis_tokens: list[str]) -> int:
    if not reference_tokens:
        return len(hypothesis_tokens)
    if not hypothesis_tokens:
        return len(reference_tokens)

    if len(reference_tokens) < len(hypothesis_tokens):
        reference_tokens, hypothesis_tokens = hypothesis_tokens, reference_tokens

    previous_row = list(range(len(hypothesis_tokens) + 1))

    for ref_index, ref_token in enumerate(reference_tokens, start=1):
        current_row = [ref_index]
        for hyp_index, hyp_token in enumerate(hypothesis_tokens, start=1):
            insertion_cost = current_row[hyp_index - 1] + 1
            deletion_cost = previous_row[hyp_index] + 1
            substitution_cost = previous_row[hyp_index - 1] + (ref_token != hyp_token)
            current_row.append(min(insertion_cost, deletion_cost, substitution_cost))
        previous_row = current_row

    return previous_row[-1]


def evaluate_pdf_text_fidelity(
    pdf_tokens_by_page: list[list[str]],
    processed_tokens_by_page: list[list[str]],
) -> dict[str, Any]:
    pages_evaluated = min(len(pdf_tokens_by_page), len(processed_tokens_by_page))

    total_reference_tokens = 0
    total_hypothesis_tokens = 0
    total_matched_tokens = 0
    total_word_edits = 0
    page_wers: list[float] = []
    pages_with_pdf_text = 0

    for page_index in range(pages_evaluated):
        reference_tokens = pdf_tokens_by_page[page_index]
        hypothesis_tokens = processed_tokens_by_page[page_index]

        if reference_tokens:
            pages_with_pdf_text += 1
            word_edits = levenshtein_distance(reference_tokens, hypothesis_tokens)
            total_word_edits += word_edits
            total_reference_tokens += len(reference_tokens)
            page_wers.append(word_edits / len(reference_tokens))
        total_hypothesis_tokens += len(hypothesis_tokens)

        matched_tokens, _, _ = token_overlap_counts(reference_tokens, hypothesis_tokens)
        total_matched_tokens += matched_tokens

    precision = safe_ratio(total_matched_tokens, total_hypothesis_tokens)
    recall = safe_ratio(total_matched_tokens, total_reference_tokens)
    f1 = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = round(2 * precision * recall / (precision + recall), 6)

    return {
        "pdf_page_count": len(pdf_tokens_by_page),
        "processed_page_count_for_text_eval": len(processed_tokens_by_page),
        "pdf_page_count_agreement_rate": agreement_rate(
            len(pdf_tokens_by_page),
            len(processed_tokens_by_page),
        ),
        "pages_evaluated_against_pdf": pages_evaluated,
        "pages_with_pdf_text": pages_with_pdf_text,
        "pages_with_pdf_text_rate": safe_ratio(pages_with_pdf_text, len(pdf_tokens_by_page)),
        "silver_pdf_word_error_rate": safe_ratio(total_word_edits, total_reference_tokens),
        "silver_pdf_word_precision": precision,
        "silver_pdf_word_recall": recall,
        "silver_pdf_word_f1": f1,
        "silver_pdf_page_wer_median": round(statistics.median(page_wers), 6) if page_wers else None,
        "silver_pdf_page_wer_p90": percentile(page_wers, 0.9),
    }


def evaluate_document(processed_path: Path) -> dict[str, Any]:
    processed_doc = load_json(processed_path)
    processed_pages = processed_doc.get("pages", []) or []
    processed_metadata = processed_doc.get("document_metadata", {}) or {}

    raw_path = find_matching_raw_file(processed_path)
    pdf_path = find_matching_pdf_file(processed_doc, processed_path)

    raw_metrics: dict[str, Any] = {}
    if raw_path is not None:
        raw_doc = load_json(raw_path)
        raw_root = get_result_root(raw_doc)
        raw_pages = raw_root.get("pages", []) or []

        processed_structure_counts = optional_structure_counts(processed_doc)
        raw_structure_counts = optional_structure_counts(raw_root)

        raw_metrics = {
            "raw_page_count_agreement_rate": agreement_rate(len(raw_pages), len(processed_pages)),
            "raw_line_preservation_rate": agreement_rate(
                count_non_empty_raw_lines(raw_pages),
                count_processed_items(processed_pages, "raw_lines"),
            ),
            "content_accounting_rate": agreement_rate(
                count_non_empty_raw_lines(raw_pages),
                count_processed_items(processed_pages, "clean_lines")
                + count_processed_items(processed_pages, "removed_lines"),
            ),
            "table_preservation_rate": agreement_rate(
                len(raw_root.get("tables", []) or []),
                count_processed_items(processed_pages, "tables"),
            ),
            "paragraph_preservation_rate": agreement_rate(
                raw_structure_counts["paragraphs"],
                processed_structure_counts["paragraphs"],
            ),
            "section_preservation_rate": agreement_rate(
                raw_structure_counts["sections"],
                processed_structure_counts["sections"],
            ),
            "style_preservation_rate": agreement_rate(
                raw_structure_counts["styles"],
                processed_structure_counts["styles"],
            ),
            "figure_preservation_rate": agreement_rate(
                raw_structure_counts["figures"],
                processed_structure_counts["figures"],
            ),
        }

    pdf_metrics: dict[str, Any] = {}
    if pdf_path is not None:
        pdf_metrics = evaluate_pdf_text_fidelity(
            extract_pdf_page_tokens(pdf_path),
            processed_page_tokens(processed_doc),
        )

    metrics = {
        "processed_page_count": len(processed_pages),
        "document_metadata_page_count": processed_metadata.get("page_count"),
        "document_metadata_table_count": processed_metadata.get("table_count"),
        "nonempty_processed_page_rate": safe_ratio(
            sum(
                1
                for page in processed_pages
                if (page.get("clean_lines") or []) or (page.get("tables") or [])
            ),
            len(processed_pages),
        ),
        **raw_metrics,
        **pdf_metrics,
    }

    return {
        "document_id": processed_path.stem.removesuffix("_processed"),
        "metrics": metrics,
    }


def build_report(documents: list[dict[str, Any]]) -> dict[str, Any]:
    overall_metrics: dict[str, float] = {}
    metric_names = sorted(
        {
            metric_name
            for document in documents
            for metric_name in document.get("metrics", {})
            if isinstance(document.get("metrics", {}).get(metric_name), (int, float))
            and document.get("metrics", {}).get(metric_name) is not None
        }
    )

    for metric_name in metric_names:
        values = [
            float(document["metrics"][metric_name])
            for document in documents
            if isinstance(document["metrics"].get(metric_name), (int, float))
        ]
        if values:
            overall_metrics[metric_name] = round(statistics.mean(values), 6)

    return {
        "overall_metrics_mean": overall_metrics,
        "documents": documents,
    }


def main() -> int:
    ensure_directories()
    processed_files = list_processed_files()

    if not processed_files:
        logger.warning("No processed JSON files found in %s", PROCESSED_DIR)
        save_json(build_report([]), OUTPUT_PATH)
        return 0

    documents = [evaluate_document(path) for path in processed_files]
    save_json(build_report(documents), OUTPUT_PATH)
    logger.info("Wrote parsing quality metrics to %s", OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
