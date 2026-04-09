from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR.parent / "parsing" / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "data" / "chunks"

TARGET_TEXT_CHARS = 1100
MIN_TEXT_CHARS = 800
MAX_TEXT_CHARS = 1500
SOFT_MAX_TEXT_CHARS = 1400
SMALL_CHUNK_MERGE_CHARS = 280
TINY_CHUNK_MERGE_CHARS = 140
MAX_TABLE_CHARS = 2200
MAX_SECTION_TITLES = 3

EXCLUDED_PARAGRAPH_ROLES = {"pageHeader", "pageFooter", "pageNumber"}
VISUAL_PAGE_TYPES = {"visual_or_table", "visual_or_cover"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def list_processed_json_files() -> list[Path]:
    if not INPUT_DIR.exists():
        return []

    return sorted(
        path
        for path in INPUT_DIR.iterdir()
        if path.is_file()
        and path.name.endswith("_processed.json")
        and "evaluation" not in path.stem.casefold()
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


def ordered_unique(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)

    return result


def sort_key_for_page_number(page_number: Any) -> tuple[int, str]:
    if isinstance(page_number, int):
        return (0, f"{page_number:08d}")
    return (1, str(page_number))


def sort_key_for_page(page: dict[str, Any]) -> tuple[int, str]:
    return sort_key_for_page_number(page.get("page_number"))


def slugify_filename(name: str) -> str:
    stem = Path(name).stem
    slug = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower()
    return slug or "document"


def build_output_path(input_path: Path) -> Path:
    if input_path.stem.endswith("_processed"):
        output_name = input_path.stem.replace("_processed", "_chunks") + ".json"
    else:
        output_name = input_path.stem + "_chunks.json"
    return OUTPUT_DIR / output_name


def round_coord(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value), 4)


def normalize_repeat_key(text: Any) -> str:
    return collapse_whitespace(text).casefold()


def extract_polygon_bounds(polygon: list[Any]) -> dict[str, float] | None:
    if not isinstance(polygon, list) or len(polygon) < 8:
        return None

    try:
        xs = [float(value) for value in polygon[0::2]]
        ys = [float(value) for value in polygon[1::2]]
    except (TypeError, ValueError):
        return None

    if not xs or not ys:
        return None

    return {
        "left": min(xs),
        "right": max(xs),
        "top": min(ys),
        "bottom": max(ys),
    }


def extract_region_bounds(
    bounding_regions: list[dict[str, Any]] | None,
    page_number: Any | None = None,
) -> list[dict[str, float]]:
    bounds_list: list[dict[str, float]] = []

    for region in bounding_regions or []:
        if page_number is not None and region.get("pageNumber") != page_number:
            continue
        bounds = extract_polygon_bounds(region.get("polygon") or [])
        if bounds is not None:
            bounds_list.append(bounds)

    return bounds_list


def is_center_inside_bounds(
    bounds: dict[str, Any] | None,
    container: dict[str, float],
) -> bool:
    if bounds is None:
        return False

    left = bounds.get("left")
    right = bounds.get("right")
    top = bounds.get("top")
    bottom = bounds.get("bottom")

    if not all(isinstance(value, (int, float)) for value in (left, right, top, bottom)):
        return False

    center_x = (float(left) + float(right)) / 2.0
    center_y = (float(top) + float(bottom)) / 2.0

    return (
        container["left"] <= center_x <= container["right"]
        and container["top"] <= center_y <= container["bottom"]
    )


def line_bounds(line: dict[str, Any]) -> dict[str, float] | None:
    left = line.get("left")
    right = line.get("right")
    top = line.get("top")
    bottom = line.get("bottom")

    if not all(isinstance(value, (int, float)) for value in (left, right, top, bottom)):
        return None

    return {
        "left": float(left),
        "right": float(right),
        "top": float(top),
        "bottom": float(bottom),
    }


def line_signature(line: dict[str, Any]) -> tuple[Any, ...]:
    return (
        collapse_whitespace(line.get("text", "")),
        round_coord(line.get("left")),
        round_coord(line.get("right")),
        round_coord(line.get("top")),
        round_coord(line.get("bottom")),
    )


def build_page_candidate_map(page: dict[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    candidate_map: dict[tuple[Any, ...], dict[str, Any]] = {}

    for candidate in page.get("header_footer_candidate_lines", []) or []:
        candidate_map[line_signature(candidate)] = candidate

    return candidate_map


def page_table_regions(page: dict[str, Any]) -> list[dict[str, float]]:
    page_number = page.get("page_number")
    regions: list[dict[str, float]] = []

    for table in page.get("tables", []) or []:
        regions.extend(extract_region_bounds(table.get("boundingRegions"), page_number))

    return regions


def bounds_inside_table(
    bounds: dict[str, Any] | None,
    table_regions: list[dict[str, float]],
) -> bool:
    return any(is_center_inside_bounds(bounds, region) for region in table_regions)


def paragraph_page_numbers(paragraph: dict[str, Any]) -> list[Any]:
    page_numbers = [
        region.get("pageNumber")
        for region in paragraph.get("boundingRegions", []) or []
        if region.get("pageNumber") is not None
    ]
    return ordered_unique(page_numbers)


def build_paragraph_index(
    document: dict[str, Any],
) -> tuple[dict[Any, list[dict[str, Any]]], dict[str, int]]:
    paragraphs_by_page: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    diagnostics = {
        "paragraph_total": 0,
        "paragraph_empty": 0,
        "paragraph_ambiguous_page": 0,
    }

    for paragraph_index, paragraph in enumerate(document.get("paragraphs", []) or []):
        diagnostics["paragraph_total"] += 1

        text = collapse_whitespace(paragraph.get("content", ""))
        if not text:
            diagnostics["paragraph_empty"] += 1
            continue

        page_numbers = paragraph_page_numbers(paragraph)
        if len(page_numbers) != 1:
            diagnostics["paragraph_ambiguous_page"] += 1
            continue

        page_number = page_numbers[0]
        paragraphs_by_page[page_number].append(
            {
                "paragraph_index": paragraph_index,
                "text": text,
                "role": paragraph.get("role"),
                "boundingRegions": paragraph.get("boundingRegions", []) or [],
                "spans": paragraph.get("spans", []) or [],
            }
        )

    return paragraphs_by_page, diagnostics


def extend_section_titles(existing_titles: list[str], new_title: str) -> list[str]:
    title = collapse_whitespace(new_title)
    if not title:
        return existing_titles
    if not is_meaningful_section_title(title):
        return existing_titles

    updated = [value for value in existing_titles if value != title]
    updated.append(title)
    return updated[-MAX_SECTION_TITLES:]


def is_text_heavy_unit(text: str) -> bool:
    token_count = len(text.split())
    return len(text) >= 180 or token_count >= 25


def looks_like_heading_text(text: str, line_count: int = 1) -> bool:
    text = collapse_whitespace(text)
    if not text:
        return False
    if not is_meaningful_section_title(text):
        return False

    token_count = len(text.split())
    if token_count == 0:
        return False
    if len(text) > 140 or token_count > 14:
        return False
    if text.endswith((".", "!", "?")):
        return False
    if line_count > 3:
        return False

    letters = [char for char in text if char.isalpha()]
    uppercase_ratio = 0.0
    if letters:
        uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)

    return token_count <= 8 or uppercase_ratio >= 0.55


def is_meaningful_section_title(text: str) -> bool:
    text = collapse_whitespace(text)
    if not text:
        return False
    if len(text) > 160:
        return False

    letters = sum(1 for char in text if char.isalpha())
    digits = sum(1 for char in text if char.isdigit())

    if letters == 0:
        return False
    if letters <= 1 and digits == 0 and len(text) <= 2:
        return False

    return True


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text)
    sentences = [collapse_whitespace(part) for part in parts if collapse_whitespace(part)]
    return sentences or [text]


def split_text_at_boundary(text: str, max_chars: int) -> tuple[str, str]:
    text = collapse_whitespace(text)
    if len(text) <= max_chars:
        return text, ""

    min_cut = max(int(max_chars * 0.6), 200)
    candidate_markers = [". ", "; ", ": ", ", ", " "]

    cut_index = -1
    for marker in candidate_markers:
        cut_index = text.rfind(marker, min_cut, max_chars + 1)
        if cut_index != -1:
            cut_index += len(marker.strip())
            break

    if cut_index == -1:
        next_space = text.find(" ", max_chars)
        if next_space != -1 and next_space <= max_chars + 120:
            cut_index = next_space

    if cut_index == -1:
        cut_index = max_chars

    left = collapse_whitespace(text[:cut_index])
    right = collapse_whitespace(text[cut_index:])
    return left, right


def pack_text_fragments(
    fragments: list[str],
    *,
    max_chars: int,
    separator: str,
) -> list[str]:
    packed: list[str] = []
    current: list[str] = []

    for fragment in fragments:
        fragment = collapse_whitespace(fragment)
        if not fragment:
            continue

        if not current:
            current = [fragment]
            continue

        candidate = separator.join(current + [fragment])
        if len(candidate) <= max_chars:
            current.append(fragment)
            continue

        packed.append(separator.join(current))
        current = [fragment]

    if current:
        packed.append(separator.join(current))

    return packed


def split_text_conservatively(text: str, max_chars: int) -> list[str]:
    text = collapse_whitespace(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentences = split_sentences(text)
    if len(sentences) > 1:
        segments = pack_text_fragments(sentences, max_chars=max_chars, separator=" ")
    else:
        segments = [text]

    final_segments: list[str] = []
    for segment in segments:
        segment = collapse_whitespace(segment)
        while len(segment) > max_chars:
            left, right = split_text_at_boundary(segment, max_chars)
            if left:
                final_segments.append(left)
            if not right or right == segment:
                segment = ""
                break
            segment = right
        if segment:
            final_segments.append(segment)

    return final_segments


def expand_units_for_chunking(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded_units: list[dict[str, Any]] = []

    for unit in units:
        if unit["char_count"] <= MAX_TEXT_CHARS:
            expanded_units.append(unit)
            continue

        segments = split_text_conservatively(unit["text"], MAX_TEXT_CHARS)
        if len(segments) <= 1:
            expanded_units.append(unit)
            continue

        for segment_index, segment in enumerate(segments):
            expanded_unit = unit.copy()
            expanded_unit["text"] = segment
            expanded_unit["char_count"] = len(segment)
            expanded_unit["heading_candidate"] = (
                unit.get("heading_candidate") if segment_index == 0 else None
            )
            expanded_unit["paragraph_count"] = (
                unit.get("paragraph_count", 0) if segment_index == 0 else 0
            )
            expanded_units.append(expanded_unit)

    return expanded_units


def paragraph_is_usable_for_narrative(
    paragraph: dict[str, Any],
    page: dict[str, Any],
    table_regions: list[dict[str, float]],
    repeat_candidates: dict[str, dict[str, Any]],
) -> bool:
    role = paragraph.get("role")
    if role in EXCLUDED_PARAGRAPH_ROLES:
        return False

    bounds_list = extract_region_bounds(
        paragraph.get("boundingRegions"),
        page_number=page.get("page_number"),
    )
    if bounds_list and any(bounds_inside_table(bounds, table_regions) for bounds in bounds_list):
        return False

    normalized_text = normalize_repeat_key(paragraph.get("text", ""))
    if role not in {"title", "sectionHeading"} and normalized_text in repeat_candidates:
        candidate = repeat_candidates[normalized_text]
        if candidate.get("page_occurrence_count", 0) >= 5:
            return False

    return True


def build_paragraph_units_for_page(
    page: dict[str, Any],
    page_paragraphs: list[dict[str, Any]],
    table_regions: list[dict[str, float]],
    repeat_candidates: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    units: list[dict[str, Any]] = []
    current_section_titles: list[str] = []
    diagnostics = {
        "paragraph_units_kept": 0,
        "paragraph_units_skipped": 0,
    }

    for paragraph in page_paragraphs:
        if not paragraph_is_usable_for_narrative(
            paragraph=paragraph,
            page=page,
            table_regions=table_regions,
            repeat_candidates=repeat_candidates,
        ):
            diagnostics["paragraph_units_skipped"] += 1
            continue

        text = paragraph["text"]
        role = paragraph.get("role")
        heading_candidate = (
            text
            if role in {"title", "sectionHeading"} and is_meaningful_section_title(text)
            else None
        )

        if heading_candidate:
            current_section_titles = extend_section_titles(
                current_section_titles,
                heading_candidate,
            )

        units.append(
            {
                "text": text,
                "source_kind": "paragraph",
                "page_number": page.get("page_number"),
                "page_type": page.get("page_type"),
                "section_titles": current_section_titles.copy(),
                "heading_candidate": heading_candidate,
                "paragraph_count": 1,
                "char_count": len(text),
            }
        )
        diagnostics["paragraph_units_kept"] += 1

    return units, diagnostics


def page_paragraphs_are_usable(page: dict[str, Any], units: list[dict[str, Any]]) -> bool:
    if not units:
        return False

    total_chars = sum(unit["char_count"] for unit in units)
    long_units = sum(1 for unit in units if is_text_heavy_unit(unit["text"]))
    short_units = sum(1 for unit in units if unit["char_count"] <= 40)
    heading_units = sum(1 for unit in units if unit.get("heading_candidate"))
    avg_chars = total_chars / max(len(units), 1)

    if page.get("page_type") in VISUAL_PAGE_TYPES and total_chars < 200:
        return False
    if len(units) >= 20 and avg_chars < 35 and short_units / len(units) >= 0.6:
        return False
    if len(units) >= 12 and avg_chars < 50 and long_units == 0 and heading_units >= len(units) * 0.35:
        return False

    if any(unit["char_count"] >= 450 for unit in units):
        return True
    if total_chars >= 350 and len(units) >= 2 and avg_chars >= 45:
        return True
    if long_units >= 2:
        return True
    if total_chars >= 600 and len(units) <= 10:
        return True

    return False


def candidate_line_should_be_excluded(
    line: dict[str, Any],
    candidate: dict[str, Any],
    non_candidate_line_count: int,
) -> bool:
    if non_candidate_line_count < 3:
        return False

    text = collapse_whitespace(line.get("text", ""))
    token_count = len(text.split())
    if token_count == 0:
        return False

    if candidate.get("page_occurrence_count", 0) < 5:
        return False

    return token_count <= 12 and len(text) <= 120


def line_break_threshold(page: dict[str, Any]) -> float:
    page_height = page.get("height")
    page_unit = page.get("unit")

    if isinstance(page_height, (int, float)) and page_height > 0:
        relative_threshold = float(page_height) * 0.018
    else:
        relative_threshold = 0.25

    if isinstance(page_unit, str) and page_unit.lower() == "inch":
        return max(0.18, min(0.35, relative_threshold))

    return max(0.18, relative_threshold)


def build_line_group_text(lines: list[dict[str, Any]]) -> str:
    return "\n".join(
        collapse_whitespace(line.get("text", ""))
        for line in lines
        if collapse_whitespace(line.get("text", ""))
    )


def should_start_new_line_group(
    previous_line: dict[str, Any],
    current_line: dict[str, Any],
    page: dict[str, Any],
    current_group: list[dict[str, Any]],
) -> bool:
    previous_bounds = line_bounds(previous_line)
    current_bounds = line_bounds(current_line)

    if previous_bounds is None or current_bounds is None:
        return looks_like_heading_text(collapse_whitespace(current_line.get("text", "")))

    gap = current_bounds["top"] - previous_bounds["bottom"]
    if gap > line_break_threshold(page):
        return True

    current_text = collapse_whitespace(current_line.get("text", ""))
    current_group_text = build_line_group_text(current_group)
    if current_group_text and len(current_group_text) >= 60 and looks_like_heading_text(current_text):
        return True

    return False


def build_line_units_for_page(
    page: dict[str, Any],
    table_regions: list[dict[str, float]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    candidate_map = build_page_candidate_map(page)
    non_candidate_line_count = sum(
        1
        for line in page.get("clean_lines", []) or []
        if line_signature(line) not in candidate_map
    )

    filtered_lines: list[dict[str, Any]] = []
    diagnostics = {
        "line_total": 0,
        "line_skipped_table": 0,
        "line_skipped_candidate": 0,
        "line_units_built": 0,
    }

    for line in page.get("clean_lines", []) or []:
        diagnostics["line_total"] += 1

        if bounds_inside_table(line_bounds(line), table_regions):
            diagnostics["line_skipped_table"] += 1
            continue

        candidate = candidate_map.get(line_signature(line))
        if candidate and candidate_line_should_be_excluded(
            line=line,
            candidate=candidate,
            non_candidate_line_count=non_candidate_line_count,
        ):
            diagnostics["line_skipped_candidate"] += 1
            continue

        filtered_lines.append(line)

    units: list[dict[str, Any]] = []
    if not filtered_lines:
        return units, diagnostics

    grouped_lines: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = []

    for line in filtered_lines:
        if current_group and should_start_new_line_group(
            previous_line=current_group[-1],
            current_line=line,
            page=page,
            current_group=current_group,
        ):
            grouped_lines.append(current_group)
            current_group = []

        current_group.append(line)

    if current_group:
        grouped_lines.append(current_group)

    current_section_titles: list[str] = []
    for group in grouped_lines:
        text = build_line_group_text(group)
        if not text:
            continue

        line_count = len(group)
        heading_candidate = text if looks_like_heading_text(text, line_count=line_count) else None
        if heading_candidate:
            current_section_titles = extend_section_titles(
                current_section_titles,
                heading_candidate,
            )

        units.append(
            {
                "text": text,
                "source_kind": "clean_lines",
                "page_number": page.get("page_number"),
                "page_type": page.get("page_type"),
                "section_titles": current_section_titles.copy(),
                "heading_candidate": heading_candidate,
                "paragraph_count": 0,
                "char_count": len(text),
            }
        )

    diagnostics["line_units_built"] = len(units)
    return units, diagnostics


def text_chunk_type_for_page(page: dict[str, Any]) -> str:
    if page.get("page_type") in VISUAL_PAGE_TYPES:
        return "visual"
    return "text"


def count_non_empty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def join_units_text(units: list[dict[str, Any]]) -> str:
    return "\n\n".join(unit["text"] for unit in units if unit.get("text"))


def build_base_chunk(
    *,
    chunk_id: str,
    chunk_index: int,
    source_file: str | None,
    model_id: str | None,
    chunk_type: str,
    page_numbers: list[Any],
    page_types: list[str],
    section_titles: list[str],
    text: str,
    table_count: int,
    paragraph_count: int,
    header_footer_candidates_present: bool,
    content_source: str,
    table_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "source_file": source_file,
        "model_id": model_id,
        "chunk_type": chunk_type,
        "content_source": content_source,
        "page_start": page_numbers[0] if page_numbers else None,
        "page_end": page_numbers[-1] if page_numbers else None,
        "page_numbers": page_numbers,
        "page_types": page_types,
        "section_titles": section_titles,
        "text": text,
        "char_count": len(text),
        "line_count": count_non_empty_lines(text),
        "table_count": table_count,
        "paragraph_count": paragraph_count,
        "header_footer_candidates_present": header_footer_candidates_present,
        "table_metadata": table_metadata,
    }


def is_small_text_chunk(chunk: dict[str, Any]) -> bool:
    if chunk.get("chunk_type") not in {"text", "visual"}:
        return False
    if chunk.get("char_count", 0) > SMALL_CHUNK_MERGE_CHARS:
        return False

    return (
        chunk.get("char_count", 0) <= TINY_CHUNK_MERGE_CHARS
        or chunk.get("line_count", 0) <= 3
        or chunk.get("paragraph_count", 0) <= 1
    )


def can_merge_adjacent_text_chunks(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("chunk_type") != right.get("chunk_type"):
        return False
    if left.get("chunk_type") not in {"text", "visual"}:
        return False
    if left.get("page_numbers") != right.get("page_numbers"):
        return False
    if left.get("content_source") != right.get("content_source"):
        return False

    combined_length = len(left.get("text", "")) + 2 + len(right.get("text", ""))
    return combined_length <= MAX_TEXT_CHARS


def merge_chunk_records(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged_text = f"{left.get('text', '')}\n\n{right.get('text', '')}".strip()
    merged_section_titles = ordered_unique(
        (left.get("section_titles") or []) + (right.get("section_titles") or [])
    )[-MAX_SECTION_TITLES:]

    return {
        **left,
        "section_titles": merged_section_titles,
        "text": merged_text,
        "char_count": len(merged_text),
        "line_count": count_non_empty_lines(merged_text),
        "paragraph_count": left.get("paragraph_count", 0) + right.get("paragraph_count", 0),
        "header_footer_candidates_present": bool(
            left.get("header_footer_candidates_present")
            or right.get("header_footer_candidates_present")
        ),
    }


def merge_small_text_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not chunks:
        return []

    merged_chunks: list[dict[str, Any]] = []
    index = 0

    while index < len(chunks):
        current = chunks[index]
        next_chunk = chunks[index + 1] if index + 1 < len(chunks) else None

        # Prefer attaching a tiny leading fragment to the next chunk on the same page.
        if (
            next_chunk is not None
            and is_small_text_chunk(current)
            and can_merge_adjacent_text_chunks(current, next_chunk)
        ):
            merged_chunks.append(merge_chunk_records(current, next_chunk))
            index += 2
            continue

        # Otherwise absorb a trailing small fragment into the previous chunk when safe.
        if (
            merged_chunks
            and is_small_text_chunk(current)
            and can_merge_adjacent_text_chunks(merged_chunks[-1], current)
        ):
            merged_chunks[-1] = merge_chunk_records(merged_chunks[-1], current)
            index += 1
            continue

        merged_chunks.append(current)
        index += 1

    return merged_chunks


def build_text_chunks_for_page(
    *,
    page: dict[str, Any],
    units: list[dict[str, Any]],
    source_file: str | None,
    model_id: str | None,
    document_slug: str,
    chunk_index_start: int,
) -> tuple[list[dict[str, Any]], int]:
    if not units:
        return [], chunk_index_start

    units = expand_units_for_chunking(units)
    chunks: list[dict[str, Any]] = []
    current_units: list[dict[str, Any]] = []
    current_chars = 0
    chunk_index = chunk_index_start
    chunk_type = text_chunk_type_for_page(page)

    def emit_chunk(units_to_emit: list[dict[str, Any]], next_chunk_index: int) -> dict[str, Any]:
        text = join_units_text(units_to_emit)
        section_titles = ordered_unique(
            [
                title
                for unit in units_to_emit
                for title in unit.get("section_titles", [])
                if collapse_whitespace(title)
            ]
        )[-MAX_SECTION_TITLES:]
        chunk_id = (
            f"{document_slug}__c{next_chunk_index:04d}"
            f"__{chunk_type}__p{page.get('page_number')}"
        )
        return build_base_chunk(
            chunk_id=chunk_id,
            chunk_index=next_chunk_index,
            source_file=source_file,
            model_id=model_id,
            chunk_type=chunk_type,
            page_numbers=[page.get("page_number")],
            page_types=[page.get("page_type")],
            section_titles=section_titles,
            text=text,
            table_count=0,
            paragraph_count=sum(unit.get("paragraph_count", 0) for unit in units_to_emit),
            header_footer_candidates_present=bool(page.get("header_footer_candidate_lines")),
            content_source=units_to_emit[0].get("source_kind", "unknown"),
        )

    for unit in units:
        unit_chars = unit["char_count"]
        heading_candidate = unit.get("heading_candidate")

        if current_units and heading_candidate and current_chars >= 180:
            chunks.append(emit_chunk(current_units, chunk_index))
            chunk_index += 1
            current_units = []
            current_chars = 0

        if current_units and current_chars >= 450 and current_chars + unit_chars > SOFT_MAX_TEXT_CHARS:
            chunks.append(emit_chunk(current_units, chunk_index))
            chunk_index += 1
            current_units = []
            current_chars = 0

        if current_units and current_chars >= MIN_TEXT_CHARS and current_chars + unit_chars > MAX_TEXT_CHARS:
            chunks.append(emit_chunk(current_units, chunk_index))
            chunk_index += 1
            current_units = []
            current_chars = 0

        current_units.append(unit)
        current_chars = len(join_units_text(current_units))

        if current_chars >= TARGET_TEXT_CHARS:
            chunks.append(emit_chunk(current_units, chunk_index))
            chunk_index += 1
            current_units = []
            current_chars = 0

    if current_units:
        if (
            chunks
            and len(join_units_text(current_units)) < 250
            and current_units[0].get("page_type") not in VISUAL_PAGE_TYPES
            and len(chunks[-1]["text"]) + 2 + len(join_units_text(current_units)) <= MAX_TEXT_CHARS
        ):
            previous_text = chunks[-1]["text"]
            trailing_text = join_units_text(current_units)
            merged_text = f"{previous_text}\n\n{trailing_text}".strip()
            chunks[-1]["text"] = merged_text
            chunks[-1]["char_count"] = len(merged_text)
            chunks[-1]["line_count"] = count_non_empty_lines(merged_text)
            chunks[-1]["paragraph_count"] += sum(
                unit.get("paragraph_count", 0) for unit in current_units
            )
            trailing_titles = [
                title
                for unit in current_units
                for title in unit.get("section_titles", [])
                if collapse_whitespace(title)
            ]
            chunks[-1]["section_titles"] = ordered_unique(
                chunks[-1]["section_titles"] + trailing_titles
            )[-MAX_SECTION_TITLES:]
        else:
            chunks.append(emit_chunk(current_units, chunk_index))
            chunk_index += 1

    chunks = merge_small_text_chunks(chunks)

    reindexed_chunks: list[dict[str, Any]] = []
    next_chunk_index = chunk_index_start

    for chunk in chunks:
        chunk_type_value = chunk.get("chunk_type", chunk_type)
        page_label = page.get("page_number")
        chunk["chunk_index"] = next_chunk_index
        chunk["chunk_id"] = (
            f"{document_slug}__c{next_chunk_index:04d}"
            f"__{chunk_type_value}__p{page_label}"
        )
        reindexed_chunks.append(chunk)
        next_chunk_index += 1

    return reindexed_chunks, next_chunk_index


def int_or_zero(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def table_signature(table: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "rowCount": table.get("rowCount"),
            "columnCount": table.get("columnCount"),
            "cells": table.get("cells", []),
            "boundingRegions": table.get("boundingRegions", []),
            "spans": table.get("spans", []),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_table_grid(table: dict[str, Any]) -> tuple[list[list[str]], dict[int, set[str]]]:
    row_count = max(int_or_zero(table.get("rowCount")), 0)
    column_count = max(int_or_zero(table.get("columnCount")), 0)
    grid = [["" for _ in range(column_count)] for _ in range(row_count)]
    row_kinds: dict[int, set[str]] = defaultdict(set)

    cells = sorted(
        table.get("cells", []) or [],
        key=lambda cell: (
            int_or_zero(cell.get("rowIndex")),
            int_or_zero(cell.get("columnIndex")),
        ),
    )

    for cell in cells:
        row_index = int_or_zero(cell.get("rowIndex"))
        column_index = int_or_zero(cell.get("columnIndex"))
        if row_index >= row_count or column_index >= column_count:
            continue

        content = collapse_whitespace(cell.get("content", ""))
        if content:
            existing = grid[row_index][column_index]
            if existing and content != existing:
                grid[row_index][column_index] = f"{existing} / {content}"
            else:
                grid[row_index][column_index] = content

        kind = collapse_whitespace(cell.get("kind", ""))
        if kind:
            row_kinds[row_index].add(kind)

    return grid, row_kinds


def format_table_row(row_index: int, row_cells: list[str], row_kinds: set[str]) -> str:
    rendered_cells = [
        f"C{column_index + 1}={cell}"
        for column_index, cell in enumerate(row_cells)
        if collapse_whitespace(cell)
    ]

    kind_suffix = ""
    if row_kinds:
        kind_suffix = f" [{', '.join(sorted(row_kinds))}]"

    if not rendered_cells:
        return f"Row {row_index + 1}{kind_suffix}: [empty]"

    return f"Row {row_index + 1}{kind_suffix}: " + " | ".join(rendered_cells)


def render_table(table: dict[str, Any]) -> tuple[list[str], list[tuple[int, str]]]:
    row_count = max(int_or_zero(table.get("rowCount")), 0)
    column_count = max(int_or_zero(table.get("columnCount")), 0)
    grid, row_kinds = build_table_grid(table)

    summary_lines = [
        f"Table with {row_count} rows and {column_count} columns.",
        f"Cell count: {len(table.get('cells', []) or [])}.",
    ]

    row_lines = [
        (row_index, format_table_row(row_index, row_cells, row_kinds.get(row_index, set())))
        for row_index, row_cells in enumerate(grid)
    ]

    return summary_lines, row_lines


def build_table_chunks(
    *,
    table: dict[str, Any],
    table_index: int,
    page_numbers: list[Any],
    page_types: list[str],
    page_heading_context: list[str],
    pages_with_candidates: set[Any],
    source_file: str | None,
    model_id: str | None,
    document_slug: str,
    chunk_index_start: int,
) -> tuple[list[dict[str, Any]], int]:
    chunk_index = chunk_index_start
    summary_lines, row_lines = render_table(table)
    row_count = max(int_or_zero(table.get("rowCount")), 0)
    column_count = max(int_or_zero(table.get("columnCount")), 0)
    cell_count = len(table.get("cells", []) or [])

    chunks: list[dict[str, Any]] = []
    current_rows: list[tuple[int, str]] = []

    def emit_table_chunk(rows_to_emit: list[tuple[int, str]], next_chunk_index: int) -> dict[str, Any]:
        row_start = rows_to_emit[0][0] + 1 if rows_to_emit else None
        row_end = rows_to_emit[-1][0] + 1 if rows_to_emit else None

        text_parts = list(summary_lines)
        if rows_to_emit:
            text_parts.append(f"Included rows: {row_start} to {row_end}.")
            text_parts.extend(row_text for _, row_text in rows_to_emit)

        text = "\n".join(text_parts)
        page_label = page_numbers[0] if page_numbers else "unknown"
        chunk_id = (
            f"{document_slug}__c{next_chunk_index:04d}"
            f"__table__p{page_label}__t{table_index:03d}"
        )

        return build_base_chunk(
            chunk_id=chunk_id,
            chunk_index=next_chunk_index,
            source_file=source_file,
            model_id=model_id,
            chunk_type="table",
            page_numbers=page_numbers,
            page_types=page_types,
            section_titles=page_heading_context,
            text=text,
            table_count=1,
            paragraph_count=0,
            header_footer_candidates_present=any(
                page_number in pages_with_candidates for page_number in page_numbers
            ),
            content_source="tables",
            table_metadata={
                "table_index": table_index,
                "row_count": row_count,
                "column_count": column_count,
                "cell_count": cell_count,
                "row_start": row_start,
                "row_end": row_end,
            },
        )

    summary_char_count = len("\n".join(summary_lines)) + 1
    current_char_count = summary_char_count

    if not row_lines:
        chunks.append(emit_table_chunk([], chunk_index))
        return chunks, chunk_index + 1

    for row in row_lines:
        row_char_count = len(row[1]) + 1

        if current_rows and current_char_count + row_char_count > MAX_TABLE_CHARS:
            chunks.append(emit_table_chunk(current_rows, chunk_index))
            chunk_index += 1
            current_rows = []
            current_char_count = summary_char_count

        current_rows.append(row)
        current_char_count += row_char_count

    if current_rows:
        chunks.append(emit_table_chunk(current_rows, chunk_index))
        chunk_index += 1

    return chunks, chunk_index


def page_heading_context(units: list[dict[str, Any]]) -> list[str]:
    return ordered_unique(
        [
            unit["heading_candidate"]
            for unit in units
            if collapse_whitespace(unit.get("heading_candidate", ""))
        ]
    )[-MAX_SECTION_TITLES:]


def chunk_document(document: dict[str, Any]) -> dict[str, Any]:
    source_file = document.get("source_file")
    model_id = document.get("model_id")
    document_slug = slugify_filename(source_file or "document")

    pages = sorted(document.get("pages", []) or [], key=sort_key_for_page)
    page_map = {page.get("page_number"): page for page in pages}
    paragraph_index, paragraph_diagnostics = build_paragraph_index(document)
    repeat_candidates = {
        candidate.get("normalized_text"): candidate
        for candidate in document.get("detected_repeated_lines", {}).get("header_footer_candidates", []) or []
        if collapse_whitespace(candidate.get("normalized_text"))
    }

    chunks: list[dict[str, Any]] = []
    seen_tables: set[str] = set()
    chunk_index = 1
    pages_using_paragraphs = 0
    pages_using_line_fallback = 0
    pages_with_candidates = {
        page.get("page_number")
        for page in pages
        if page.get("header_footer_candidate_lines")
    }

    table_index = 1

    for page in pages:
        page_number = page.get("page_number")
        table_regions = page_table_regions(page)
        raw_page_paragraphs = paragraph_index.get(page_number, [])
        paragraph_units, _ = build_paragraph_units_for_page(
            page=page,
            page_paragraphs=raw_page_paragraphs,
            table_regions=table_regions,
            repeat_candidates=repeat_candidates,
        )

        if page_paragraphs_are_usable(page, paragraph_units):
            narrative_units = paragraph_units
            pages_using_paragraphs += 1
        else:
            narrative_units, _ = build_line_units_for_page(
                page=page,
                table_regions=table_regions,
            )
            pages_using_line_fallback += 1

        page_text_chunks, chunk_index = build_text_chunks_for_page(
            page=page,
            units=narrative_units,
            source_file=source_file,
            model_id=model_id,
            document_slug=document_slug,
            chunk_index_start=chunk_index,
        )
        chunks.extend(page_text_chunks)

        page_titles = page_heading_context(narrative_units)

        for table in page.get("tables", []) or []:
            signature = table_signature(table)
            if signature in seen_tables:
                continue

            seen_tables.add(signature)
            page_numbers = ordered_unique(
                [
                    region.get("pageNumber")
                    for region in table.get("boundingRegions", []) or []
                    if region.get("pageNumber") is not None
                ]
            )
            if not page_numbers:
                page_numbers = [page_number]

            page_types = ordered_unique(
                [
                    page_map.get(number, {}).get("page_type", page.get("page_type"))
                    for number in page_numbers
                ]
            )

            table_chunks, chunk_index = build_table_chunks(
                table=table,
                table_index=table_index,
                page_numbers=page_numbers,
                page_types=page_types,
                page_heading_context=page_titles,
                pages_with_candidates=pages_with_candidates,
                source_file=source_file,
                model_id=model_id,
                document_slug=document_slug,
                chunk_index_start=chunk_index,
            )
            chunks.extend(table_chunks)
            table_index += 1

    text_chunk_count = sum(1 for chunk in chunks if chunk["chunk_type"] == "text")
    table_chunk_count = sum(1 for chunk in chunks if chunk["chunk_type"] == "table")
    visual_chunk_count = sum(1 for chunk in chunks if chunk["chunk_type"] == "visual")

    return {
        "source_file": source_file,
        "model_id": model_id,
        "document_metadata": document.get("document_metadata", {}),
        "chunking_metadata": {
            "chunker_name": "conservative_chunker",
            "chunker_version": 1,
            "source_page_count": len(pages),
            "total_chunks": len(chunks),
            "text_chunk_count": text_chunk_count,
            "table_chunk_count": table_chunk_count,
            "visual_chunk_count": visual_chunk_count,
            "pages_using_paragraphs": pages_using_paragraphs,
            "pages_using_line_fallback": pages_using_line_fallback,
            "paragraph_total": paragraph_diagnostics["paragraph_total"],
            "paragraph_empty": paragraph_diagnostics["paragraph_empty"],
            "paragraph_ambiguous_page": paragraph_diagnostics["paragraph_ambiguous_page"],
            "repeated_header_footer_candidate_count": len(repeat_candidates),
        },
        "chunks": chunks,
    }


def main() -> int:
    try:
        ensure_directories()

        input_files = list_processed_json_files()
        if not input_files:
            logger.warning("No processed JSON files found in %s", INPUT_DIR.resolve())
            return 0

        successes = 0
        failures = 0

        for input_path in input_files:
            output_path = build_output_path(input_path)

            try:
                logger.info("Chunking %s", input_path.name)
                document = load_json(input_path)
                chunked_document = chunk_document(document)
                save_json(chunked_document, output_path)
                logger.info("Saved %s", output_path)
                successes += 1
            except Exception as exc:
                failures += 1
                logger.exception("Failed on %s: %s", input_path.name, exc)

        logger.info("Finished. Successes=%s Failures=%s", successes, failures)
        return 0 if failures == 0 else 1

    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
