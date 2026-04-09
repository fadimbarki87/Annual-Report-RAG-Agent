from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import error, parse, request


BASE_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = BASE_DIR.parent.parent
EMBEDDINGS_DIR = PIPELINE_DIR / "embeeding" / "data" / "embeddings"
OUTPUT_DIR = BASE_DIR / "data"
CONFIG_PATH = BASE_DIR / "qdrant_config.json"
TEMPLATE_CONFIG_PATH = BASE_DIR / "qdrant_config.template.json"
SUMMARY_PATH = OUTPUT_DIR / "qdrant_upsert_summary.json"

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION_NAME = "annual_report_chunks"
DEFAULT_VECTOR_SIZE = 3072
DEFAULT_DISTANCE = "Cosine"
DEFAULT_BATCH_SIZE = 64
DEFAULT_PAYLOAD_INDEXES = {
    "document_id": "keyword",
    "source_file": "keyword",
    "chunk_type": "keyword",
    "content_source": "keyword",
    "chunk_index": "integer",
    "page_start": "integer",
    "page_end": "integer",
}
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 2

POINT_NAMESPACE = uuid.UUID("0a59b45a-32d7-49e8-8658-8cb05d71a9dc")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, indent=2)


def load_config() -> dict[str, Any]:
    config: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        config = load_json(CONFIG_PATH)

    return {
        "qdrant_url": str(
            config.get("qdrant_url")
            or os.environ.get("QDRANT_URL")
            or DEFAULT_QDRANT_URL
        ).rstrip("/"),
        "api_key": str(
            config.get("api_key")
            or os.environ.get("QDRANT_API_KEY")
            or ""
        ).strip(),
        "collection_name": str(
            config.get("collection_name")
            or os.environ.get("QDRANT_COLLECTION_NAME")
            or DEFAULT_COLLECTION_NAME
        ).strip(),
        "vector_size": int(config.get("vector_size") or DEFAULT_VECTOR_SIZE),
        "distance": str(config.get("distance") or DEFAULT_DISTANCE).strip(),
        "batch_size": max(int(config.get("batch_size") or DEFAULT_BATCH_SIZE), 1),
        "recreate_collection": bool(config.get("recreate_collection", False)),
        "on_disk_payload": bool(config.get("on_disk_payload", True)),
        "payload_indexes": config.get("payload_indexes") or DEFAULT_PAYLOAD_INDEXES,
    }


def validate_config(config: dict[str, Any]) -> None:
    qdrant_url = str(config.get("qdrant_url") or "").strip()
    api_key = str(config.get("api_key") or "").strip()
    collection_name = str(config.get("collection_name") or "").strip()
    distance = str(config.get("distance") or "").strip()

    missing = [
        name
        for name, value in (
            ("qdrant_url", qdrant_url),
            ("collection_name", collection_name),
            ("distance", distance),
        )
        if not value or "YOUR" in value.upper()
    ]
    if qdrant_url.startswith("https://") and not api_key:
        missing.append("api_key")
    if api_key and "YOUR" in api_key.upper():
        missing.append("api_key")

    if missing:
        raise ValueError(
            "Missing Qdrant configuration values: "
            + ", ".join(sorted(set(missing)))
            + f". Set them in {CONFIG_PATH} or via environment variables."
        )
    if config["vector_size"] <= 0:
        raise ValueError("Qdrant vector_size must be positive.")


def qdrant_headers(config: dict[str, Any]) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.get("api_key"):
        headers["api-key"] = config["api_key"]
    return headers


def qdrant_url(config: dict[str, Any], path: str, query: dict[str, Any] | None = None) -> str:
    base_url = config["qdrant_url"]
    encoded_path = "/".join(parse.quote(part, safe="") for part in path.strip("/").split("/"))
    url = f"{base_url}/{encoded_path}"
    if query:
        url += "?" + parse.urlencode(query)
    return url


def qdrant_request(
    *,
    config: dict[str, Any],
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    allow_404: bool = False,
) -> dict[str, Any] | None:
    data = None if body is None else json.dumps(body).encode("utf-8")
    url = qdrant_url(config, path, query=query)

    for attempt in range(1, MAX_RETRIES + 1):
        req = request.Request(
            url=url,
            data=data,
            headers=qdrant_headers(config),
            method=method,
        )

        try:
            with request.urlopen(req, timeout=120) as response:
                response_body = response.read().decode("utf-8")
            if not response_body:
                return None
            return json.loads(response_body)
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            if allow_404 and exc.code == 404:
                return None
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Qdrant request failed with HTTP {exc.code}: {response_body}"
                ) from exc
            logger.warning(
                "Qdrant request failed on attempt %s/%s with HTTP %s. Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                exc.code,
                RETRY_SLEEP_SECONDS,
            )
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            logger.warning(
                "Qdrant request failed on attempt %s/%s. Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                RETRY_SLEEP_SECONDS,
            )

        time.sleep(RETRY_SLEEP_SECONDS * attempt)

    raise RuntimeError("Qdrant request failed unexpectedly.")


def list_embedding_manifests() -> list[Path]:
    if not EMBEDDINGS_DIR.exists():
        return []
    return sorted(
        path
        for path in EMBEDDINGS_DIR.glob("*/manifest.json")
        if path.is_file()
    )


def stable_point_id(chunk_id: Any) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, str(chunk_id)))


def read_embedding_records(manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(manifest_path)
    jsonl_path = manifest_path.parent / str(manifest["output_jsonl"])
    records: list[dict[str, Any]] = []

    with jsonl_path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            if not line.strip():
                continue
            record = json.loads(line)
            payload = record.get("payload") or {}
            chunk_id = record.get("id") or payload.get("chunk_id")
            payload["qdrant_point_id"] = stable_point_id(chunk_id)
            records.append(
                {
                    "id": stable_point_id(chunk_id),
                    "vector": record["vector"],
                    "payload": payload,
                }
            )

    return manifest, records


def create_collection(config: dict[str, Any]) -> None:
    body = {
        "vectors": {
            "size": config["vector_size"],
            "distance": config["distance"],
        },
        "on_disk_payload": config["on_disk_payload"],
    }
    qdrant_request(
        config=config,
        method="PUT",
        path=f"/collections/{config['collection_name']}",
        body=body,
    )


def delete_collection(config: dict[str, Any]) -> None:
    qdrant_request(
        config=config,
        method="DELETE",
        path=f"/collections/{config['collection_name']}",
        allow_404=True,
    )


def ensure_collection(config: dict[str, Any]) -> None:
    if config["recreate_collection"]:
        logger.info("Recreating Qdrant collection %s", config["collection_name"])
        delete_collection(config)
        create_collection(config)
        return

    collection = qdrant_request(
        config=config,
        method="GET",
        path=f"/collections/{config['collection_name']}",
        allow_404=True,
    )
    if collection is None:
        logger.info("Creating Qdrant collection %s", config["collection_name"])
        create_collection(config)
        return

    logger.info("Using existing Qdrant collection %s", config["collection_name"])


def upsert_points(config: dict[str, Any], points: list[dict[str, Any]]) -> None:
    qdrant_request(
        config=config,
        method="PUT",
        path=f"/collections/{config['collection_name']}/points",
        query={"wait": "true"},
        body={"points": points},
    )


def get_collection_points_count(config: dict[str, Any]) -> int | None:
    collection = qdrant_request(
        config=config,
        method="GET",
        path=f"/collections/{config['collection_name']}",
    )
    if not collection:
        return None

    result = collection.get("result") or {}
    points_count = result.get("points_count")
    if isinstance(points_count, bool) or not isinstance(points_count, int):
        return None
    return points_count


def get_payload_schema(config: dict[str, Any]) -> dict[str, Any]:
    collection = qdrant_request(
        config=config,
        method="GET",
        path=f"/collections/{config['collection_name']}",
    )
    if not collection:
        return {}

    result = collection.get("result") or {}
    payload_schema = result.get("payload_schema") or {}
    return payload_schema if isinstance(payload_schema, dict) else {}


def ensure_payload_indexes(config: dict[str, Any]) -> None:
    payload_indexes = config.get("payload_indexes") or {}
    if not isinstance(payload_indexes, dict) or not payload_indexes:
        return

    existing_schema = get_payload_schema(config)

    for field_name, field_schema in payload_indexes.items():
        if field_name in existing_schema:
            logger.info("Qdrant payload index already exists for %s", field_name)
            continue

        logger.info("Creating Qdrant payload index for %s (%s)", field_name, field_schema)
        qdrant_request(
            config=config,
            method="PUT",
            path=f"/collections/{config['collection_name']}/index",
            query={"wait": "true"},
            body={
                "field_name": field_name,
                "field_schema": field_schema,
            },
        )


def main() -> int:
    ensure_directories()

    try:
        config = load_config()
        validate_config(config)
    except Exception as exc:
        logger.error("%s", exc)
        logger.error("You can copy %s to %s and adjust it.", TEMPLATE_CONFIG_PATH, CONFIG_PATH)
        return 1

    manifests = list_embedding_manifests()
    if not manifests:
        logger.warning("No embedding manifests found in %s", EMBEDDINGS_DIR)
        return 0

    try:
        ensure_collection(config)
        ensure_payload_indexes(config)
    except Exception as exc:
        logger.exception("Failed connecting to Qdrant: %s", exc)
        return 1

    total_points = 0
    documents: list[dict[str, Any]] = []

    for manifest_path in manifests:
        manifest, records = read_embedding_records(manifest_path)
        document_id = manifest["document_id"]
        logger.info("Upserting %s points for %s", len(records), document_id)

        for start in range(0, len(records), config["batch_size"]):
            batch = records[start : start + config["batch_size"]]
            upsert_points(config, batch)

        total_points += len(records)
        documents.append(
            {
                "document_id": document_id,
                "points_upserted": len(records),
                "source_embedding_file": str(manifest_path.parent / manifest["output_jsonl"]),
                "vector_dimension": manifest.get("vector_dimension"),
            }
        )

    collection_points_count = get_collection_points_count(config)
    summary = {
        "qdrant_url": config["qdrant_url"],
        "collection_name": config["collection_name"],
        "distance": config["distance"],
        "configured_vector_size": config["vector_size"],
        "documents_upserted": len(documents),
        "points_upserted": total_points,
        "collection_points_count_after_upsert": collection_points_count,
        "collection_count_matches_upserted_points": collection_points_count == total_points,
        "payload_indexes": config.get("payload_indexes") or {},
        "documents": documents,
    }
    save_json(summary, SUMMARY_PATH)
    logger.info("Saved Qdrant upsert summary to %s", SUMMARY_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
