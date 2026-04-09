from __future__ import annotations

import math

from agent_pipeline.retrieval.azure_query_embedder import embed_query
from agent_pipeline.retrieval.document_registry import resolve_document_ids
from agent_pipeline.retrieval.qdrant_retriever import RetrievedChunk, search_chunks
from agent_pipeline.retrieval.settings import (
    AzureEmbeddingSettings,
    QdrantSettings,
    load_azure_embedding_settings,
    load_qdrant_settings,
)


def reindex_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            rank=index,
            score=chunk.score,
            point_id=chunk.point_id,
            payload=chunk.payload,
        )
        for index, chunk in enumerate(chunks, start=1)
    ]


def interleave_document_results(
    results_by_document: dict[str, list[RetrievedChunk]],
    *,
    limit: int,
) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    seen_point_ids: set[str] = set()
    ordered_document_ids = list(results_by_document)
    index_by_document = {document_id: 0 for document_id in ordered_document_ids}

    while len(selected) < limit:
        added_any = False
        for document_id in ordered_document_ids:
            document_results = results_by_document[document_id]
            current_index = index_by_document[document_id]
            while current_index < len(document_results):
                candidate = document_results[current_index]
                current_index += 1
                if candidate.point_id in seen_point_ids:
                    continue
                selected.append(candidate)
                seen_point_ids.add(candidate.point_id)
                added_any = True
                break
            index_by_document[document_id] = current_index
            if len(selected) >= limit:
                break
        if not added_any:
            break

    return reindex_chunks(selected)


def retrieve_chunks(
    *,
    query: str,
    company_filters: list[str] | None = None,
    document_ids: list[str] | None = None,
    chunk_types: list[str] | None = None,
    limit: int = 8,
    score_threshold: float | None = None,
    balance_across_documents: bool = False,
    azure_settings: AzureEmbeddingSettings | None = None,
    qdrant_settings: QdrantSettings | None = None,
) -> list[RetrievedChunk]:
    resolved_document_ids = document_ids or resolve_document_ids(company_filters)

    azure_settings = azure_settings or load_azure_embedding_settings()
    qdrant_settings = qdrant_settings or load_qdrant_settings()

    query_vector = embed_query(query, settings=azure_settings)
    if balance_across_documents and len(resolved_document_ids) > 1:
        per_document_limit = max(
            8,
            min(16, int(math.ceil(limit / len(resolved_document_ids))) + 4),
        )
        results_by_document = {
            document_id: search_chunks(
                query_vector=query_vector,
                document_ids=[document_id],
                chunk_types=chunk_types,
                limit=per_document_limit,
                score_threshold=score_threshold,
                settings=qdrant_settings,
            )
            for document_id in resolved_document_ids
        }
        return interleave_document_results(results_by_document, limit=limit)

    return search_chunks(
        query_vector=query_vector,
        document_ids=resolved_document_ids,
        chunk_types=chunk_types,
        limit=limit,
        score_threshold=score_threshold,
        settings=qdrant_settings,
    )
