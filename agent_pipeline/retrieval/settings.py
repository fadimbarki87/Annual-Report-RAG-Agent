from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

AZURE_CONFIG_PATH = (
    PROJECT_ROOT / "ingestion_pipeline" / "embeeding" / "azure_openai_config.json"
)
QDRANT_CONFIG_PATH = (
    PROJECT_ROOT
    / "ingestion_pipeline"
    / "vector_storage"
    / "qdrant"
    / "qdrant_config.json"
)

DEFAULT_AZURE_API_VERSION = "2024-02-01"
DEFAULT_QDRANT_COLLECTION = "annual_report_chunks"


@dataclass(frozen=True)
class AzureEmbeddingSettings:
    endpoint: str
    api_key: str
    embedding_deployment: str
    api_version: str


@dataclass(frozen=True)
class QdrantSettings:
    qdrant_url: str
    api_key: str
    collection_name: str


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().upper()
    return not normalized or "YOUR_" in normalized or normalized.startswith("YOUR-")


def load_azure_embedding_settings() -> AzureEmbeddingSettings:
    config = load_json(AZURE_CONFIG_PATH)

    endpoint = str(
        config.get("endpoint") or os.environ.get("AZURE_OPENAI_ENDPOINT") or ""
    ).strip()
    api_key = str(
        config.get("api_key") or os.environ.get("AZURE_OPENAI_API_KEY") or ""
    ).strip()
    deployment = str(
        config.get("embedding_deployment")
        or os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or ""
    ).strip()
    api_version = str(
        config.get("api_version")
        or os.environ.get("AZURE_OPENAI_API_VERSION")
        or DEFAULT_AZURE_API_VERSION
    ).strip()

    missing = [
        name
        for name, value in (
            ("endpoint", endpoint),
            ("api_key", api_key),
            ("embedding_deployment", deployment),
        )
        if looks_like_placeholder(value)
    ]
    if missing:
        raise ValueError(
            "Missing Azure OpenAI retrieval configuration values: "
            + ", ".join(missing)
            + f". Set them in {AZURE_CONFIG_PATH} or environment variables."
        )

    if "/openai/" in endpoint:
        raise ValueError(
            "Azure OpenAI endpoint must be the base resource URL only, not a full "
            f"deployment URL. Check {AZURE_CONFIG_PATH}."
        )

    return AzureEmbeddingSettings(
        endpoint=endpoint.rstrip("/"),
        api_key=api_key,
        embedding_deployment=deployment,
        api_version=api_version,
    )


def load_qdrant_settings() -> QdrantSettings:
    config = load_json(QDRANT_CONFIG_PATH)

    qdrant_url = str(
        config.get("qdrant_url") or os.environ.get("QDRANT_URL") or ""
    ).strip()
    api_key = str(
        config.get("api_key") or os.environ.get("QDRANT_API_KEY") or ""
    ).strip()
    collection_name = str(
        config.get("collection_name")
        or os.environ.get("QDRANT_COLLECTION_NAME")
        or DEFAULT_QDRANT_COLLECTION
    ).strip()

    missing = [
        name
        for name, value in (
            ("qdrant_url", qdrant_url),
            ("collection_name", collection_name),
        )
        if looks_like_placeholder(value)
    ]
    if qdrant_url.startswith("https://") and looks_like_placeholder(api_key):
        missing.append("api_key")

    if missing:
        raise ValueError(
            "Missing Qdrant retrieval configuration values: "
            + ", ".join(sorted(set(missing)))
            + f". Set them in {QDRANT_CONFIG_PATH} or environment variables."
        )

    return QdrantSettings(
        qdrant_url=qdrant_url.rstrip("/"),
        api_key=api_key,
        collection_name=collection_name,
    )

