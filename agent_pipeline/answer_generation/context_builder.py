from __future__ import annotations

from typing import Any

from agent_pipeline.retrieval.document_registry import company_name_for_document
from agent_pipeline.retrieval.qdrant_retriever import RetrievedChunk


def collapse_whitespace(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(str(text).replace("\u00a0", " ").split()).strip()


def truncate_text(text: Any, max_chars: int) -> str:
    text_value = str(text or "").strip()
    if len(text_value) <= max_chars:
        return text_value
    return text_value[:max_chars].rstrip() + "\n[TRUNCATED]"


def format_list(values: Any) -> str:
    if isinstance(values, list):
        return ", ".join(str(value) for value in values)
    if values is None:
        return ""
    return str(values)


def build_context(
    chunks: list[RetrievedChunk],
    *,
    max_context_characters: int,
    max_chunk_characters: int,
) -> str:
    sections: list[str] = []
    current_length = 0

    for chunk in chunks:
        payload = chunk.payload
        document_id = str(payload.get("document_id") or "")
        table_metadata = payload.get("table_metadata")

        metadata_lines = [
            f"[Evidence {chunk.rank}]",
            f"score: {chunk.score:.6f}",
            f"company: {company_name_for_document(document_id)}",
            f"document_id: {document_id}",
            f"source_file: {payload.get('source_file')}",
            f"page_numbers: {format_list(payload.get('page_numbers'))}",
            f"chunk_id: {payload.get('chunk_id')}",
            f"chunk_type: {payload.get('chunk_type')}",
            f"section_titles: {format_list(payload.get('section_titles'))}",
        ]
        if table_metadata:
            metadata_lines.append(f"table_metadata: {table_metadata}")

        metadata_lines.append("exact_text:")
        metadata_lines.append(truncate_text(payload.get("text"), max_chunk_characters))

        section = "\n".join(metadata_lines)
        if sections and current_length + len(section) > max_context_characters:
            break

        sections.append(section)
        current_length += len(section)

    return "\n\n---\n\n".join(sections)

