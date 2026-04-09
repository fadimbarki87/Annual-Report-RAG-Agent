from __future__ import annotations

import argparse
import sys
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from agent_pipeline.answer_generation.answer_generator import answer_question  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a grounded answer from retrieved annual-report chunks."
    )
    parser.add_argument("question", help="Question to answer from the annual reports.")
    parser.add_argument(
        "--company",
        action="append",
        default=[],
        help="Optional company filter. Can be repeated.",
    )
    parser.add_argument(
        "--chunk-type",
        action="append",
        choices=("text", "table", "visual"),
        default=[],
        help="Optional chunk type filter. Can be repeated.",
    )
    parser.add_argument(
        "--retrieval-limit",
        type=int,
        default=None,
        help="Override the number of retrieved chunks passed to answer generation.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        answer = answer_question(
            question=args.question,
            company_filters=args.company,
            chunk_types=args.chunk_type,
            retrieval_limit=args.retrieval_limit,
        )
    except Exception as exc:
        print(f"Answer generation failed: {exc}", file=sys.stderr)
        return 1

    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

