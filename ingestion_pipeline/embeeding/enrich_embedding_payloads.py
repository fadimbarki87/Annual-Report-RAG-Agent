from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CHUNKS_DIR = BASE_DIR.parent / "chunking" / "data" / "chunks"
EMBEDDINGS_DIR = BASE_DIR / "data" / "embeddings"
SUMMARY_PATH = EMBEDDINGS_DIR / "embedding_payload_enrichment_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, indent=2)


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


def build_table_metadata_index() -> dict[str, dict[str, Any] | None]:
    table_metadata_by_chunk_id: dict[str, dict[str, Any] | None] = {}

    for chunk_path in list_chunk_files():
        document = load_json(chunk_path)
        for chunk in document.get("chunks", []) or []:
            chunk_id = chunk.get("chunk_id")
            if not chunk_id:
                continue
            table_metadata_by_chunk_id[str(chunk_id)] = chunk.get("table_metadata")

    return table_metadata_by_chunk_id


def enrich_document_embeddings(
    manifest_path: Path,
    table_metadata_by_chunk_id: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    jsonl_path = manifest_path.parent / str(manifest["output_jsonl"])
    temp_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp")

    records_seen = 0
    records_changed = 0
    table_records_with_metadata = 0

    with jsonl_path.open("r", encoding="utf-8") as input_handle, temp_path.open(
        "w",
        encoding="utf-8",
    ) as output_handle:
        for line in input_handle:
            if not line.strip():
                continue

            record = json.loads(line)
            payload = record.setdefault("payload", {})
            chunk_id = str(record.get("id") or payload.get("chunk_id") or "")
            table_metadata = table_metadata_by_chunk_id.get(chunk_id)

            if "table_metadata" not in payload or payload.get("table_metadata") != table_metadata:
                payload["table_metadata"] = table_metadata
                records_changed += 1

            if table_metadata:
                table_records_with_metadata += 1

            records_seen += 1
            output_handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    temp_path.replace(jsonl_path)

    return {
        "document_id": manifest["document_id"],
        "embedding_jsonl": str(jsonl_path),
        "records_seen": records_seen,
        "records_changed": records_changed,
        "table_records_with_metadata": table_records_with_metadata,
    }


def main() -> int:
    table_metadata_by_chunk_id = build_table_metadata_index()
    manifests = sorted(EMBEDDINGS_DIR.glob("*/manifest.json"))
    documents = [
        enrich_document_embeddings(manifest_path, table_metadata_by_chunk_id)
        for manifest_path in manifests
    ]
    summary = {
        "documents_processed": len(documents),
        "records_seen": sum(item["records_seen"] for item in documents),
        "records_changed": sum(item["records_changed"] for item in documents),
        "table_records_with_metadata": sum(
            item["table_records_with_metadata"] for item in documents
        ),
        "documents": documents,
    }
    save_json(summary, SUMMARY_PATH)
    print(f"Saved embedding payload enrichment summary to {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
