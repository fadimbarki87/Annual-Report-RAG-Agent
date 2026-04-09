from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR.parent / "chunking" / "data" / "chunks"
OUTPUT_DIR = BASE_DIR / "data" / "embeddings"
CONFIG_PATH = BASE_DIR / "azure_openai_config.json"
TEMPLATE_CONFIG_PATH = BASE_DIR / "azure_openai_config.template.json"

DEFAULT_API_VERSION = "2024-02-01"
DEFAULT_BATCH_SIZE = 16
DEFAULT_MAX_BATCH_CHARACTERS = 20000
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def list_chunk_files() -> list[Path]:
    if not INPUT_DIR.exists():
        return []

    return sorted(
        path
        for path in INPUT_DIR.iterdir()
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
    return " ".join(str(text).replace("\u00a0", " ").split()).strip()


def load_config() -> dict[str, Any]:
    config: dict[str, Any] = {}

    if CONFIG_PATH.exists():
        config = load_json(CONFIG_PATH)

    endpoint = str(config.get("endpoint") or os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip()
    api_key = str(config.get("api_key") or os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
    deployment = str(
        config.get("embedding_deployment")
        or os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or ""
    ).strip()
    api_version = str(
        config.get("api_version")
        or os.environ.get("AZURE_OPENAI_API_VERSION")
        or DEFAULT_API_VERSION
    ).strip()
    batch_size = int(config.get("batch_size") or DEFAULT_BATCH_SIZE)
    max_batch_characters = int(
        config.get("max_batch_characters") or DEFAULT_MAX_BATCH_CHARACTERS
    )

    return {
        "endpoint": endpoint.rstrip("/"),
        "api_key": api_key,
        "embedding_deployment": deployment,
        "api_version": api_version,
        "batch_size": max(batch_size, 1),
        "max_batch_characters": max(max_batch_characters, 1000),
    }


def validate_config(config: dict[str, Any]) -> None:
    missing = [
        name
        for name in ("endpoint", "api_key", "embedding_deployment")
        if not collapse_whitespace(config.get(name))
    ]
    if not missing:
        return

    raise ValueError(
        "Missing Azure OpenAI configuration values: "
        + ", ".join(missing)
        + f". Set them in {CONFIG_PATH} or via environment variables."
    )


def build_embedding_url(config: dict[str, Any]) -> str:
    endpoint = config["endpoint"]
    deployment = parse.quote(config["embedding_deployment"], safe="")
    api_version = parse.quote(config["api_version"], safe="")
    return (
        f"{endpoint}/openai/deployments/{deployment}/embeddings"
        f"?api-version={api_version}"
    )


def request_embeddings(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    if not texts:
        return []

    url = build_embedding_url(config)
    payload = json.dumps({"input": texts}).encode("utf-8")

    for attempt in range(1, MAX_RETRIES + 1):
        req = request.Request(
            url=url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "api-key": config["api_key"],
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=120) as response:
                body = response.read().decode("utf-8")
            result = json.loads(body)
            data = result.get("data", []) or []
            ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
            vectors = [item.get("embedding", []) for item in ordered]
            if len(vectors) != len(texts):
                raise ValueError(
                    f"Expected {len(texts)} embeddings but received {len(vectors)}."
                )
            return vectors
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Azure OpenAI embeddings request failed with HTTP {exc.code}: "
                    f"{response_body}"
                ) from exc
            logger.warning(
                "Embedding request failed on attempt %s/%s with HTTP %s. Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                exc.code,
                RETRY_SLEEP_SECONDS,
            )
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            logger.warning(
                "Embedding request failed on attempt %s/%s. Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                RETRY_SLEEP_SECONDS,
            )

        time.sleep(RETRY_SLEEP_SECONDS * attempt)

    raise RuntimeError("Embedding request failed unexpectedly.")


def build_document_slug(path: Path) -> str:
    return path.stem.removesuffix("_chunks")


def prepare_records(document: dict[str, Any], document_slug: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for chunk in document.get("chunks", []) or []:
        text = str(chunk.get("text") or "")
        if not collapse_whitespace(text):
            continue

        records.append(
            {
                "id": chunk.get("chunk_id"),
                "text": text,
                "payload": {
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
                },
            }
        )

    return records


def build_batches(
    records: list[dict[str, Any]],
    *,
    batch_size: int,
    max_batch_characters: int,
) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_chars = 0

    for record in records:
        text_length = len(record["text"])

        should_flush = False
        if current_batch and len(current_batch) >= batch_size:
            should_flush = True
        if current_batch and current_chars + text_length > max_batch_characters:
            should_flush = True

        if should_flush:
            batches.append(current_batch)
            current_batch = []
            current_chars = 0

        current_batch.append(record)
        current_chars += text_length

    if current_batch:
        batches.append(current_batch)

    return batches


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file_handle:
        for record in records:
            file_handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def embed_document(chunk_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    document_slug = build_document_slug(chunk_path)
    document = load_json(chunk_path)
    records = prepare_records(document, document_slug)
    batches = build_batches(
        records,
        batch_size=config["batch_size"],
        max_batch_characters=config["max_batch_characters"],
    )

    logger.info(
        "Embedding %s with %s chunks in %s batches",
        chunk_path.name,
        len(records),
        len(batches),
    )

    embedded_records: list[dict[str, Any]] = []
    vector_dimension = None

    for batch_index, batch in enumerate(batches, start=1):
        texts = [item["text"] for item in batch]
        embeddings = request_embeddings(texts, config)
        for item, embedding in zip(batch, embeddings, strict=True):
            if vector_dimension is None:
                vector_dimension = len(embedding)

            embedded_records.append(
                {
                    "id": item["id"],
                    "vector": embedding,
                    "payload": {
                        **item["payload"],
                        "text": item["text"],
                    },
                }
            )

        logger.info(
            "Embedded %s batch %s/%s",
            document_slug,
            batch_index,
            len(batches),
        )

    output_dir = OUTPUT_DIR / document_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    vectors_path = output_dir / f"{document_slug}_embeddings.jsonl"
    manifest_path = output_dir / "manifest.json"

    write_jsonl(embedded_records, vectors_path)
    save_json(
        {
            "document_id": document_slug,
            "source_chunk_file": chunk_path.name,
            "source_file": document.get("source_file"),
            "chunk_count_embedded": len(embedded_records),
            "vector_dimension": vector_dimension,
            "embedding_provider": "azure_openai",
            "embedding_deployment": config["embedding_deployment"],
            "api_version": config["api_version"],
            "output_jsonl": vectors_path.name,
        },
        manifest_path,
    )

    return {
        "document_id": document_slug,
        "chunk_count_embedded": len(embedded_records),
        "vector_dimension": vector_dimension,
        "output_dir": str(output_dir),
    }


def main() -> int:
    ensure_directories()
    chunk_files = list_chunk_files()
    if not chunk_files:
        logger.warning("No chunk JSON files found in %s", INPUT_DIR)
        return 0

    try:
        config = load_config()
        validate_config(config)
    except Exception as exc:
        logger.error("%s", exc)
        logger.error("You can copy %s to %s and fill in your Azure values.", TEMPLATE_CONFIG_PATH, CONFIG_PATH)
        return 1

    successes = 0
    failures = 0
    for chunk_path in chunk_files:
        try:
            result = embed_document(chunk_path, config)
            logger.info(
                "Saved embeddings for %s to %s",
                result["document_id"],
                result["output_dir"],
            )
            successes += 1
        except Exception as exc:
            logger.exception("Failed embedding %s: %s", chunk_path.name, exc)
            failures += 1

    logger.info("Finished embedding. Successes=%s Failures=%s", successes, failures)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
