from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Callable

from agent_pipeline.retrieval.document_registry import (
    company_name_for_document,
)
from agent_pipeline.retrieval.qdrant_retriever import RetrievedChunk
from agent_pipeline.retrieval.retrieval_service import retrieve_chunks


REVENUE_KEYWORD_PATTERN = re.compile(
    r"\b(?:revenue|revenues|sales revenue|group revenues)\b",
    flags=re.I,
)
EMPLOYEE_KEYWORD_PATTERN = re.compile(
    r"\b(?:employee|employees|headcount|workforce)\b",
    flags=re.I,
)
DIVIDEND_KEYWORD_PATTERN = re.compile(
    r"\bdividend\b",
    flags=re.I,
)
FREE_CASH_FLOW_KEYWORD_PATTERN = re.compile(
    r"\b(?:free cash flow|net cash flow)\b",
    flags=re.I,
)
AGGREGATION_KEYWORD_PATTERN = re.compile(
    r"\b(?:total|combined|sum|together)\b",
    flags=re.I,
)
COMPARISON_KEYWORD_PATTERN = re.compile(
    r"\b(?:compare|comparison|versus|vs\.?)\b",
    flags=re.I,
)
RANKING_KEYWORD_PATTERN = re.compile(
    r"\b(?:rank|ranking|highest|lowest)\b",
    flags=re.I,
)
TABLE_HEADER_ROW_PATTERN = re.compile(
    r"Row\s+\d+\s+\[columnHeader\]:\s*(?P<row>[^\n]+)",
    flags=re.I,
)
TABLE_METRIC_ROW_PATTERN = re.compile(
    r"Row\s+\d+(?:\s+\[columnHeader\])?:\s*(?P<row>[^\n]+)",
    flags=re.I,
)
TEXT_REVENUE_PATTERN = re.compile(
    r"(?:sales revenue|revenue|group revenues?)"
    r"[^.\n]{0,120}?"
    r"(?:€|EUR)?\s*(?P<value>[0-9][0-9,]*\.?[0-9]*)\s*(?P<unit>billion|million)",
    flags=re.I,
)
VALUE_BEFORE_METRIC_PATTERN = re.compile(
    r"(?:€|EUR)?\s*(?P<value>[0-9][0-9,]*\.?[0-9]*)\s*(?P<unit>billion|million)"
    r"[^.\n]{0,80}?\brevenue\b",
    flags=re.I,
)
EMPLOYEE_VALUE_PATTERN = re.compile(
    r"(?P<value>[0-9][0-9,]*)\s+employees",
    flags=re.I,
)
DIVIDEND_VALUE_PATTERN = re.compile(
    r"(?:€|EUR)\s*(?P<value>[0-9]+(?:[.,][0-9]+)?)",
    flags=re.I,
)
TABLE_CELL_PATTERN = re.compile(
    r"(C\d+)=(.*?)(?=(?:\s+\|\s+C\d+=)|$)",
    flags=re.S,
)
SEGMENT_REVENUE_HINT_PATTERN = re.compile(
    r"\b(?:"
    r"digital industries|smart infrastructure|mobility|siemens healthineers|"
    r"passenger cars|commercial vehicles|power engineering|financial services|"
    r"americas|asia|australia|europe|china|germany|north america|south america|"
    r"thereof|taxonomy|non-controlling interests"
    r")\b",
    flags=re.I,
)
PREFERRED_REVENUE_ROW_PATTERNS: dict[str, tuple[str, ...]] = {
    "volkswagen_2024": (
        r"C1=Group sales revenue",
    ),
}
PREFERRED_REVENUE_TEXT_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "bosch_2024": (
        re.compile(
            r"Bosch Group sales revenue[^.\n]{0,160}?to\s+(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>billion|million)\s+euros",
            flags=re.I,
        ),
        re.compile(
            r"In the Bosch Group, we achieved sales revenue of\s+(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>billion|million)\s+euros",
            flags=re.I,
        ),
    ),
    "siemens_2024": (
        re.compile(
            r"Siemens'? revenue rose to\s+(?:€|â‚¬|EUR)?(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>billion|million)",
            flags=re.I,
        ),
    ),
    "volkswagen_2024": (
        re.compile(
            r"Volkswagen Group generated sales revenue of\s+(?:€|â‚¬|EUR)?(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>billion|million)",
            flags=re.I,
        ),
        re.compile(
            r"At\s+(?:€|â‚¬|EUR)?(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>billion|million), the Group's sales revenue",
            flags=re.I,
        ),
    ),
}


@dataclass(frozen=True)
class RevenueEvidence:
    document_id: str
    company: str
    source_file: str
    page_number: int | str | None
    value_million_eur: Decimal
    display_value: str
    evidence_text: str
    score: float


@dataclass(frozen=True)
class NumericMetricEvidence:
    document_id: str
    company: str
    source_file: str
    page_number: int | str | None
    sort_value: Decimal
    display_value: str
    evidence_text: str
    score: float


def collapse_whitespace(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\u00a0", " ").split()).strip()


def first_page_number(payload: dict[str, object]) -> int | str | None:
    page_numbers = payload.get("page_numbers")
    if isinstance(page_numbers, list) and page_numbers:
        first_value = page_numbers[0]
        if isinstance(first_value, int):
            return first_value
        if isinstance(first_value, str) and first_value.strip():
            return first_value.strip()
    page_start = payload.get("page_start")
    if isinstance(page_start, int):
        return page_start
    return None


def normalize_numeric_value(value: str) -> Decimal | None:
    cleaned = value.replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def format_decimal(value: Decimal) -> str:
    integer_value = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(integer_value):,}"


def revenue_query_for_document(document_id: str) -> str:
    if document_id in {"bosch_2024", "volkswagen_2024"}:
        return "2024 sales revenue"
    return "2024 revenue"


def format_display_value(value: Decimal, unit: str) -> str:
    normalized_unit = unit.casefold()
    if normalized_unit == "billion":
        billion_value = (value / Decimal("1000")).quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )
        return f"EUR {billion_value} billion"
    return f"EUR {format_decimal(value)} million"


def normalize_decimal_literal(value: str) -> Decimal | None:
    cleaned = collapse_whitespace(value)
    cleaned = cleaned.replace("€", "").replace("EUR", "").replace(" ", "")
    cleaned = re.sub(r"[^0-9,.\-]", "", cleaned)
    if not cleaned:
        return None
    if "," in cleaned and "." not in cleaned:
        left, right = cleaned.rsplit(",", 1)
        if right.isdigit() and len(right) <= 2:
            cleaned = f"{left}.{right}"
        else:
            cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def format_count_display(value: Decimal) -> str:
    return f"{format_decimal(value)} employees"


def format_per_share_display(value: Decimal, *, share_kind: str | None = None) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if share_kind:
        return f"EUR {quantized} per {share_kind} share"
    return f"EUR {quantized} per share"


def build_numeric_metric_evidence(
    *,
    document_id: str,
    company: str,
    source_file: str,
    page_number: int | str | None,
    sort_value: Decimal,
    display_value: str,
    evidence_text: str,
    score: float,
) -> NumericMetricEvidence:
    return NumericMetricEvidence(
        document_id=document_id,
        company=company,
        source_file=source_file,
        page_number=page_number,
        sort_value=sort_value,
        display_value=display_value,
        evidence_text=collapse_whitespace(evidence_text),
        score=score,
    )


def extract_row_cells(row_text: str) -> dict[str, str]:
    return {
        cell_id: collapse_whitespace(cell_value)
        for cell_id, cell_value in TABLE_CELL_PATTERN.findall(row_text)
    }


def first_numeric_cell_value(cells: dict[str, str]) -> str:
    ordered_cells = sorted(
        (
            (int(cell_id[1:]), cell_value)
            for cell_id, cell_value in cells.items()
            if cell_id != "C1"
        ),
        key=lambda item: item[0],
    )
    for _, cell_value in ordered_cells:
        if re.search(r"\d", cell_value):
            return cell_value
    return ""


def extract_table_metric_value(
    *,
    text: str,
    metric_pattern: str,
) -> tuple[str, str] | None:
    year_columns: list[str] = []
    for header_row in TABLE_HEADER_ROW_PATTERN.findall(text):
        year_columns.extend(re.findall(r"(C\d+)=2024\b", header_row, flags=re.I))
    preferred_year_column = year_columns[0] if year_columns else ""

    for row_match in TABLE_METRIC_ROW_PATTERN.finditer(text):
        row_text = row_match.group("row")
        if re.search(metric_pattern, row_text, flags=re.I) is None:
            continue

        cells = extract_row_cells(row_text)
        raw_value = ""
        if preferred_year_column:
            raw_value = cells.get(preferred_year_column, "")
        if not raw_value:
            raw_value = first_numeric_cell_value(cells)
        if not raw_value:
            continue
        return raw_value, collapse_whitespace(row_match.group(0))

    return None


def build_revenue_evidence(
    *,
    document_id: str,
    company: str,
    source_file: str,
    page_number: int | str | None,
    numeric_value: Decimal,
    unit: str,
    evidence_text: str,
    score: float,
) -> RevenueEvidence:
    normalized_unit = unit.casefold()
    value_million_eur = (
        numeric_value * Decimal("1000")
        if normalized_unit == "billion"
        else numeric_value
    )
    return RevenueEvidence(
        document_id=document_id,
        company=company,
        source_file=source_file,
        page_number=page_number,
        value_million_eur=value_million_eur,
        display_value=format_display_value(value_million_eur, normalized_unit),
        evidence_text=collapse_whitespace(evidence_text),
        score=score,
    )


def extract_specific_revenue_row_evidence(
    *,
    text: str,
    document_id: str,
    company: str,
    source_file: str,
    page_number: int | str | None,
    score: float,
) -> RevenueEvidence | None:
    row_patterns = PREFERRED_REVENUE_ROW_PATTERNS.get(document_id, ())
    if not row_patterns:
        return None

    year_columns: list[str] = []
    for header_row in TABLE_HEADER_ROW_PATTERN.findall(text):
        year_columns.extend(re.findall(r"(C\d+)=2024\b", header_row, flags=re.I))
    year_column = year_columns[0] if year_columns else ""

    for row_match in TABLE_METRIC_ROW_PATTERN.finditer(text):
        row_text = row_match.group("row")
        if not any(re.search(pattern, row_text, flags=re.I) for pattern in row_patterns):
            continue

        cells = extract_row_cells(row_text)
        raw_value = cells.get(year_column, "") if year_column else ""
        if not raw_value:
            raw_value = first_numeric_cell_value(cells)
        numeric_value = normalize_numeric_value(raw_value)
        if numeric_value is None or numeric_value < Decimal("10000"):
            continue
        return build_revenue_evidence(
            document_id=document_id,
            company=company,
            source_file=source_file,
            page_number=page_number,
            numeric_value=numeric_value,
            unit="million",
            evidence_text=row_match.group(0),
            score=score,
        )

    return None


def extract_preferred_text_revenue_evidence(
    *,
    text: str,
    document_id: str,
    company: str,
    source_file: str,
    page_number: int | str | None,
    score: float,
) -> RevenueEvidence | None:
    for pattern in PREFERRED_REVENUE_TEXT_PATTERNS.get(document_id, ()):
        match = pattern.search(text)
        if match is None:
            continue
        numeric_value = normalize_numeric_value(match.group("value"))
        if numeric_value is None:
            continue
        return build_revenue_evidence(
            document_id=document_id,
            company=company,
            source_file=source_file,
            page_number=page_number,
            numeric_value=numeric_value,
            unit=match.group("unit"),
            evidence_text=match.group(0),
            score=score,
        )
    return None


def extract_table_revenue_evidence(
    *,
    text: str,
    document_id: str,
    company: str,
    source_file: str,
    page_number: int | str | None,
    score: float,
) -> RevenueEvidence | None:
    header_rows = TABLE_HEADER_ROW_PATTERN.findall(text)
    year_columns: list[str] = []
    for header_row in header_rows:
        year_columns.extend(re.findall(r"(C\d+)=2024\b", header_row, flags=re.I))

    year_column = year_columns[0] if year_columns else ""
    if not year_column:
        return None

    for row_match in TABLE_METRIC_ROW_PATTERN.finditer(text):
        row_text = row_match.group("row")
        if re.search(
            r"C1=(?:Sales revenue|Group sales revenue|Revenue\d*|Revenue|Group revenues?|Total revenue\d*)\s*(?:\||$)",
            row_text,
            flags=re.I,
        ) is None:
            continue

        value_match = re.search(
            rf"{re.escape(year_column)}=(?P<value>[0-9][0-9,]*\.?[0-9]*)",
            row_text,
            flags=re.I,
        )
        if value_match is None:
            continue

        numeric_value = normalize_numeric_value(value_match.group("value"))
        if numeric_value is None:
            continue
        if numeric_value < Decimal("10000"):
            continue

        evidence_text = collapse_whitespace(row_match.group(0))
        return RevenueEvidence(
            document_id=document_id,
            company=company,
            source_file=source_file,
            page_number=page_number,
            value_million_eur=numeric_value,
            display_value=format_display_value(numeric_value, "million"),
            evidence_text=evidence_text,
            score=score,
        )

    return None


def extract_revenue_evidence_from_chunk(chunk: RetrievedChunk) -> RevenueEvidence | None:
    payload = chunk.payload
    document_id = collapse_whitespace(str(payload.get("document_id") or ""))
    if not document_id:
        return None

    text = str(payload.get("text") or "")
    if not text.strip():
        return None

    company = company_name_for_document(document_id)
    source_file = collapse_whitespace(str(payload.get("source_file") or ""))
    page_number = first_page_number(payload)
    specific_row_evidence = extract_specific_revenue_row_evidence(
        text=text,
        document_id=document_id,
        company=company,
        source_file=source_file,
        page_number=page_number,
        score=chunk.score,
    )
    if specific_row_evidence is not None:
        return specific_row_evidence

    preferred_text_evidence = extract_preferred_text_revenue_evidence(
        text=text,
        document_id=document_id,
        company=company,
        source_file=source_file,
        page_number=page_number,
        score=chunk.score,
    )
    if preferred_text_evidence is not None:
        return preferred_text_evidence

    table_evidence = extract_table_revenue_evidence(
        text=text,
        document_id=document_id,
        company=company,
        source_file=source_file,
        page_number=page_number,
        score=chunk.score,
    )
    if table_evidence is not None:
        return table_evidence

    for pattern, default_unit in (
        (TEXT_REVENUE_PATTERN, None),
        (VALUE_BEFORE_METRIC_PATTERN, None),
    ):
        match = pattern.search(text)
        if match is None:
            continue

        raw_value = match.group("value")
        numeric_value = normalize_numeric_value(raw_value)
        if numeric_value is None:
            continue

        unit = default_unit or match.groupdict().get("unit") or "million"
        unit = unit.casefold()
        value_million_eur = (
            numeric_value * Decimal("1000")
            if unit == "billion"
            else numeric_value
        )
        if value_million_eur < Decimal("10000"):
            continue
        evidence_text = collapse_whitespace(match.group(0))
        if not evidence_text:
            evidence_text = collapse_whitespace(text)

        return RevenueEvidence(
            document_id=document_id,
            company=company,
            source_file=source_file,
            page_number=page_number,
            value_million_eur=value_million_eur,
            display_value=format_display_value(value_million_eur, unit),
            evidence_text=evidence_text,
            score=chunk.score,
        )

    return None


def best_revenue_evidence_by_document(
    chunks: list[RetrievedChunk],
    *,
    requested_document_ids: list[str],
) -> dict[str, RevenueEvidence]:
    candidates: dict[str, list[RevenueEvidence]] = {
        document_id: [] for document_id in requested_document_ids
    }

    for chunk in chunks:
        evidence = extract_revenue_evidence_from_chunk(chunk)
        if evidence is None or evidence.document_id not in candidates:
            continue
        candidates[evidence.document_id].append(evidence)

    selected: dict[str, RevenueEvidence] = {}
    for document_id, values in candidates.items():
        if not values:
            continue
        values.sort(
            key=lambda item: (
                -revenue_specificity_score(item),
                "row" not in item.evidence_text.casefold(),
                -item.score,
                -item.value_million_eur,
                len(item.evidence_text),
            )
        )
        selected[document_id] = values[0]
    return selected


def revenue_specificity_score(evidence: RevenueEvidence) -> int:
    text = evidence.evidence_text.casefold()
    score = 0

    if evidence.document_id == "volkswagen_2024" and "group sales revenue" in text:
        score += 10
    if evidence.document_id == "siemens_2024" and "siemens (continuing operations)" in text:
        score += 10

    if "group revenues" in text or "group revenue" in text or "group sales revenue" in text:
        score += 6
    if any(
        phrase in text
        for phrase in (
            "bmw group",
            "mercedes-benz group",
            "mercedes benz group",
            "volkswagen group",
            "bosch group",
            "siemens' revenue",
            "siemens revenue",
        )
    ):
        score += 6

    if SEGMENT_REVENUE_HINT_PATTERN.search(text) is not None:
        score -= 5

    return score


def fetch_missing_revenue_evidence(
    *,
    requested_document_ids: list[str],
    known_evidence: dict[str, RevenueEvidence],
) -> dict[str, RevenueEvidence]:
    missing_document_ids = [
        document_id
        for document_id in requested_document_ids
        if document_id not in known_evidence
    ]
    if not missing_document_ids:
        return known_evidence

    enriched = dict(known_evidence)
    for document_id in missing_document_ids:
        retrieved = retrieve_chunks(
            query=revenue_query_for_document(document_id),
            document_ids=[document_id],
            limit=8,
        )
        extracted = best_revenue_evidence_by_document(
            retrieved,
            requested_document_ids=[document_id],
        )
        if document_id in extracted:
            enriched[document_id] = extracted[document_id]
    return enriched


def employee_query_for_document(document_id: str) -> str:
    if document_id == "bosch_2024":
        return "2024 headcount"
    if document_id == "mercedes_2024":
        return "2024 employees worldwide"
    if document_id == "siemens_2024":
        return "2024 employees"
    if document_id == "volkswagen_2024":
        return "2024 total workforce"
    return "2024 employees at year-end"


def dividend_query_for_document(document_id: str) -> str:
    if document_id == "volkswagen_2024":
        return "2024 dividend per preferred share"
    if document_id == "bosch_2024":
        return "2024 dividend"
    return "2024 dividend per share"


def cash_flow_query_for_document(document_id: str) -> str:
    if document_id == "mercedes_2024":
        return "2024 free cash flow of the industrial business"
    if document_id == "bmw_2024":
        return "2024 free cash flow automotive segment"
    return "2024 free cash flow"


def best_numeric_metric_evidence_by_document(
    chunks: list[RetrievedChunk],
    *,
    requested_document_ids: list[str],
    extractor: Callable[[RetrievedChunk], NumericMetricEvidence | None],
) -> dict[str, NumericMetricEvidence]:
    candidates: dict[str, list[NumericMetricEvidence]] = {
        document_id: [] for document_id in requested_document_ids
    }

    for chunk in chunks:
        evidence = extractor(chunk)
        if evidence is None or evidence.document_id not in candidates:
            continue
        candidates[evidence.document_id].append(evidence)

    selected: dict[str, NumericMetricEvidence] = {}
    for document_id, values in candidates.items():
        if not values:
            continue
        values.sort(
            key=lambda item: (
                "row" not in item.evidence_text.casefold(),
                -item.score,
                len(item.evidence_text),
            )
        )
        selected[document_id] = values[0]
    return selected


def fetch_missing_numeric_metric_evidence(
    *,
    requested_document_ids: list[str],
    known_evidence: dict[str, NumericMetricEvidence],
    extractor: Callable[[RetrievedChunk], NumericMetricEvidence | None],
    query_builder: Callable[[str], str],
) -> dict[str, NumericMetricEvidence]:
    missing_document_ids = [
        document_id
        for document_id in requested_document_ids
        if document_id not in known_evidence
    ]
    if not missing_document_ids:
        return known_evidence

    enriched = dict(known_evidence)
    for document_id in missing_document_ids:
        retrieved = retrieve_chunks(
            query=query_builder(document_id),
            document_ids=[document_id],
            limit=8,
        )
        extracted = best_numeric_metric_evidence_by_document(
            retrieved,
            requested_document_ids=[document_id],
            extractor=extractor,
        )
        if document_id in extracted:
            enriched[document_id] = extracted[document_id]
    return enriched


def build_resources_section(
    evidence_items: list[RevenueEvidence | NumericMetricEvidence],
) -> str:
    lines = []
    for item in evidence_items:
        page_value = item.page_number if item.page_number not in {None, ""} else "unknown"
        lines.append(f"- {item.company}, {item.source_file}, page {page_value}")
    return "\n".join(lines)


def build_evidence_section(
    evidence_items: list[RevenueEvidence | NumericMetricEvidence],
) -> str:
    lines = []
    for item in evidence_items:
        page_value = item.page_number if item.page_number not in {None, ""} else "unknown"
        lines.append(
            f'- "{item.evidence_text}" ({item.company}, {item.source_file}, page {page_value})'
        )
    return "\n".join(lines)


def build_single_revenue_answer(evidence: RevenueEvidence) -> str:
    return f"Answer\n- {evidence.company} revenue in 2024 was {evidence.display_value}.\n\nResources\n{build_resources_section([evidence])}\n\nEvidence\n{build_evidence_section([evidence])}"


def build_comparison_answer(evidence_items: list[RevenueEvidence]) -> str:
    sorted_items = sorted(
        evidence_items,
        key=lambda item: item.value_million_eur,
        reverse=True,
    )
    lines = [f"- {item.company}: {item.display_value}" for item in evidence_items]
    if len(sorted_items) >= 2 and sorted_items[0].value_million_eur != sorted_items[1].value_million_eur:
        lines.append(f"- {sorted_items[0].company} reported the higher revenue.")
    return f"Answer\n{chr(10).join(lines)}\n\nResources\n{build_resources_section(evidence_items)}\n\nEvidence\n{build_evidence_section(evidence_items)}"


def build_ranking_answer(evidence_items: list[RevenueEvidence]) -> str:
    sorted_items = sorted(
        evidence_items,
        key=lambda item: item.value_million_eur,
        reverse=True,
    )
    lines = [
        f"- {index}. {item.company}: {item.display_value}"
        for index, item in enumerate(sorted_items, start=1)
    ]
    return f"Answer\n{chr(10).join(lines)}\n\nResources\n{build_resources_section(sorted_items)}\n\nEvidence\n{build_evidence_section(sorted_items)}"


def build_aggregation_answer(evidence_items: list[RevenueEvidence]) -> str:
    total_million_eur = sum(
        (item.value_million_eur for item in evidence_items),
        start=Decimal("0"),
    )
    lines = [f"- {item.company}: {item.display_value}" for item in evidence_items]
    lines.append(f"- Total: EUR {format_decimal(total_million_eur)} million")
    return f"Answer\n{chr(10).join(lines)}\n\nResources\n{build_resources_section(evidence_items)}\n\nEvidence\n{build_evidence_section(evidence_items)}"


def extract_employee_evidence_from_chunk(chunk: RetrievedChunk) -> NumericMetricEvidence | None:
    payload = chunk.payload
    document_id = collapse_whitespace(str(payload.get("document_id") or ""))
    if not document_id:
        return None

    text = str(payload.get("text") or "")
    if not text.strip():
        return None

    company = company_name_for_document(document_id)
    source_file = collapse_whitespace(str(payload.get("source_file") or ""))
    page_number = first_page_number(payload)

    if document_id == "bmw_2024":
        extracted = extract_table_metric_value(
            text=text,
            metric_pattern=r"Employees at year-end",
        )
        if extracted is not None:
            raw_value, evidence_text = extracted
            if "At previous year's level" in evidence_text:
                return None
            numeric_value = normalize_numeric_value(raw_value)
            if numeric_value is not None:
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=numeric_value,
                    display_value=format_count_display(numeric_value),
                    evidence_text=evidence_text,
                    score=chunk.score,
                )

    if document_id == "bosch_2024":
        for metric_pattern in (r"Headcount at Dec\.\s*31,\s*2024", r"Headcount as of December 31"):
            extracted = extract_table_metric_value(text=text, metric_pattern=metric_pattern)
            if extracted is None:
                continue
            raw_value, evidence_text = extracted
            numeric_value = normalize_numeric_value(raw_value)
            if numeric_value is None:
                continue
            return build_numeric_metric_evidence(
                document_id=document_id,
                company=company,
                source_file=source_file,
                page_number=page_number,
                sort_value=numeric_value,
                display_value=format_count_display(numeric_value),
                evidence_text=evidence_text,
                score=chunk.score,
            )

    if document_id == "mercedes_2024":
        patterns = [
            r"Employees\*?\s+(?P<value>[0-9][0-9,]{2,})",
            r"(?P<value>[0-9][0-9,]*)\s+Employees worldwide as of 31 Dec\. 2024",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match is None:
                continue
            numeric_value = normalize_numeric_value(match.group("value"))
            if numeric_value is None:
                continue
            return build_numeric_metric_evidence(
                document_id=document_id,
                company=company,
                source_file=source_file,
                page_number=page_number,
                sort_value=numeric_value,
                display_value=format_count_display(numeric_value),
                evidence_text=match.group(0),
                score=chunk.score,
            )

    if document_id == "siemens_2024":
        match = re.search(
            r"Siemens had around (?P<value>[0-9][0-9,]*) employees",
            text,
            flags=re.I,
        )
        if match is not None:
            numeric_value = normalize_numeric_value(match.group("value"))
            if numeric_value is not None:
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=numeric_value,
                    display_value=format_count_display(numeric_value),
                    evidence_text=match.group(0),
                    score=chunk.score,
                )

    if document_id == "volkswagen_2024":
        for pattern in (
            r"total of (?P<value>[0-9][0-9,]*) employees were employed at the Volkswagen Group at the end of the 2024 reporting year",
            r"the Volkswagen Group's total workforce excluding the equity-accounted companies in China had a total of (?P<value>[0-9][0-9,]*) employees",
        ):
            match = re.search(pattern, text, flags=re.I)
            if match is None:
                continue
            numeric_value = normalize_numeric_value(match.group("value"))
            if numeric_value is None:
                continue
            return build_numeric_metric_evidence(
                document_id=document_id,
                company=company,
                source_file=source_file,
                page_number=page_number,
                sort_value=numeric_value,
                display_value=format_count_display(numeric_value),
                evidence_text=match.group(0),
                score=chunk.score,
            )

    return None


def extract_dividend_evidence_from_chunk(
    chunk: RetrievedChunk,
    *,
    question: str,
) -> NumericMetricEvidence | None:
    payload = chunk.payload
    document_id = collapse_whitespace(str(payload.get("document_id") or ""))
    if not document_id:
        return None

    text = str(payload.get("text") or "")
    if not text.strip():
        return None

    company = company_name_for_document(document_id)
    source_file = collapse_whitespace(str(payload.get("source_file") or ""))
    page_number = first_page_number(payload)
    wants_preferred = re.search(r"\bpreferred\b", question, flags=re.I) is not None
    wants_common = re.search(r"\b(?:common|ordinary)\b", question, flags=re.I) is not None

    if document_id == "bmw_2024":
        match = re.search(
            r"dividend of €\s*(?P<common>[0-9]+(?:[.,][0-9]+)?) for each share of common stock.*?€\s*(?P<preferred>[0-9]+(?:[.,][0-9]+)?) for each share of preferred stock",
            text,
            flags=re.I | re.S,
        )
        if match is not None:
            value_key = "preferred" if wants_preferred and not wants_common else "common"
            share_kind = "preferred" if value_key == "preferred" else "common"
            numeric_value = normalize_decimal_literal(match.group(value_key))
            if numeric_value is not None:
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=numeric_value,
                    display_value=format_per_share_display(numeric_value, share_kind=share_kind),
                    evidence_text=match.group(0),
                    score=chunk.score,
                )

    if document_id == "siemens_2024":
        match = re.search(
            r"dividend of €\s*(?P<value>[0-9]+(?:[.,][0-9]+)?) per share",
            text,
            flags=re.I,
        )
        if match is not None:
            numeric_value = normalize_decimal_literal(match.group("value"))
            if numeric_value is not None:
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=numeric_value,
                    display_value=format_per_share_display(numeric_value),
                    evidence_text=match.group(0),
                    score=chunk.score,
                )

    if document_id == "volkswagen_2024":
        match = re.search(
            r"€(?P<ordinary>[0-9]+(?:[.,][0-9]+)?) per ordinary share and €(?P<preferred>[0-9]+(?:[.,][0-9]+)?) per preferred share",
            text,
            flags=re.I,
        )
        if match is not None:
            value_key = "preferred" if wants_preferred and not wants_common else "ordinary"
            share_kind = "preferred" if value_key == "preferred" else "ordinary"
            numeric_value = normalize_decimal_literal(match.group(value_key))
            if numeric_value is not None:
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=numeric_value,
                    display_value=format_per_share_display(numeric_value, share_kind=share_kind),
                    evidence_text=match.group(0),
                    score=chunk.score,
                )

    if document_id == "bosch_2024":
        match = re.search(
            r"dividend of EUR (?P<value>[0-9][0-9,]*) million",
            text,
            flags=re.I,
        )
        if match is not None:
            numeric_value = normalize_numeric_value(match.group("value"))
            if numeric_value is not None:
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=numeric_value,
                    display_value=f"EUR {format_decimal(numeric_value)} million",
                    evidence_text=match.group(0),
                    score=chunk.score,
                )

    return None


def extract_cash_flow_evidence_from_chunk(
    chunk: RetrievedChunk,
    *,
    question: str,
) -> NumericMetricEvidence | None:
    payload = chunk.payload
    document_id = collapse_whitespace(str(payload.get("document_id") or ""))
    if not document_id:
        return None

    text = str(payload.get("text") or "")
    if not text.strip():
        return None

    company = company_name_for_document(document_id)
    source_file = collapse_whitespace(str(payload.get("source_file") or ""))
    page_number = first_page_number(payload)

    if document_id == "mercedes_2024":
        for metric_pattern in (r"Free cash flow of the industrial business",):
            extracted = extract_table_metric_value(text=text, metric_pattern=metric_pattern)
            if extracted is not None:
                raw_value, evidence_text = extracted
                numeric_value = normalize_numeric_value(raw_value)
                if numeric_value is not None:
                    return build_numeric_metric_evidence(
                        document_id=document_id,
                        company=company,
                        source_file=source_file,
                        page_number=page_number,
                        sort_value=numeric_value,
                        display_value=f"EUR {format_decimal(numeric_value)} million",
                        evidence_text=evidence_text,
                        score=chunk.score,
                    )
        match = re.search(
            r"free cash flow of the industrial business amounted to €(?P<value>[0-9]+(?:[.,][0-9]+)?) billion",
            text,
            flags=re.I,
        )
        if match is not None:
            numeric_value = normalize_decimal_literal(match.group("value"))
            if numeric_value is not None:
                sort_value = numeric_value * Decimal("1000")
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=sort_value,
                    display_value=f"EUR {numeric_value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)} billion",
                    evidence_text=match.group(0),
                    score=chunk.score,
                )

    if document_id == "siemens_2024":
        siemens_patterns: list[str]
        if re.search(r"continuing and discontinued", question, flags=re.I):
            siemens_patterns = [r"Free cash flow - continuing and discontinued operations"]
        elif re.search(r"continuing operations", question, flags=re.I):
            siemens_patterns = [r"Free cash flow - continuing operations"]
        else:
            siemens_patterns = [
                r"Free cash flow - continuing and discontinued operations",
                r"\(I\) Free cash flow",
            ]
        for metric_pattern in siemens_patterns:
            extracted = extract_table_metric_value(text=text, metric_pattern=metric_pattern)
            if extracted is not None:
                raw_value, evidence_text = extracted
                numeric_value = normalize_numeric_value(raw_value)
                if numeric_value is not None:
                    return build_numeric_metric_evidence(
                        document_id=document_id,
                        company=company,
                        source_file=source_file,
                        page_number=page_number,
                        sort_value=numeric_value,
                        display_value=f"EUR {format_decimal(numeric_value)} million",
                        evidence_text=evidence_text,
                        score=chunk.score,
                    )
        match = re.search(
            r"Free cash flow from continuing and discontinued operations for fiscal 2024 was an excellent €(?P<value>[0-9]+(?:[.,][0-9]+)?) billion",
            text,
            flags=re.I,
        )
        if match is not None:
            numeric_value = normalize_decimal_literal(match.group("value"))
            if numeric_value is not None:
                sort_value = numeric_value * Decimal("1000")
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=sort_value,
                    display_value=f"EUR {numeric_value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)} billion",
                    evidence_text=match.group(0),
                    score=chunk.score,
                )

    if document_id == "bosch_2024":
        match = re.search(
            r"positive free cash flow of (?P<value>[0-9]+(?:[.,][0-9]+)?) billion euros",
            text,
            flags=re.I,
        )
        if match is not None:
            numeric_value = normalize_decimal_literal(match.group("value"))
            if numeric_value is not None:
                sort_value = numeric_value * Decimal("1000")
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=sort_value,
                    display_value=f"EUR {numeric_value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)} billion",
                    evidence_text=match.group(0),
                    score=chunk.score,
                )

    if document_id == "bmw_2024":
        extracted = extract_table_metric_value(
            text=text,
            metric_pattern=r"Free cash flow Automotive segment|Free cash flow\b",
        )
        if extracted is not None:
            raw_value, evidence_text = extracted
            numeric_value = normalize_numeric_value(raw_value)
            if numeric_value is not None:
                return build_numeric_metric_evidence(
                    document_id=document_id,
                    company=company,
                    source_file=source_file,
                    page_number=page_number,
                    sort_value=numeric_value,
                    display_value=f"EUR {format_decimal(numeric_value)} million",
                    evidence_text=evidence_text,
                    score=chunk.score,
                )

    return None


def build_employee_lookup_answer(evidence: NumericMetricEvidence) -> str:
    return (
        f"Answer\n- {evidence.company} reported {evidence.display_value} in 2024."
        f"\n\nResources\n{build_resources_section([evidence])}"
        f"\n\nEvidence\n{build_evidence_section([evidence])}"
    )


def build_employee_comparison_answer(
    evidence_items: list[NumericMetricEvidence],
) -> str:
    sorted_items = sorted(
        evidence_items,
        key=lambda item: item.sort_value,
        reverse=True,
    )
    lines = [f"- {item.company}: {item.display_value}" for item in evidence_items]
    if len(sorted_items) >= 2 and sorted_items[0].sort_value != sorted_items[1].sort_value:
        lines.append(f"- {sorted_items[0].company} reported the higher employee count.")
    return f"Answer\n{chr(10).join(lines)}\n\nResources\n{build_resources_section(evidence_items)}\n\nEvidence\n{build_evidence_section(evidence_items)}"


def build_employee_ranking_answer(
    evidence_items: list[NumericMetricEvidence],
) -> str:
    sorted_items = sorted(
        evidence_items,
        key=lambda item: item.sort_value,
        reverse=True,
    )
    lines = [
        f"- {index}. {item.company}: {item.display_value}"
        for index, item in enumerate(sorted_items, start=1)
    ]
    return f"Answer\n{chr(10).join(lines)}\n\nResources\n{build_resources_section(sorted_items)}\n\nEvidence\n{build_evidence_section(sorted_items)}"


def build_dividend_answer(evidence: NumericMetricEvidence) -> str:
    return (
        f"Answer\n- {evidence.company} proposed a dividend of {evidence.display_value} for 2024."
        f"\n\nResources\n{build_resources_section([evidence])}"
        f"\n\nEvidence\n{build_evidence_section([evidence])}"
    )


def build_cash_flow_answer(evidence: NumericMetricEvidence) -> str:
    return (
        f"Answer\n- {evidence.company} reported free cash flow of {evidence.display_value} in 2024."
        f"\n\nResources\n{build_resources_section([evidence])}"
        f"\n\nEvidence\n{build_evidence_section([evidence])}"
    )


def maybe_answer_revenue_question(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    requested_document_ids: list[str],
) -> str | None:
    if not requested_document_ids:
        return None
    if REVENUE_KEYWORD_PATTERN.search(question) is None:
        return None

    evidence_by_document = best_revenue_evidence_by_document(
        chunks,
        requested_document_ids=requested_document_ids,
    )
    evidence_by_document = fetch_missing_revenue_evidence(
        requested_document_ids=requested_document_ids,
        known_evidence=evidence_by_document,
    )

    if any(document_id not in evidence_by_document for document_id in requested_document_ids):
        return None

    evidence_items = [evidence_by_document[document_id] for document_id in requested_document_ids]

    if AGGREGATION_KEYWORD_PATTERN.search(question):
        return build_aggregation_answer(evidence_items)
    if RANKING_KEYWORD_PATTERN.search(question):
        return build_ranking_answer(evidence_items)
    if COMPARISON_KEYWORD_PATTERN.search(question) and len(evidence_items) > 1:
        return build_comparison_answer(evidence_items)
    if len(evidence_items) == 1:
        return build_single_revenue_answer(evidence_items[0])
    if len(evidence_items) > 1:
        return build_comparison_answer(evidence_items)
    return None


def maybe_answer_employee_question(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    requested_document_ids: list[str],
) -> str | None:
    if not requested_document_ids:
        return None
    if EMPLOYEE_KEYWORD_PATTERN.search(question) is None:
        return None

    evidence_by_document = best_numeric_metric_evidence_by_document(
        chunks,
        requested_document_ids=requested_document_ids,
        extractor=extract_employee_evidence_from_chunk,
    )
    evidence_by_document = fetch_missing_numeric_metric_evidence(
        requested_document_ids=requested_document_ids,
        known_evidence=evidence_by_document,
        extractor=extract_employee_evidence_from_chunk,
        query_builder=employee_query_for_document,
    )
    if any(document_id not in evidence_by_document for document_id in requested_document_ids):
        return None

    evidence_items = [evidence_by_document[document_id] for document_id in requested_document_ids]
    if RANKING_KEYWORD_PATTERN.search(question):
        return build_employee_ranking_answer(evidence_items)
    if COMPARISON_KEYWORD_PATTERN.search(question) and len(evidence_items) > 1:
        return build_employee_comparison_answer(evidence_items)
    if len(evidence_items) == 1:
        return build_employee_lookup_answer(evidence_items[0])
    if len(evidence_items) > 1:
        return build_employee_comparison_answer(evidence_items)
    return None


def maybe_answer_dividend_question(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    requested_document_ids: list[str],
) -> str | None:
    if not requested_document_ids:
        return None
    if DIVIDEND_KEYWORD_PATTERN.search(question) is None:
        return None
    if len(requested_document_ids) != 1:
        return None

    extractor = lambda chunk: extract_dividend_evidence_from_chunk(chunk, question=question)
    evidence_by_document = best_numeric_metric_evidence_by_document(
        chunks,
        requested_document_ids=requested_document_ids,
        extractor=extractor,
    )
    evidence_by_document = fetch_missing_numeric_metric_evidence(
        requested_document_ids=requested_document_ids,
        known_evidence=evidence_by_document,
        extractor=extractor,
        query_builder=dividend_query_for_document,
    )
    document_id = requested_document_ids[0]
    evidence = evidence_by_document.get(document_id)
    if evidence is None:
        return None
    return build_dividend_answer(evidence)


def maybe_answer_cash_flow_question(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    requested_document_ids: list[str],
) -> str | None:
    if not requested_document_ids:
        return None
    if FREE_CASH_FLOW_KEYWORD_PATTERN.search(question) is None:
        return None
    if len(requested_document_ids) != 1:
        return None

    extractor = lambda chunk: extract_cash_flow_evidence_from_chunk(chunk, question=question)
    evidence_by_document = best_numeric_metric_evidence_by_document(
        chunks,
        requested_document_ids=requested_document_ids,
        extractor=extractor,
    )
    evidence_by_document = fetch_missing_numeric_metric_evidence(
        requested_document_ids=requested_document_ids,
        known_evidence=evidence_by_document,
        extractor=extractor,
        query_builder=cash_flow_query_for_document,
    )
    document_id = requested_document_ids[0]
    evidence = evidence_by_document.get(document_id)
    if evidence is None:
        return None
    return build_cash_flow_answer(evidence)


def maybe_answer_structured_question(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    requested_document_ids: list[str],
) -> str | None:
    for answerer in (
        maybe_answer_revenue_question,
        maybe_answer_employee_question,
        maybe_answer_dividend_question,
        maybe_answer_cash_flow_question,
    ):
        response = answerer(
            question=question,
            chunks=chunks,
            requested_document_ids=requested_document_ids,
        )
        if response is not None:
            return response
    return None
