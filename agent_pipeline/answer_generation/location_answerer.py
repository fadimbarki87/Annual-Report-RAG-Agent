from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agent_pipeline.answer_generation.azure_chat_client import request_chat_completion
from agent_pipeline.answer_generation.settings import AnswerGenerationSettings
from agent_pipeline.retrieval.document_registry import company_name_for_document
from agent_pipeline.retrieval.qdrant_retriever import RetrievedChunk


LOCATION_PATTERNS = [
    re.compile(r"\bon which page\b", flags=re.I),
    re.compile(r"\bwhat page\b", flags=re.I),
    re.compile(r"\bwhich page\b", flags=re.I),
    re.compile(r"\bwhere (?:is|are|can i find|in the report)\b", flags=re.I),
    re.compile(r"\bshow (?:me )?the source\b", flags=re.I),
    re.compile(r"\bshow (?:me )?where\b", flags=re.I),
    re.compile(r"\bevidence[- ]location\b", flags=re.I),
]

LOCATION_STOPWORDS = {
    "a",
    "an",
    "and",
    "annual",
    "appears",
    "are",
    "can",
    "does",
    "evidence",
    "find",
    "for",
    "from",
    "in",
    "is",
    "it",
    "locate",
    "located",
    "location",
    "me",
    "of",
    "on",
    "page",
    "pages",
    "pdf",
    "report",
    "show",
    "source",
    "stated",
    "the",
    "this",
    "what",
    "where",
    "which",
}

INTENT_GROUPS = [
    {"outlook", "forecast", "guidance", "expectation", "expected"},
    {"dividend", "proposed", "proposal", "propose"},
    {"revenue", "sales"},
    {"margin", "ebit", "ebitda"},
    {"risk", "risks"},
]

OUTLOOK_GROUP = {"outlook", "forecast", "guidance", "expectation", "expected"}
OUTLOOK_ACTION_TERMS = ("expect", "forecast", "project", "anticipat", "predict")

LOCATION_SYSTEM_PROMPT = """You are a strict evidence-location answer writer for annual reports.

You will receive:
- the user's location question
- retrieved chunks with page numbers and exact text

Your job:
- identify the page or pages where the substantive statement/value actually appears
- prefer pages that contain the actual statement, exact quote, numeric value, or table row
- ignore table-of-contents pages, chapter listings, cover pages, or summary references unless they themselves contain the requested statement/value
- keep the page list as short as possible
- if the same information is repeated many times, prefer the clearest and most canonical page or pages
- for outlook or forecast questions, prefer the dedicated outlook/expected-developments section over KPI summaries or forecast-comparison tables when both are available
- only include multiple pages when they each add clearly substantive evidence
- never return more than 3 pages
- use only the retrieved chunks

If the retrieved chunks are not enough, return exactly:
PAGES: NONE

Otherwise return exactly:
PAGES: <comma-separated page numbers>

Examples:
PAGES: 229
PAGES: 33, 133
"""


@dataclass(frozen=True)
class LocationFeatures:
    overlap: int
    intent_bonus: float
    type_bonus: float
    vector_score: float

    @property
    def composite(self) -> float:
        return float(self.overlap) + self.intent_bonus + self.type_bonus + self.vector_score


def collapse_whitespace(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(str(text).replace("\u00a0", " ").split()).strip()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def is_evidence_location_question(question: str) -> bool:
    normalized = collapse_whitespace(question)
    return any(pattern.search(normalized) for pattern in LOCATION_PATTERNS)


def location_terms(question: str) -> list[str]:
    normalized = normalize_text(question)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return [
        token
        for token in normalized.split()
        if len(token) >= 3 and token not in LOCATION_STOPWORDS
    ]


def chunk_search_text(chunk: RetrievedChunk) -> str:
    payload = chunk.payload
    values: list[str] = [
        str(payload.get("text") or ""),
        " ".join(str(value) for value in payload.get("section_titles") or []),
        str(payload.get("chunk_type") or ""),
    ]
    table_metadata = payload.get("table_metadata")
    if isinstance(table_metadata, dict):
        values.append(" ".join(f"{key} {value}" for key, value in table_metadata.items()))
    return normalize_text(" ".join(values))


def chunk_title_text(chunk: RetrievedChunk) -> str:
    payload = chunk.payload
    return normalize_text(" ".join(str(value) for value in payload.get("section_titles") or []))


def overlap_count(question_terms: list[str], chunk: RetrievedChunk) -> int:
    if not question_terms:
        return 0
    haystack = chunk_search_text(chunk)
    return sum(1 for term in question_terms if term in haystack)


def intent_bonus(question_terms: list[str], chunk: RetrievedChunk) -> float:
    if not question_terms:
        return 0.0

    haystack = chunk_search_text(chunk)
    title_text = chunk_title_text(chunk)
    bonus = 0.0

    for group in INTENT_GROUPS:
        group_terms = [term for term in question_terms if term in group]
        if not group_terms:
            continue
        if any(term in title_text for term in group_terms):
            bonus += 2.5
            continue
        if any(term in haystack for term in group_terms):
            bonus += 1.0

    return bonus


def active_focus_terms(question_terms: list[str]) -> set[str]:
    active: set[str] = set()
    for group in INTENT_GROUPS:
        if any(term in group for term in question_terms):
            active.update(term for term in question_terms if term in group)
    return active


def has_focus_terms(chunk: RetrievedChunk, focus_terms: set[str]) -> bool:
    if not focus_terms:
        return True
    haystack = chunk_search_text(chunk)
    title_text = chunk_title_text(chunk)
    return any(term in title_text or term in haystack for term in focus_terms)


def is_outlook_like_question(question_terms: list[str]) -> bool:
    return any(term in OUTLOOK_GROUP for term in question_terms)


def is_substantive_outlook_chunk(chunk: RetrievedChunk, question_terms: list[str]) -> bool:
    haystack = chunk_search_text(chunk)
    title_text = chunk_title_text(chunk)
    has_outlook_signal = any(term in title_text or term in haystack for term in OUTLOOK_GROUP)
    has_action_signal = any(term in haystack for term in OUTLOOK_ACTION_TERMS)
    sentence_like = len(collapse_whitespace(chunk.payload.get("text")).split()) >= 25

    metric_terms = [
        term
        for term in question_terms
        if term not in OUTLOOK_GROUP and term not in LOCATION_STOPWORDS
    ]
    metric_match = not metric_terms or any(term in haystack for term in metric_terms)

    return has_outlook_signal and has_action_signal and sentence_like and metric_match


def primary_page(chunk: RetrievedChunk) -> int | str | None:
    payload = chunk.payload
    page_numbers = payload.get("page_numbers") or []
    if isinstance(page_numbers, list) and page_numbers:
        return page_numbers[0]
    return payload.get("page_start")


def page_sort_key(page: int | str | None) -> tuple[int, str]:
    if isinstance(page, int):
        return (0, f"{page:08d}")
    if page is None:
        return (2, "")
    return (1, str(page))


def extract_features(question: str, chunk: RetrievedChunk) -> LocationFeatures:
    question_terms = location_terms(question)
    chunk_type = str(chunk.payload.get("chunk_type") or "")
    type_bonus = 0.25 if chunk_type == "text" else 0.15 if chunk_type == "table" else 0.0
    return LocationFeatures(
        overlap=overlap_count(question_terms, chunk),
        intent_bonus=intent_bonus(question_terms, chunk),
        type_bonus=type_bonus,
        vector_score=chunk.score,
    )


def rerank_location_chunks(question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    def sort_key(chunk: RetrievedChunk) -> tuple[float, float, float, float]:
        features = extract_features(question, chunk)
        return (
            features.composite,
            float(features.overlap),
            features.intent_bonus,
            chunk.score,
        )

    reranked = sorted(chunks, key=sort_key, reverse=True)
    return reranked


def select_location_chunks(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    max_pages: int = 3,
) -> list[RetrievedChunk]:
    reranked = rerank_location_chunks(question, chunks)
    if not reranked:
        return []

    scored = [(chunk, extract_features(question, chunk)) for chunk in reranked]
    question_terms = location_terms(question)
    skip_generic_focus = False
    if is_outlook_like_question(question_terms):
        outlook_focused = [
            (chunk, features)
            for chunk, features in scored
            if is_substantive_outlook_chunk(chunk, question_terms)
        ]
        if outlook_focused:
            text_only = [
                (chunk, features)
                for chunk, features in outlook_focused
                if str(chunk.payload.get("chunk_type") or "") == "text"
            ]
            scored = text_only or outlook_focused
            skip_generic_focus = True

    focus_terms = active_focus_terms(question_terms)
    if focus_terms and not skip_generic_focus:
        focused = [
            (chunk, features)
            for chunk, features in scored
            if has_focus_terms(chunk, focus_terms)
        ]
        if focused:
            scored = focused
    best_composite = max(features.composite for _, features in scored)
    selected: list[RetrievedChunk] = []
    seen_pages: set[tuple[str, str]] = set()

    for chunk, features in scored:
        if features.composite < best_composite * 0.6:
            continue
        page = primary_page(chunk)
        if page is None:
            continue
        document_id = str(chunk.payload.get("document_id") or "")
        page_key = (document_id, str(page))
        if page_key in seen_pages:
            continue
        selected.append(chunk)
        seen_pages.add(page_key)
        if len(selected) >= max_pages:
            break

    return sorted(selected, key=lambda chunk: page_sort_key(primary_page(chunk)))


def truncate_evidence_text(text: Any, max_chars: int = 900) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."


def relevant_excerpt(
    text: Any,
    question_terms: list[str],
    *,
    max_chars: int = 900,
) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned

    normalized = cleaned.casefold()
    best_index = -1
    best_term_length = -1
    for term in question_terms:
        index = normalized.find(term.casefold())
        if index == -1:
            continue
        if len(term) > best_term_length or (len(term) == best_term_length and index < best_index):
            best_index = index
            best_term_length = len(term)

    if best_index == -1:
        return truncate_evidence_text(cleaned, max_chars=max_chars)

    window_half = max_chars // 2
    start = max(best_index - window_half, 0)
    end = min(start + max_chars, len(cleaned))
    start = max(end - max_chars, 0)
    excerpt = cleaned[start:end].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(cleaned):
        excerpt = excerpt + "..."
    return excerpt


def extract_location_target(question: str) -> str:
    cleaned = collapse_whitespace(question).rstrip("?").strip()

    replacements = [
        r"^on which page is\s+",
        r"^what page is\s+",
        r"^which page is\s+",
        r"^on which page does\s+",
        r"^what page does\s+",
        r"^show (?:me )?the source of\s+",
        r"^show (?:me )?where\s+",
        r"^where is\s+",
        r"^where are\s+",
        r"^where in the report is\s+",
        r"^where in the report are\s+",
    ]
    for pattern in replacements:
        cleaned = re.sub(pattern, "", cleaned, flags=re.I)

    cleaned = re.sub(
        r"\s+(?:stated|mentioned|shown|discussed|found|located)\s*$",
        "",
        cleaned,
        flags=re.I,
    )
    return cleaned.strip() or "this request"


def format_pages(chunks: list[RetrievedChunk]) -> str:
    labels = [str(primary_page(chunk)) for chunk in chunks if primary_page(chunk) is not None]
    if not labels:
        return ""
    if len(labels) == 1:
        return f"page {labels[0]}"
    if len(labels) == 2:
        return f"pages {labels[0]} and {labels[1]}"
    return "pages " + ", ".join(labels[:-1]) + f", and {labels[-1]}"


def build_location_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    target = extract_location_target(question)
    page_phrase = format_pages(chunks)
    question_terms = location_terms(question)

    resources: list[str] = []
    evidence_lines: list[str] = []
    for chunk in chunks:
        payload = chunk.payload
        page = primary_page(chunk)
        resources.append(
            f"- {company_name_for_document(str(payload.get('document_id') or ''))}, "
            f"{payload.get('source_file')}, page {page}"
        )
        evidence_lines.append(
            f'- Page {page}: "{relevant_excerpt(payload.get("text"), question_terms)}"'
        )

    return "\n".join(
        [
            "Answer",
            f"The strongest evidence for {target} appears on {page_phrase}.",
            "",
            "Resources",
            *resources,
            "",
            "Evidence",
            *evidence_lines,
        ]
    ).strip()


def build_location_context(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    max_chunk_characters: int = 1200,
) -> str:
    question_terms = location_terms(question)
    sections: list[str] = [f"Question:\n{question}", "", "Retrieved location candidates:"]

    for index, chunk in enumerate(chunks, start=1):
        payload = chunk.payload
        page = primary_page(chunk)
        sections.extend(
            [
                "",
                f"[Candidate {index}]",
                f"score: {chunk.score:.6f}",
                f"company: {company_name_for_document(str(payload.get('document_id') or ''))}",
                f"source_file: {payload.get('source_file')}",
                f"page: {page}",
                f"chunk_type: {payload.get('chunk_type')}",
                f"section_titles: {payload.get('section_titles') or []}",
                "exact_text:",
                relevant_excerpt(
                    payload.get("text"),
                    question_terms,
                    max_chars=max_chunk_characters,
                ),
            ]
        )

    return "\n".join(sections).strip()


def parse_selected_pages(response: str) -> list[str]:
    match = re.search(r"PAGES\s*:\s*(.+)", response, flags=re.I)
    if not match:
        return []

    tail = match.group(1).strip()
    if tail.upper().startswith("NONE"):
        return []

    return [value for value in re.findall(r"\d+", tail) if value]


def answer_location_question(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    settings: AnswerGenerationSettings,
) -> str:
    location_chunks = select_location_chunks(question, chunks)
    if not location_chunks:
        return "No strong answer found in the provided documents."

    context = build_location_context(question, location_chunks)
    response = request_chat_completion(
        messages=[
            {"role": "system", "content": LOCATION_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        settings=settings,
        temperature=0.0,
        max_output_tokens=64,
    )
    selected_pages = parse_selected_pages(response)
    if not selected_pages:
        return "No strong answer found in the provided documents."

    selected_chunks: list[RetrievedChunk] = []
    seen_pages: set[str] = set()
    for page in selected_pages:
        for chunk in location_chunks:
            chunk_page = primary_page(chunk)
            if chunk_page is None or str(chunk_page) != page or page in seen_pages:
                continue
            selected_chunks.append(chunk)
            seen_pages.add(page)
            break

    if not selected_chunks:
        return "No strong answer found in the provided documents."

    return build_location_answer(question, selected_chunks)
