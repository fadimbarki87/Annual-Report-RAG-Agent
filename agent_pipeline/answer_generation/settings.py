from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import parse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = Path(__file__).resolve().parent

ANSWER_CONFIG_PATH = BASE_DIR / "answer_generation_config.json"
ANSWER_TEMPLATE_CONFIG_PATH = BASE_DIR / "answer_generation_config.template.json"
AZURE_EMBEDDING_CONFIG_PATH = (
    PROJECT_ROOT / "ingestion_pipeline" / "embeeding" / "azure_openai_config.json"
)

DEFAULT_API_VERSION = "2024-02-01"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_OUTPUT_TOKENS = 1200
DEFAULT_RETRIEVAL_LIMIT = 12
DEFAULT_MINIMUM_TOP_SCORE = 0.45
DEFAULT_MAX_CONTEXT_CHARACTERS = 24000
DEFAULT_MAX_CHUNK_CHARACTERS = 2500


@dataclass(frozen=True)
class AnswerGenerationSettings:
    endpoint: str
    api_key: str
    chat_deployment: str
    api_version: str
    temperature: float
    max_output_tokens: int
    retrieval_limit: int
    minimum_top_score: float
    max_context_characters: int
    max_chunk_characters: int


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().upper()
    return not normalized or "YOUR_" in normalized or normalized.startswith("YOUR-")


def normalize_azure_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip().rstrip("/")
    if not endpoint:
        return ""

    parsed = parse.urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        return endpoint

    return f"{parsed.scheme}://{parsed.netloc}"


def load_answer_generation_settings() -> AnswerGenerationSettings:
    answer_config = load_json(ANSWER_CONFIG_PATH)
    embedding_config = load_json(AZURE_EMBEDDING_CONFIG_PATH)

    endpoint = str(
        answer_config.get("endpoint")
        or os.environ.get("AZURE_OPENAI_ENDPOINT")
        or embedding_config.get("endpoint")
        or ""
    ).strip()
    api_key = str(
        answer_config.get("api_key")
        or os.environ.get("AZURE_OPENAI_API_KEY")
        or embedding_config.get("api_key")
        or ""
    ).strip()
    chat_deployment = str(
        answer_config.get("chat_deployment")
        or os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT")
        or ""
    ).strip()
    api_version = str(
        answer_config.get("api_version")
        or os.environ.get("AZURE_OPENAI_CHAT_API_VERSION")
        or embedding_config.get("api_version")
        or DEFAULT_API_VERSION
    ).strip()

    missing = [
        name
        for name, value in (
            ("endpoint", endpoint),
            ("api_key", api_key),
            ("chat_deployment", chat_deployment),
        )
        if looks_like_placeholder(value)
    ]
    if missing:
        raise ValueError(
            "Missing answer-generation configuration values: "
            + ", ".join(missing)
            + f". Copy {ANSWER_TEMPLATE_CONFIG_PATH} to {ANSWER_CONFIG_PATH} "
            "and set your Azure OpenAI chat deployment."
        )
    endpoint = normalize_azure_endpoint(endpoint)

    return AnswerGenerationSettings(
        endpoint=endpoint.rstrip("/"),
        api_key=api_key,
        chat_deployment=chat_deployment,
        api_version=api_version,
        temperature=float(answer_config.get("temperature", DEFAULT_TEMPERATURE)),
        max_output_tokens=max(
            int(answer_config.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS)),
            1,
        ),
        retrieval_limit=max(
            int(answer_config.get("retrieval_limit", DEFAULT_RETRIEVAL_LIMIT)),
            1,
        ),
        minimum_top_score=float(
            answer_config.get("minimum_top_score", DEFAULT_MINIMUM_TOP_SCORE)
        ),
        max_context_characters=max(
            int(
                answer_config.get(
                    "max_context_characters",
                    DEFAULT_MAX_CONTEXT_CHARACTERS,
                )
            ),
            1000,
        ),
        max_chunk_characters=max(
            int(answer_config.get("max_chunk_characters", DEFAULT_MAX_CHUNK_CHARACTERS)),
            500,
        ),
    )
