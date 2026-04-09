from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
RAW_INPUT_DIR = BASE_DIR / "data" / "raw_azure"
PROCESSED_OUTPUT_DIR = BASE_DIR / "data" / "processed"

# Conservative margin settings for repeated header/footer candidate detection.
# Azure layout results for PDFs are commonly expressed in inches, but we also
# support a relative fallback for other or missing units.
HEADER_TOP_THRESHOLD_IN = 0.9
FOOTER_BOTTOM_THRESHOLD_IN = 0.9
HEADER_FOOTER_MARGIN_RATIO = 0.08
MIN_REPEAT_PAGES = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    RAW_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def list_raw_json_files() -> list[Path]:
    return sorted(
        path
        for path in RAW_INPUT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".json"
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def collapse_whitespace(text: Any) -> str:
    if text is None:
        return ""

    text = str(text).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_repeat_key(text: str) -> str:
    return collapse_whitespace(text).casefold()


def extract_polygon_bounds(polygon: list[Any]) -> dict[str, float | None]:
    if not isinstance(polygon, list) or len(polygon) < 8:
        return {
            "left": None,
            "right": None,
            "top": None,
            "bottom": None,
        }

    try:
        xs = [float(value) for value in polygon[0::2]]
        ys = [float(value) for value in polygon[1::2]]
    except (TypeError, ValueError):
        return {
            "left": None,
            "right": None,
            "top": None,
            "bottom": None,
        }

    return {
        "left": min(xs) if xs else None,
        "right": max(xs) if xs else None,
        "top": min(ys) if ys else None,
        "bottom": max(ys) if ys else None,
    }


def build_line_record(line: dict[str, Any]) -> dict[str, Any] | None:
    text = collapse_whitespace(line.get("content", ""))
    if not text:
        return None

    polygon = line.get("polygon", [])
    if isinstance(polygon, tuple):
        polygon = list(polygon)
    elif not isinstance(polygon, list):
        polygon = []

    bounds = extract_polygon_bounds(polygon)
    return {
        "text": text,
        "polygon": polygon,
        "left": bounds["left"],
        "right": bounds["right"],
        "top": bounds["top"],
        "bottom": bounds["bottom"],
    }


def build_page_line_records(page: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for line in page.get("lines", []) or []:
        record = build_line_record(line)
        if record is not None:
            records.append(record)

    return records


def classify_page_type(line_count: int, table_count: int) -> str:
    if table_count > 0 and line_count <= 10:
        return "visual_or_table"
    if table_count > 0:
        return "mixed"
    if line_count <= 8:
        return "visual_or_cover"
    return "text"


def get_result_root(raw_doc: dict[str, Any]) -> dict[str, Any]:
    for key in ("result", "analyzeResult"):
        value = raw_doc.get(key)
        if isinstance(value, dict):
            return value

    return raw_doc


def build_table_page_map(
    tables: list[dict[str, Any]],
) -> tuple[dict[Any, list[dict[str, Any]]], list[dict[str, Any]]]:
    table_page_map: dict[Any, list[dict[str, Any]]] = {}
    unmapped_tables: list[dict[str, Any]] = []

    for table in tables:
        page_numbers: set[Any] = set()

        for region in table.get("boundingRegions", []) or []:
            page_number = region.get("pageNumber")
            if page_number is not None:
                page_numbers.add(page_number)

        if not page_numbers:
            unmapped_tables.append(table)
            continue

        for page_number in page_numbers:
            table_page_map.setdefault(page_number, []).append(table)

    return table_page_map, unmapped_tables


def get_margin_cutoffs(
    page_height: Any,
    page_unit: Any,
) -> tuple[float, float] | None:
    if not isinstance(page_height, (int, float)) or page_height <= 0:
        return None

    relative_margin = max(page_height * HEADER_FOOTER_MARGIN_RATIO, 0.0)

    if isinstance(page_unit, str) and page_unit.lower() == "inch":
        top_margin = min(HEADER_TOP_THRESHOLD_IN, relative_margin or HEADER_TOP_THRESHOLD_IN)
        bottom_margin = min(
            FOOTER_BOTTOM_THRESHOLD_IN,
            relative_margin or FOOTER_BOTTOM_THRESHOLD_IN,
        )
    else:
        top_margin = relative_margin
        bottom_margin = relative_margin

    return top_margin, max(page_height - bottom_margin, 0.0)


def get_margin_position(
    line: dict[str, Any],
    page_height: Any,
    page_unit: Any,
) -> str | None:
    cutoffs = get_margin_cutoffs(page_height=page_height, page_unit=page_unit)
    if cutoffs is None:
        return None

    top_cutoff, bottom_cutoff = cutoffs
    top = line.get("top")
    bottom = line.get("bottom")

    if isinstance(top, (int, float)) and top <= top_cutoff:
        return "top"
    if isinstance(bottom, (int, float)) and bottom >= bottom_cutoff:
        return "bottom"
    return None


def get_min_repeat_pages(total_pages: int) -> int:
    if total_pages < 2:
        return 2
    return min(MIN_REPEAT_PAGES, total_pages)


def collect_repeated_header_footer_candidates(
    processed_pages: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int]:
    page_occurrence_counter: Counter[str] = Counter()
    sample_text_by_key: dict[str, str] = {}
    margin_positions_by_key: dict[str, set[str]] = defaultdict(set)

    for page in processed_pages:
        seen_on_page: set[str] = set()
        page_margin_positions: dict[str, set[str]] = defaultdict(set)

        for line in page["raw_lines"]:
            margin_position = get_margin_position(
                line=line,
                page_height=page["height"],
                page_unit=page["unit"],
            )
            if margin_position is None:
                continue

            key = normalize_repeat_key(line["text"])
            if not key:
                continue

            sample_text_by_key.setdefault(key, line["text"])
            seen_on_page.add(key)
            page_margin_positions[key].add(margin_position)

        for key in seen_on_page:
            page_occurrence_counter[key] += 1
            margin_positions_by_key[key].update(page_margin_positions[key])

    min_repeat_pages = get_min_repeat_pages(len(processed_pages))
    candidates: dict[str, dict[str, Any]] = {}

    for key, count in page_occurrence_counter.items():
        if count < min_repeat_pages:
            continue

        candidates[key] = {
            "text": sample_text_by_key[key],
            "normalized_text": key,
            "page_occurrence_count": count,
            "margin_positions": sorted(margin_positions_by_key[key]),
        }

    return candidates, min_repeat_pages


def preserve_optional_document_fields(result_root: dict[str, Any]) -> dict[str, Any]:
    preserved: dict[str, Any] = {}

    for field in ("paragraphs", "sections", "styles", "figures"):
        if field in result_root:
            preserved[field] = result_root.get(field)

    return preserved


def normalize_document(raw_doc: dict[str, Any]) -> dict[str, Any]:
    result_root = get_result_root(raw_doc)

    source_file = (
        raw_doc.get("source_file")
        or raw_doc.get("sourceFile")
        or raw_doc.get("source_path")
        or raw_doc.get("sourcePath")
    )
    model_id = (
        raw_doc.get("model_id")
        or raw_doc.get("modelId")
        or result_root.get("modelId")
        or "unknown"
    )

    pages = result_root.get("pages", []) or []
    tables = result_root.get("tables", []) or []
    table_page_map, unmapped_tables = build_table_page_map(tables)

    processed_pages: list[dict[str, Any]] = []

    for page in pages:
        page_number = page.get("pageNumber")
        page_width = page.get("width")
        page_height = page.get("height")
        page_unit = page.get("unit")

        raw_lines = build_page_line_records(page)
        clean_lines = [line.copy() for line in raw_lines]
        page_tables = table_page_map.get(page_number, [])

        processed_pages.append(
            {
                "page_number": page_number,
                "width": page_width,
                "height": page_height,
                "unit": page_unit,
                "raw_lines": raw_lines,
                "clean_lines": clean_lines,
                "header_footer_candidate_lines": [],
                "removed_lines": [],
                "tables": page_tables,
                "page_type": classify_page_type(
                    line_count=len(raw_lines),
                    table_count=len(page_tables),
                ),
            }
        )

    repeated_candidates, min_repeat_pages = collect_repeated_header_footer_candidates(
        processed_pages
    )

    for page in processed_pages:
        candidate_lines: list[dict[str, Any]] = []

        for line in page["raw_lines"]:
            margin_position = get_margin_position(
                line=line,
                page_height=page["height"],
                page_unit=page["unit"],
            )
            if margin_position is None:
                continue

            key = normalize_repeat_key(line["text"])
            candidate = repeated_candidates.get(key)
            if candidate is None:
                continue

            flagged_line = line.copy()
            flagged_line["candidate_type"] = "repeated_header_footer_candidate"
            flagged_line["margin_position"] = margin_position
            flagged_line["page_occurrence_count"] = candidate["page_occurrence_count"]
            candidate_lines.append(flagged_line)

        page["header_footer_candidate_lines"] = candidate_lines

    document_metadata = {
        "source_file": source_file,
        "model_id": model_id,
        "page_count": len(processed_pages),
        "table_count": len(tables),
        "unmapped_table_count": len(unmapped_tables),
        "api_version": result_root.get("apiVersion"),
        "content_format": result_root.get("contentFormat"),
        "string_index_type": result_root.get("stringIndexType"),
    }

    normalized_document = {
        "source_file": source_file,
        "model_id": model_id,
        "document_metadata": document_metadata,
        "detected_repeated_lines": {
            "header_footer_candidates": sorted(
                repeated_candidates.values(),
                key=lambda item: (-item["page_occurrence_count"], item["text"]),
            ),
            "min_repeat_pages": min_repeat_pages,
        },
        "pages": processed_pages,
    }

    normalized_document.update(preserve_optional_document_fields(result_root))

    return normalized_document


def build_output_path(raw_json_path: Path) -> Path:
    if raw_json_path.stem.endswith("_layout"):
        output_name = raw_json_path.stem.replace("_layout", "_processed") + ".json"
    else:
        output_name = raw_json_path.stem + "_processed.json"

    return PROCESSED_OUTPUT_DIR / output_name


def main() -> int:
    try:
        ensure_directories()

        raw_files = list_raw_json_files()
        if not raw_files:
            logger.warning("No raw Azure JSON files found in %s", RAW_INPUT_DIR.resolve())
            return 0

        successes = 0
        failures = 0

        for raw_path in raw_files:
            output_path = build_output_path(raw_path)

            try:
                logger.info("Normalizing %s", raw_path.name)
                raw_doc = load_json(raw_path)
                normalized = normalize_document(raw_doc)
                save_json(normalized, output_path)
                logger.info("Saved %s", output_path)
                successes += 1
            except Exception as exc:
                failures += 1
                logger.exception("Failed on %s: %s", raw_path.name, exc)

        logger.info("Finished. Successes=%s Failures=%s", successes, failures)
        return 0 if failures == 0 else 1

    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
