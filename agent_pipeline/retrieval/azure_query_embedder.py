from __future__ import annotations

import json
import logging
import time
from urllib import error, parse, request

from agent_pipeline.retrieval.settings import (
    AzureEmbeddingSettings,
    load_azure_embedding_settings,
)


MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3

logger = logging.getLogger(__name__)


def build_embedding_url(settings: AzureEmbeddingSettings) -> str:
    deployment = parse.quote(settings.embedding_deployment, safe="")
    api_version = parse.quote(settings.api_version, safe="")
    return (
        f"{settings.endpoint}/openai/deployments/{deployment}/embeddings"
        f"?api-version={api_version}"
    )


def embed_query(
    query: str,
    settings: AzureEmbeddingSettings | None = None,
) -> list[float]:
    query = query.strip()
    if not query:
        raise ValueError("Query cannot be empty.")

    settings = settings or load_azure_embedding_settings()
    url = build_embedding_url(settings)
    payload = json.dumps({"input": [query]}).encode("utf-8")

    for attempt in range(1, MAX_RETRIES + 1):
        req = request.Request(
            url=url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "api-key": settings.api_key,
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=120) as response:
                body = response.read().decode("utf-8")
            result = json.loads(body)
            data = result.get("data", []) or []
            if len(data) != 1:
                raise ValueError(f"Expected 1 query embedding, received {len(data)}.")
            vector = data[0].get("embedding") or []
            if not vector:
                raise ValueError("Azure OpenAI returned an empty query embedding.")
            return vector
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Azure OpenAI query embedding failed with HTTP {exc.code}: "
                    f"{response_body}"
                ) from exc
            logger.warning(
                "Query embedding failed on attempt %s/%s with HTTP %s. Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                exc.code,
                RETRY_SLEEP_SECONDS,
            )
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            logger.warning(
                "Query embedding failed on attempt %s/%s. Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                RETRY_SLEEP_SECONDS,
            )

        time.sleep(RETRY_SLEEP_SECONDS * attempt)

    raise RuntimeError("Query embedding failed unexpectedly.")

