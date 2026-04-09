from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CHUNKS_DIR = BASE_DIR.parent / "chunking" / "data" / "chunks"
EMBEDDINGS_DIR = BASE_DIR / "data" / "embeddings"
OUTPUT_PATH = EMBEDDINGS_DIR / "embedding_quality_evaluation.json"

PAYLOAD_METADATA_KEYS = (
    "document_id",
    "chunk_id",
    "chunk_index",
    "source_file",
    "model_id",
    "chunk_type",
    "content_source",
    "page_start",
    "page_end",
    "page_numbers",
    "page_types",
    "section_titles",
    "char_count",
    "line_count",
    "table_count",
    "table_metadata",
    "paragraph_count",
    "header_footer_candidates_present",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, indent=2)


def collapse_whitespace(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(str(text).replace("\u00a0", " ").split()).strip()


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 1.0
    return float(numerator) / float(denominator)


def round_metric(value: Any, digits: int = 6) -> Any:
    if isinstance(value, float):
        return round(value, digits)
    return value


def round_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: round_metric(value) for key, value in metrics.items()}


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return 0.0 if values else None
    avg = sum(values) / len(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def build_document_slug(chunk_path: Path) -> str:
    return chunk_path.stem.removesuffix("_chunks")


def list_chunk_files() -> list[Path]:
    if not CHUNKS_DIR.exists():
        return []
    return sorted(
        path
        for path in CHUNKS_DIR.iterdir()
        if path.is_file()
        and path.name.endswith("_chunks.json")
        and "evaluation" not in path.stem.casefold()
    )


def expected_chunk_payloads(chunk_path: Path) -> dict[str, dict[str, Any]]:
    document_slug = build_document_slug(chunk_path)
    document = load_json(chunk_path)
    expected: dict[str, dict[str, Any]] = {}

    for chunk in document.get("chunks", []) or []:
        text = str(chunk.get("text") or "")
        if not collapse_whitespace(text):
            continue

        chunk_id = chunk.get("chunk_id")
        if not chunk_id:
            continue

        expected[str(chunk_id)] = {
            "document_id": document_slug,
            "chunk_id": chunk.get("chunk_id"),
            "chunk_index": chunk.get("chunk_index"),
            "source_file": chunk.get("source_file"),
            "model_id": chunk.get("model_id"),
            "chunk_type": chunk.get("chunk_type"),
            "content_source": chunk.get("content_source"),
            "page_start": chunk.get("page_start"),
            "page_end": chunk.get("page_end"),
            "page_numbers": chunk.get("page_numbers"),
            "page_types": chunk.get("page_types"),
            "section_titles": chunk.get("section_titles"),
            "char_count": chunk.get("char_count"),
            "line_count": chunk.get("line_count"),
            "table_count": chunk.get("table_count"),
            "table_metadata": chunk.get("table_metadata"),
            "paragraph_count": chunk.get("paragraph_count"),
            "header_footer_candidates_present": chunk.get(
                "header_footer_candidates_present"
            ),
            "text": text,
        }

    return expected


def vector_norm(vector: list[Any]) -> tuple[float, bool]:
    total = 0.0
    all_finite = True

    for value in vector:
        if not isinstance(value, (int, float)):
            all_finite = False
            continue
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            all_finite = False
            continue
        total += numeric_value * numeric_value

    return math.sqrt(total), all_finite


def evaluate_document(chunk_path: Path) -> dict[str, Any]:
    document_slug = build_document_slug(chunk_path)
    embedding_dir = EMBEDDINGS_DIR / document_slug
    manifest_path = embedding_dir / "manifest.json"

    expected_payloads = expected_chunk_payloads(chunk_path)
    expected_ids = set(expected_payloads)

    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    output_jsonl = manifest.get("output_jsonl") or f"{document_slug}_embeddings.jsonl"
    jsonl_path = embedding_dir / str(output_jsonl)

    record_ids: list[str] = []
    seen_ids: set[str] = set()
    duplicate_id_count = 0
    matched_id_count = 0
    id_payload_match_count = 0
    text_exact_match_count = 0
    payload_metadata_match_count = 0
    required_payload_field_present_count = 0
    required_payload_field_total_count = 0
    nonempty_vector_count = 0
    finite_vector_count = 0
    nonzero_vector_count = 0
    dimension_match_count = 0
    table_record_count = 0
    table_records_with_metadata = 0
    vector_dimensions: Counter[int] = Counter()
    vector_norms: list[float] = []

    manifest_dimension = manifest.get("vector_dimension")
    if isinstance(manifest_dimension, bool) or not isinstance(manifest_dimension, int):
        manifest_dimension = None

    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as file_handle:
            for line in file_handle:
                if not line.strip():
                    continue

                record = json.loads(line)
                record_id = str(record.get("id") or "")
                payload = record.get("payload") or {}
                vector = record.get("vector") or []

                record_ids.append(record_id)
                if record_id in seen_ids:
                    duplicate_id_count += 1
                seen_ids.add(record_id)

                if record_id in expected_ids:
                    matched_id_count += 1

                if record_id and record_id == str(payload.get("chunk_id") or ""):
                    id_payload_match_count += 1

                expected = expected_payloads.get(record_id)
                if expected is not None and payload.get("text") == expected.get("text"):
                    text_exact_match_count += 1

                if payload.get("chunk_type") == "table":
                    table_record_count += 1
                    if payload.get("table_metadata"):
                        table_records_with_metadata += 1

                if expected is not None:
                    metadata_matches = all(
                        payload.get(key) == expected.get(key)
                        for key in PAYLOAD_METADATA_KEYS
                    )
                    if metadata_matches:
                        payload_metadata_match_count += 1

                for key in PAYLOAD_METADATA_KEYS:
                    required_payload_field_total_count += 1
                    if key in payload:
                        required_payload_field_present_count += 1

                if isinstance(vector, list) and vector:
                    nonempty_vector_count += 1

                dimension = len(vector) if isinstance(vector, list) else 0
                vector_dimensions[dimension] += 1
                if manifest_dimension is not None and dimension == manifest_dimension:
                    dimension_match_count += 1

                norm, all_finite = vector_norm(vector if isinstance(vector, list) else [])
                vector_norms.append(norm)
                if all_finite and dimension > 0:
                    finite_vector_count += 1
                if norm > 0:
                    nonzero_vector_count += 1

    record_count = len(record_ids)
    unique_record_ids = set(record_ids)
    missing_ids = expected_ids - unique_record_ids
    extra_ids = unique_record_ids - expected_ids
    expected_count = len(expected_ids)

    metrics = {
        "source_chunk_count": expected_count,
        "embedded_record_count": record_count,
        "unique_embedded_id_count": len(unique_record_ids),
        "manifest_chunk_count_embedded": manifest.get("chunk_count_embedded"),
        "manifest_count_matches_jsonl_rate": safe_rate(
            int(manifest.get("chunk_count_embedded") == record_count),
            1,
        ),
        "embedding_coverage_rate": safe_rate(len(expected_ids & unique_record_ids), expected_count),
        "missing_embedding_count": len(missing_ids),
        "extra_embedding_count": len(extra_ids),
        "duplicate_embedding_id_count": duplicate_id_count,
        "id_payload_match_rate": safe_rate(id_payload_match_count, record_count),
        "payload_text_exact_match_rate": safe_rate(text_exact_match_count, record_count),
        "payload_metadata_match_rate": safe_rate(payload_metadata_match_count, record_count),
        "table_record_count": table_record_count,
        "table_records_with_metadata": table_records_with_metadata,
        "table_metadata_presence_rate": safe_rate(
            table_records_with_metadata,
            table_record_count,
        ),
        "required_payload_field_presence_rate": safe_rate(
            required_payload_field_present_count,
            required_payload_field_total_count,
        ),
        "nonempty_vector_rate": safe_rate(nonempty_vector_count, record_count),
        "finite_vector_rate": safe_rate(finite_vector_count, record_count),
        "nonzero_vector_rate": safe_rate(nonzero_vector_count, record_count),
        "vector_dimension": manifest_dimension,
        "vector_dimension_consistency_rate": safe_rate(dimension_match_count, record_count),
        "vector_norm_min": min(vector_norms) if vector_norms else None,
        "vector_norm_max": max(vector_norms) if vector_norms else None,
        "vector_norm_mean": mean(vector_norms),
        "vector_norm_std": stdev(vector_norms),
    }

    return {
        "document_id": document_slug,
        "metrics": round_metrics(metrics),
        "vector_dimensions_observed": {
            str(dimension): count for dimension, count in sorted(vector_dimensions.items())
        },
    }


def build_overall_metrics(documents: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "source_chunk_count": 0,
        "embedded_record_count": 0,
        "unique_embedded_id_count": 0,
        "missing_embedding_count": 0,
        "extra_embedding_count": 0,
        "duplicate_embedding_id_count": 0,
        "table_record_count": 0,
        "table_records_with_metadata": 0,
    }
    weighted_rates = {
        "id_payload_match_rate": 0.0,
        "payload_text_exact_match_rate": 0.0,
        "payload_metadata_match_rate": 0.0,
        "required_payload_field_presence_rate": 0.0,
        "nonempty_vector_rate": 0.0,
        "finite_vector_rate": 0.0,
        "nonzero_vector_rate": 0.0,
        "vector_dimension_consistency_rate": 0.0,
    }
    weighted_rate_denominator = 0
    manifest_count_matches = 0
    vector_norm_means: list[float] = []
    vector_norm_mins: list[float] = []
    vector_norm_maxes: list[float] = []
    vector_dimensions: set[Any] = set()

    for document in documents:
        metrics = document["metrics"]
        record_count = int(metrics["embedded_record_count"])
        expected_count = int(metrics["source_chunk_count"])

        for key in totals:
            totals[key] += int(metrics[key])

        for key in weighted_rates:
            weighted_rates[key] += float(metrics[key]) * record_count
        weighted_rate_denominator += record_count

        manifest_count_matches += int(metrics["manifest_count_matches_jsonl_rate"] == 1.0)

        if metrics["vector_norm_mean"] is not None:
            vector_norm_means.append(float(metrics["vector_norm_mean"]))
        if metrics["vector_norm_min"] is not None:
            vector_norm_mins.append(float(metrics["vector_norm_min"]))
        if metrics["vector_norm_max"] is not None:
            vector_norm_maxes.append(float(metrics["vector_norm_max"]))
        if metrics["vector_dimension"] is not None:
            vector_dimensions.add(metrics["vector_dimension"])

    overall = {
        "document_count": len(documents),
        **totals,
        "manifest_count_matches_jsonl_rate": safe_rate(
            manifest_count_matches,
            len(documents),
        ),
        "table_metadata_presence_rate": safe_rate(
            totals["table_records_with_metadata"],
            totals["table_record_count"],
        ),
        "embedding_coverage_rate": safe_rate(
            totals["unique_embedded_id_count"] - totals["extra_embedding_count"],
            totals["source_chunk_count"],
        ),
        "vector_dimension": (
            next(iter(vector_dimensions)) if len(vector_dimensions) == 1 else None
        ),
        "vector_norm_min": min(vector_norm_mins) if vector_norm_mins else None,
        "vector_norm_max": max(vector_norm_maxes) if vector_norm_maxes else None,
        "vector_norm_mean_macro": mean(vector_norm_means),
    }

    for key, value in weighted_rates.items():
        overall[key] = safe_rate(value, weighted_rate_denominator)

    return round_metrics(overall)


def main() -> int:
    chunk_files = list_chunk_files()
    documents = [evaluate_document(chunk_path) for chunk_path in chunk_files]
    output = {
        "overall_metrics": build_overall_metrics(documents),
        "documents": documents,
    }
    save_json(output, OUTPUT_PATH)
    print(f"Saved embedding evaluation to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
