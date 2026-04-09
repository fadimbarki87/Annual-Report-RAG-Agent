from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

from agent_pipeline.retrieval.settings import QdrantSettings, load_qdrant_settings


MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 2

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    rank: int
    score: float
    point_id: str
    payload: dict[str, Any]


def qdrant_headers(settings: QdrantSettings) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["api-key"] = settings.api_key
    return headers


def qdrant_url(
    settings: QdrantSettings,
    path: str,
    query: dict[str, Any] | None = None,
) -> str:
    encoded_path = "/".join(
        parse.quote(part, safe="") for part in path.strip("/").split("/")
    )
    url = f"{settings.qdrant_url}/{encoded_path}"
    if query:
        url += "?" + parse.urlencode(query)
    return url


def qdrant_request(
    *,
    settings: QdrantSettings,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    data = None if body is None else json.dumps(body).encode("utf-8")
    url = qdrant_url(settings, path, query=query)

    for attempt in range(1, MAX_RETRIES + 1):
        req = request.Request(
            url=url,
            data=data,
            headers=qdrant_headers(settings),
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
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Qdrant retrieval request failed with HTTP {exc.code}: "
                    f"{response_body}"
                ) from exc
            logger.warning(
                "Qdrant retrieval request failed on attempt %s/%s with HTTP %s. "
                "Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                exc.code,
                RETRY_SLEEP_SECONDS,
            )
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            logger.warning(
                "Qdrant retrieval request failed on attempt %s/%s. Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                RETRY_SLEEP_SECONDS,
            )

        time.sleep(RETRY_SLEEP_SECONDS * attempt)

    raise RuntimeError("Qdrant retrieval request failed unexpectedly.")


def match_condition(key: str, values: list[str]) -> dict[str, Any] | None:
    clean_values = [value for value in values if value]
    if not clean_values:
        return None
    if len(clean_values) == 1:
        return {"key": key, "match": {"value": clean_values[0]}}
    return {"key": key, "match": {"any": clean_values}}


def build_filter(
    *,
    document_ids: list[str] | None = None,
    chunk_types: list[str] | None = None,
) -> dict[str, Any] | None:
    must: list[dict[str, Any]] = []

    document_filter = match_condition("document_id", document_ids or [])
    if document_filter is not None:
        must.append(document_filter)

    chunk_type_filter = match_condition("chunk_type", chunk_types or [])
    if chunk_type_filter is not None:
        must.append(chunk_type_filter)

    if not must:
        return None
    return {"must": must}


def parse_search_result(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not result:
        return []

    payload = result.get("result")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("points"), list):
        return payload["points"]
    return []


def search_chunks(
    *,
    query_vector: list[float],
    document_ids: list[str] | None = None,
    chunk_types: list[str] | None = None,
    limit: int = 8,
    score_threshold: float | None = None,
    settings: QdrantSettings | None = None,
) -> list[RetrievedChunk]:
    if not query_vector:
        raise ValueError("Query vector cannot be empty.")

    settings = settings or load_qdrant_settings()
    body: dict[str, Any] = {
        "vector": query_vector,
        "limit": max(int(limit), 1),
        "with_payload": True,
        "with_vector": False,
    }

    filter_body = build_filter(document_ids=document_ids, chunk_types=chunk_types)
    if filter_body is not None:
        body["filter"] = filter_body
    if score_threshold is not None:
        body["score_threshold"] = float(score_threshold)

    result = qdrant_request(
        settings=settings,
        method="POST",
        path=f"/collections/{settings.collection_name}/points/search",
        body=body,
    )

    points = parse_search_result(result)
    return [
        RetrievedChunk(
            rank=index,
            score=float(point.get("score", 0.0)),
            point_id=str(point.get("id", "")),
            payload=point.get("payload") or {},
        )
        for index, point in enumerate(points, start=1)
    ]

