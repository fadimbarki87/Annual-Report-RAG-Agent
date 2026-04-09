from __future__ import annotations

import json
import logging
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CHUNK_DIR = BASE_DIR / "data" / "chunks"
PROCESSED_DIR = BASE_DIR.parent / "parsing" / "data" / "processed"
OUTPUT_PATH = CHUNK_DIR / "chunking_quality_evaluation.json"

HEADING_ROLES = {"title", "sectionHeading"}
EXCLUDED_PARAGRAPH_ROLES = {"pageHeader", "pageFooter", "pageNumber"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)


def list_chunk_files() -> list[Path]:
    if not CHUNK_DIR.exists():
        return []

    return sorted(
        path
        for path in CHUNK_DIR.iterdir()
        if path.is_file()
        and path.name.endswith("_chunks.json")
        and "evaluation" not in path.stem.casefold()
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


def summarize_numeric(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "p50": None,
            "p90": None,
            "max": None,
            "mean": None,
        }

    return {
        "count": len(values),
        "min": min(values),
        "p50": percentile([float(value) for value in values], 0.5),
        "p90": percentile([float(value) for value in values], 0.9),
        "max": max(values),
        "mean": round(statistics.mean(values), 6),
    }


def paragraph_page_numbers(paragraph: dict[str, Any]) -> list[Any]:
    page_numbers: list[Any] = []
    for region in paragraph.get("boundingRegions", []) or []:
        page_number = region.get("pageNumber")
        if page_number is not None and page_number not in page_numbers:
            page_numbers.append(page_number)
    return page_numbers


def build_paragraph_index(processed_doc: dict[str, Any]) -> dict[Any, list[dict[str, Any]]]:
    paragraphs_by_page: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for paragraph in processed_doc.get("paragraphs", []) or []:
        text = collapse_whitespace(paragraph.get("content", ""))
        if not text:
            continue

        page_numbers = paragraph_page_numbers(paragraph)
        if len(page_numbers) != 1:
            continue

        paragraphs_by_page[page_numbers[0]].append(
            {
                "text": text,
                "role": paragraph.get("role"),
            }
        )

    return paragraphs_by_page


def build_source_page_texts(processed_doc: dict[str, Any]) -> tuple[dict[int, str], dict[int, list[str]], dict[str, Any]]:
    pages = processed_doc.get("pages", []) or []
    paragraphs_by_page = build_paragraph_index(processed_doc)

    source_page_texts: dict[int, str] = {}
    headings_by_page: dict[int, list[str]] = {}
    paragraph_pages = 0
    clean_line_fallback_pages = 0

    for page in pages:
        page_number = page.get("page_number")
        if not isinstance(page_number, int):
            continue

        page_paragraphs = paragraphs_by_page.get(page_number, [])
        usable_paragraphs = [
            item["text"]
            for item in page_paragraphs
            if item.get("role") not in EXCLUDED_PARAGRAPH_ROLES
        ]
        page_headings = [
            item["text"]
            for item in page_paragraphs
            if item.get("role") in HEADING_ROLES
        ]

        if usable_paragraphs:
            paragraph_pages += 1
            source_page_texts[page_number] = "\n\n".join(usable_paragraphs)
        else:
            clean_line_fallback_pages += 1
            clean_line_text = "\n".join(
                collapse_whitespace(line.get("text", ""))
                for line in page.get("clean_lines", []) or []
                if collapse_whitespace(line.get("text", ""))
            )
            source_page_texts[page_number] = clean_line_text

        headings_by_page[page_number] = page_headings

    source_stats = {
        "paragraph_source_pages": paragraph_pages,
        "clean_line_fallback_source_pages": clean_line_fallback_pages,
    }

    return source_page_texts, headings_by_page, source_stats


def build_chunk_page_texts(chunk_doc: dict[str, Any]) -> tuple[dict[int, list[str]], dict[int, list[str]], dict[str, Any]]:
    text_by_page: dict[int, list[str]] = defaultdict(list)
    section_titles_by_page: dict[int, list[str]] = defaultdict(list)
    chunks = chunk_doc.get("chunks", []) or []
    cross_page_text_chunks = 0

    for chunk in chunks:
        page_numbers = [
            page_number
            for page_number in chunk.get("page_numbers", []) or []
            if isinstance(page_number, int)
        ]
        if not page_numbers:
            continue

        if chunk.get("chunk_type") in {"text", "visual"}:
            if len(set(page_numbers)) > 1:
                cross_page_text_chunks += 1

            chunk_text = collapse_whitespace(chunk.get("text", ""))
            for page_number in page_numbers:
                if chunk_text:
                    text_by_page[page_number].append(chunk_text)
                for title in chunk.get("section_titles", []) or []:
                    normalized_title = collapse_whitespace(title)
                    if normalized_title:
                        section_titles_by_page[page_number].append(normalized_title)

    chunk_stats = {
        "cross_page_text_chunk_count": cross_page_text_chunks,
    }
    return text_by_page, section_titles_by_page, chunk_stats


def token_overlap_counts(reference_tokens: list[str], hypothesis_tokens: list[str]) -> tuple[int, int, int]:
    reference_counter = Counter(reference_tokens)
    hypothesis_counter = Counter(hypothesis_tokens)
    matched = sum(
        min(reference_counter[token], hypothesis_counter[token])
        for token in reference_counter.keys() | hypothesis_counter.keys()
    )
    return matched, len(reference_tokens), len(hypothesis_tokens)


def find_matching_processed_file(chunk_path: Path) -> Path | None:
    base_name = chunk_path.stem.removesuffix("_chunks")
    candidate = PROCESSED_DIR / f"{base_name}_processed.json"
    if candidate.exists():
        return candidate
    return None


def unique_table_ids(chunks: list[dict[str, Any]]) -> set[tuple[int, int]]:
    table_ids: set[tuple[int, int]] = set()
    for chunk in chunks:
        if chunk.get("chunk_type") != "table":
            continue
        page_start = chunk.get("page_start")
        table_metadata = chunk.get("table_metadata") or {}
        table_index = table_metadata.get("table_index")
        if isinstance(page_start, int) and isinstance(table_index, int):
            table_ids.add((page_start, table_index))
    return table_ids


def processed_table_ids(processed_doc: dict[str, Any]) -> set[tuple[int, int]]:
    table_ids: set[tuple[int, int]] = set()
    for page in processed_doc.get("pages", []) or []:
        page_number = page.get("page_number")
        if not isinstance(page_number, int):
            continue
        for table_index, _table in enumerate(page.get("tables", []) or [], start=1):
            table_ids.add((page_number, table_index))
    return table_ids


def evaluate_document(chunk_path: Path) -> dict[str, Any]:
    chunk_doc = load_json(chunk_path)
    chunks = chunk_doc.get("chunks", []) or []
    chunking_metadata = chunk_doc.get("chunking_metadata", {}) or {}

    processed_path = find_matching_processed_file(chunk_path)
    processed_doc = load_json(processed_path) if processed_path is not None else {}

    source_page_texts, headings_by_page, source_stats = build_source_page_texts(processed_doc)
    chunk_page_texts, section_titles_by_page, chunk_stats = build_chunk_page_texts(chunk_doc)

    source_page_numbers = sorted(source_page_texts.keys())
    chunk_page_numbers = sorted(
        {
            page_number
            for chunk in chunks
            for page_number in (chunk.get("page_numbers") or [])
            if isinstance(page_number, int)
        }
    )

    total_source_tokens = 0
    total_chunk_tokens = 0
    total_matched_tokens = 0

    headings_total = 0
    headings_covered = 0

    for page_number in source_page_numbers:
        source_tokens = tokenize(source_page_texts.get(page_number, ""))
        chunk_text = "\n\n".join(chunk_page_texts.get(page_number, []))
        chunk_tokens = tokenize(chunk_text)

        matched_tokens, source_token_count, chunk_token_count = token_overlap_counts(
            source_tokens,
            chunk_tokens,
        )
        total_source_tokens += source_token_count
        total_chunk_tokens += chunk_token_count
        total_matched_tokens += matched_tokens

        searchable_page_text = normalize_text(chunk_text)
        searchable_titles = " || ".join(section_titles_by_page.get(page_number, []))
        searchable_titles = normalize_text(searchable_titles)

        for heading in headings_by_page.get(page_number, []):
            normalized_heading = normalize_text(heading)
            if not normalized_heading:
                continue
            headings_total += 1
            if normalized_heading in searchable_page_text or normalized_heading in searchable_titles:
                headings_covered += 1

    token_precision = safe_ratio(total_matched_tokens, total_chunk_tokens)
    token_recall = safe_ratio(total_matched_tokens, total_source_tokens)
    token_f1 = None
    if token_precision is not None and token_recall is not None and (token_precision + token_recall) > 0:
        token_f1 = round(2 * token_precision * token_recall / (token_precision + token_recall), 6)

    text_chunks = [chunk for chunk in chunks if chunk.get("chunk_type") in {"text", "visual"}]
    text_chunk_char_counts = [len(collapse_whitespace(chunk.get("text", ""))) for chunk in text_chunks]
    text_chunk_word_counts = [len(tokenize(chunk.get("text", ""))) for chunk in text_chunks]

    table_ids_source = processed_table_ids(processed_doc)
    table_ids_chunked = unique_table_ids(chunks)

    source_page_count = len(processed_doc.get("pages", []) or [])

    metrics = {
        "page_coverage_rate": safe_ratio(len(set(chunk_page_numbers)), source_page_count),
        "table_coverage_rate": safe_ratio(len(table_ids_chunked), len(table_ids_source)),
        "source_token_recall": token_recall,
        "chunk_token_precision": token_precision,
        "chunk_token_f1": token_f1,
        "heading_coverage_rate": safe_ratio(headings_covered, headings_total),
        "chunk_text_to_source_token_ratio": (
            round(total_chunk_tokens / total_source_tokens, 6) if total_source_tokens > 0 else None
        ),
        "text_chunk_char_metrics": summarize_numeric(text_chunk_char_counts),
        "text_chunk_word_metrics": summarize_numeric(text_chunk_word_counts),
        "target_text_chunk_rate_chars_800_1500": safe_ratio(
            sum(1 for count in text_chunk_char_counts if 800 <= count <= 1500),
            len(text_chunk_char_counts),
        ),
        "small_text_chunk_rate_chars_lt_400": safe_ratio(
            sum(1 for count in text_chunk_char_counts if count < 400),
            len(text_chunk_char_counts),
        ),
        "oversized_text_chunk_rate_chars_gt_1500": safe_ratio(
            sum(1 for count in text_chunk_char_counts if count > 1500),
            len(text_chunk_char_counts),
        ),
        "cross_page_text_chunk_rate": safe_ratio(
            chunk_stats["cross_page_text_chunk_count"],
            len(text_chunks),
        ),
        "pages_using_paragraphs_rate": safe_ratio(
            int(chunking_metadata.get("pages_using_paragraphs") or 0),
            source_page_count,
        ),
        "pages_using_line_fallback_rate": safe_ratio(
            int(chunking_metadata.get("pages_using_line_fallback") or 0),
            source_page_count,
        ),
    }

    return {
        "document_id": chunk_path.stem.removesuffix("_chunks"),
        "metrics": metrics,
    }


def build_report(documents: list[dict[str, Any]]) -> dict[str, Any]:
    overall_numeric_metrics: dict[str, float] = {}

    scalar_metric_names = sorted(
        {
            metric_name
            for document in documents
            for metric_name, metric_value in document.get("metrics", {}).items()
            if isinstance(metric_value, (int, float))
        }
    )

    for metric_name in scalar_metric_names:
        values = [
            float(document["metrics"][metric_name])
            for document in documents
            if isinstance(document["metrics"].get(metric_name), (int, float))
        ]
        if values:
            overall_numeric_metrics[metric_name] = round(statistics.mean(values), 6)

    return {
        "overall_numeric_metrics_mean": overall_numeric_metrics,
        "documents": documents,
    }


def main() -> int:
    ensure_directories()
    chunk_files = list_chunk_files()

    if not chunk_files:
        logger.warning("No chunk JSON files found in %s", CHUNK_DIR)
        save_json(build_report([]), OUTPUT_PATH)
        return 0

    documents = [evaluate_document(path) for path in chunk_files]
    save_json(build_report(documents), OUTPUT_PATH)
    logger.info("Wrote chunking quality metrics to %s", OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
