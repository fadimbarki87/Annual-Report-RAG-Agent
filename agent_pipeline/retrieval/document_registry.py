from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DocumentInfo:
    document_id: str
    company_name: str
    source_file: str
    aliases: tuple[str, ...]


DOCUMENTS: dict[str, DocumentInfo] = {
    "bmw_2024": DocumentInfo(
        document_id="bmw_2024",
        company_name="BMW Group",
        source_file="bmw_2024.pdf",
        aliases=("bmw", "bmw group"),
    ),
    "bosch_2024": DocumentInfo(
        document_id="bosch_2024",
        company_name="Robert Bosch GmbH",
        source_file="bosch_2024.pdf",
        aliases=("bosch", "robert bosch", "robert bosch gmbh"),
    ),
    "mercedes_2024": DocumentInfo(
        document_id="mercedes_2024",
        company_name="Mercedes-Benz Group",
        source_file="mercedes_2024.pdf",
        aliases=(
            "mercedes",
            "mercedes benz",
            "mercedes-benz",
            "mercedes-benz group",
        ),
    ),
    "siemens_2024": DocumentInfo(
        document_id="siemens_2024",
        company_name="Siemens AG",
        source_file="siemens_2024.pdf",
        aliases=("siemens", "siemens ag"),
    ),
    "volkswagen_2024": DocumentInfo(
        document_id="volkswagen_2024",
        company_name="Volkswagen Group",
        source_file="volkswagen_2024.pdf",
        aliases=("volkswagen", "volkswagen group", "vw"),
    ),
}


def normalize_lookup_key(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}

    for document_id, document in DOCUMENTS.items():
        aliases[normalize_lookup_key(document_id)] = document_id
        aliases[normalize_lookup_key(document.source_file)] = document_id
        aliases[normalize_lookup_key(document.company_name)] = document_id
        for alias in document.aliases:
            aliases[normalize_lookup_key(alias)] = document_id

    return aliases


def detect_document_ids_in_text(text: str | None) -> list[str]:
    normalized_text = normalize_lookup_key(text or "")
    if not normalized_text:
        return []

    matches: list[tuple[int, int, str]] = []
    for alias, document_id in alias_map().items():
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        matches.append((match.start(), -len(alias), document_id))

    ordered_document_ids: list[str] = []
    for _, _, document_id in sorted(matches):
        if document_id not in ordered_document_ids:
            ordered_document_ids.append(document_id)
    return ordered_document_ids


def resolve_document_ids(company_filters: Iterable[str] | None) -> list[str]:
    values = [value for value in company_filters or [] if value and value.strip()]
    if not values:
        return []

    lookup = alias_map()
    resolved: list[str] = []
    unknown: list[str] = []

    for value in values:
        normalized = normalize_lookup_key(value)
        if normalized in {"all", "all companies", "all documents"}:
            return list(DOCUMENTS)

        document_id = lookup.get(normalized)
        if document_id is None:
            unknown.append(value)
            continue
        if document_id not in resolved:
            resolved.append(document_id)

    if unknown:
        supported = ", ".join(document.company_name for document in DOCUMENTS.values())
        raise ValueError(
            "Unknown company/document filter: "
            + ", ".join(unknown)
            + f". Supported companies: {supported}."
        )

    return resolved


def document_info(document_id: str | None) -> DocumentInfo | None:
    if document_id is None:
        return None
    return DOCUMENTS.get(document_id)


def company_name_for_document(document_id: str | None) -> str:
    document = document_info(document_id)
    if document is None:
        return str(document_id or "unknown")
    return document.company_name
