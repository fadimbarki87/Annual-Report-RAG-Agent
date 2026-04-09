from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from agent_pipeline.retrieval.document_registry import (  # noqa: E402
    company_name_for_document,
    resolve_document_ids,
)
from agent_pipeline.retrieval.retrieval_service import retrieve_chunks  # noqa: E402


def collapse_whitespace(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(str(text).replace("\u00a0", " ").split()).strip()


def exact_preview(text: Any, max_chars: int) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."


def format_list(values: Any) -> str:
    if isinstance(values, list):
        return ", ".join(str(value) for value in values)
    if values is None:
        return ""
    return str(values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Retrieve evidence chunks from Qdrant. This does not generate final answers."
        )
    )
    parser.add_argument("query", help="Question or search query to embed and retrieve.")
    parser.add_argument(
        "--company",
        action="append",
        default=[],
        help=(
            "Optional company/document filter. Can be repeated, e.g. "
            "--company bmw --company volkswagen."
        ),
    )
    parser.add_argument(
        "--document-id",
        action="append",
        default=[],
        help="Optional direct document_id filter, e.g. bmw_2024.",
    )
    parser.add_argument(
        "--chunk-type",
        action="append",
        choices=("text", "table", "visual"),
        default=[],
        help="Optional chunk type filter. Can be repeated.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Maximum number of chunks to return.",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=None,
        help="Optional Qdrant similarity score threshold.",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=900,
        help="Maximum exact text characters to print per retrieved chunk.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        registry_document_ids = resolve_document_ids(args.company)
        direct_document_ids = [
            document_id.strip()
            for document_id in args.document_id
            if document_id and document_id.strip()
        ]
        document_ids = registry_document_ids + [
            document_id
            for document_id in direct_document_ids
            if document_id not in registry_document_ids
        ]

        results = retrieve_chunks(
            query=args.query,
            document_ids=document_ids,
            chunk_types=args.chunk_type,
            limit=args.limit,
            score_threshold=args.score_threshold,
        )
    except Exception as exc:
        print(f"Retrieval failed: {exc}", file=sys.stderr)
        return 1

    filter_label = ", ".join(document_ids) if document_ids else "all documents"
    chunk_type_label = ", ".join(args.chunk_type) if args.chunk_type else "all chunk types"

    print("Retrieval only. No final answer was generated.")
    print(f"Query: {args.query}")
    print(f"Document filter: {filter_label}")
    print(f"Chunk type filter: {chunk_type_label}")
    print(f"Results: {len(results)}")

    for result in results:
        payload = result.payload
        document_id = str(payload.get("document_id") or "")
        company_name = company_name_for_document(document_id)
        page_numbers = format_list(payload.get("page_numbers"))
        section_titles = format_list(payload.get("section_titles"))
        table_metadata = payload.get("table_metadata")

        print("\n" + "=" * 80)
        print(f"Rank: {result.rank}")
        print(f"Score: {result.score:.6f}")
        print(f"Company: {company_name}")
        print(f"Document ID: {document_id}")
        print(f"Source file: {payload.get('source_file')}")
        print(f"Chunk ID: {payload.get('chunk_id')}")
        print(f"Chunk type: {payload.get('chunk_type')}")
        print(f"Pages: {page_numbers}")
        if section_titles:
            print(f"Section titles: {section_titles}")
        if table_metadata:
            print(f"Table metadata: {table_metadata}")
        print("Exact text preview:")
        print(exact_preview(payload.get("text"), max(args.preview_chars, 100)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

