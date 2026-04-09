from __future__ import annotations

import re
from typing import Any

from agent_pipeline.answer_generation.scope_guard import (
    NO_STRONG_ANSWER_RESPONSE,
    UNSUPPORTED_RESPONSE,
)


SECTION_PATTERN = re.compile(
    r"(?im)^(Answer|Reporting Period|Resources|Evidence)\s*:?\s*$"
)
LIST_PREFIX_PATTERN = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s*")
PAGE_PREFIX_PATTERN = re.compile(r"^(?:pages?|pp?|p)\.?\s*", flags=re.I)
SOURCE_FILE_PATTERN = re.compile(r"(?P<source_file>[^,\s()]+\.pdf)\b", flags=re.I)
PAGE_REFERENCE_PATTERN = re.compile(
    r"\b(?P<page>(?:pages?|pp?|p)\.?\s*\d[\d,\sand-]*)\b",
    flags=re.I,
)
RESOURCE_PATTERN = re.compile(
    r"^(?:(?P<company>.+?),\s*)?"
    r"(?P<source_file>[^,\s()]+\.pdf)\s*,\s*"
    r"(?P<page>(?:pages?|pp?|p)\.?\s*.+?)\s*$",
    flags=re.I,
)
EVIDENCE_PREFIX_CITATION_PATTERN = re.compile(
    r"^(?:(?P<company>.+?),\s*)?"
    r"(?P<source_file>[^,\s()]+\.pdf)\s*,\s*"
    r"(?P<page>(?:pages?|pp?|p)\.?\s*[^:\n]+)\s*:\s*"
    r"(?P<text>.*)$",
    flags=re.I | re.S,
)
EVIDENCE_SUFFIX_CITATION_PATTERN = re.compile(
    r"^(?P<text>.*?)(?:\s*\("
    r"(?:(?P<company>[^,()]+),\s*)?"
    r"(?P<source_file>[^,\s()]+\.pdf)\s*,\s*"
    r"(?P<page>(?:pages?|pp?|p)\.?\s*[^)]+)"
    r"\))\s*$",
    flags=re.I | re.S,
)
EVIDENCE_PAGE_PREFIX_PATTERN = re.compile(
    r"^Page\s+(?P<page>[^:\n]+):\s*(?P<text>.*)$",
    flags=re.I | re.S,
)
EVIDENCE_PAGE_SUFFIX_PATTERN = re.compile(
    r"^(?P<text>.*?)(?:\s*\((?P<page>(?:pages?|pp?|p)\.?\s*[^)]+)\))\s*$",
    flags=re.I | re.S,
)
COMPANY_HEADER_PATTERN = re.compile(r"^[A-Za-z0-9 .&'/()-]+:\s*$")

SPECIAL_RESPONSES = {
    UNSUPPORTED_RESPONSE,
    NO_STRONG_ANSWER_RESPONSE,
    "I do not find sufficient data in the documents to compute this.",
    "I only have data from the 2024 annual reports unless prior-year information is explicitly stated in them.",
}


def collapse_whitespace(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\u00a0", " ").split()).strip()


def strip_list_prefix(value: str) -> str:
    return LIST_PREFIX_PATTERN.sub("", value, count=1).strip()


def strip_page_prefix(value: str) -> str:
    return PAGE_PREFIX_PATTERN.sub("", value, count=1).strip()


def parse_page_number(value: str) -> int | str | None:
    cleaned = collapse_whitespace(value).strip("()[]{}\"'.,;: ")
    cleaned = strip_page_prefix(cleaned)
    if not cleaned:
        return None
    if cleaned.isdigit():
        return int(cleaned)
    return cleaned


def parse_sections(response_text: str) -> dict[str, str]:
    matches = list(SECTION_PATTERN.finditer(response_text))
    if not matches:
        return {"Answer": response_text.strip()}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).title()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(response_text)
        sections[title] = response_text[start:end].strip()
    return sections


def resource_identity(resource: dict[str, Any]) -> tuple[str, str, str] | None:
    company = collapse_whitespace(resource.get("company")).casefold()
    source_file = collapse_whitespace(resource.get("source_file")).casefold()
    page_number = collapse_whitespace(resource.get("page_number"))
    if not any((company, source_file, page_number)):
        return None
    return (company, source_file, page_number.casefold())


def normalize_resource(
    *,
    company: str = "",
    source_file: str = "",
    page_number: int | str | None = None,
    raw: str = "",
) -> dict[str, Any]:
    return {
        "company": collapse_whitespace(company),
        "source_file": collapse_whitespace(source_file),
        "page_number": page_number,
        "raw": collapse_whitespace(raw),
    }


def build_resource_from_match(match: re.Match[str], raw: str) -> dict[str, Any]:
    return normalize_resource(
        company=match.groupdict().get("company") or "",
        source_file=match.groupdict().get("source_file") or "",
        page_number=parse_page_number(match.groupdict().get("page") or ""),
        raw=raw,
    )


def extract_source_file(value: str) -> str:
    match = SOURCE_FILE_PATTERN.search(value)
    return collapse_whitespace(match.group("source_file")) if match else ""


def extract_page_reference(value: str) -> int | str | None:
    match = PAGE_REFERENCE_PATTERN.search(value)
    if not match:
        return None
    return parse_page_number(match.group("page"))


def parse_resource_line(line: str) -> dict[str, Any] | None:
    cleaned = collapse_whitespace(strip_list_prefix(line))
    if not cleaned or cleaned.casefold() == "none":
        return None

    match = RESOURCE_PATTERN.fullmatch(cleaned)
    if match:
        return build_resource_from_match(match, cleaned)

    source_file = extract_source_file(cleaned)
    page_number = extract_page_reference(cleaned)
    company = ""
    if source_file:
        company = collapse_whitespace(cleaned.split(source_file, maxsplit=1)[0].rstrip(", "))

    return normalize_resource(
        company=company,
        source_file=source_file,
        page_number=page_number,
        raw=cleaned,
    )


def parse_resources(raw_resources: str) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for line in raw_resources.splitlines():
        resource = parse_resource_line(line)
        if resource is None:
            continue
        resources.append(resource)
    return resources


def looks_like_evidence_item_start(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if LIST_PREFIX_PATTERN.match(stripped):
        return True
    if EVIDENCE_PAGE_PREFIX_PATTERN.match(stripped):
        return True
    if EVIDENCE_PREFIX_CITATION_PATTERN.match(stripped):
        return True
    return False


def split_evidence_blocks(raw_evidence: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []

    for line in raw_evidence.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue

        if current and looks_like_evidence_item_start(line):
            blocks.append("\n".join(current).strip())
            current = [line]
            continue

        current.append(line)

    if current:
        blocks.append("\n".join(current).strip())

    return blocks


def parse_evidence_block(block: str) -> dict[str, Any] | None:
    cleaned = block.strip()
    cleaned = LIST_PREFIX_PATTERN.sub("", cleaned, count=1).strip()
    if not cleaned or cleaned.casefold() == "none":
        return None
    if COMPANY_HEADER_PATTERN.fullmatch(collapse_whitespace(cleaned)):
        return None

    company = ""
    source_file = ""
    page_number: int | str | None = None
    text = cleaned

    prefix_match = EVIDENCE_PREFIX_CITATION_PATTERN.match(cleaned)
    if prefix_match:
        company = prefix_match.group("company") or ""
        source_file = prefix_match.group("source_file") or ""
        page_number = parse_page_number(prefix_match.group("page") or "")
        text = prefix_match.group("text") or ""
    else:
        page_prefix_match = EVIDENCE_PAGE_PREFIX_PATTERN.match(cleaned)
        if page_prefix_match:
            page_number = parse_page_number(page_prefix_match.group("page") or "")
            text = page_prefix_match.group("text") or ""
        else:
            suffix_match = EVIDENCE_SUFFIX_CITATION_PATTERN.match(cleaned)
            if suffix_match:
                company = suffix_match.group("company") or ""
                source_file = suffix_match.group("source_file") or ""
                page_number = parse_page_number(suffix_match.group("page") or "")
                text = suffix_match.group("text") or ""
            else:
                page_suffix_match = EVIDENCE_PAGE_SUFFIX_PATTERN.match(cleaned)
                if page_suffix_match:
                    page_number = parse_page_number(page_suffix_match.group("page") or "")
                    text = page_suffix_match.group("text") or ""

    text = collapse_whitespace(text)
    if not text:
        return None

    return {
        "text": text,
        "page_number": page_number,
        "company": collapse_whitespace(company),
        "source_file": collapse_whitespace(source_file),
        "raw": collapse_whitespace(cleaned),
    }


def parse_evidence(raw_evidence: str) -> list[dict[str, Any]]:
    evidence_items: list[dict[str, Any]] = []
    for block in split_evidence_blocks(raw_evidence):
        item = parse_evidence_block(block)
        if item is None:
            continue
        evidence_items.append(item)
    return evidence_items


def resources_from_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    derived: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for item in evidence:
        resource = normalize_resource(
            company=item.get("company", ""),
            source_file=item.get("source_file", ""),
            page_number=item.get("page_number"),
            raw=item.get("raw", ""),
        )
        key = resource_identity(resource)
        if key is None or key in seen:
            continue
        seen.add(key)
        derived.append(resource)

    return derived


def merge_resources(
    resources: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    derived_resources = resources_from_evidence(evidence)
    structured_resources = [item for item in resources if resource_identity(item) is not None]
    if not structured_resources:
        return derived_resources or resources

    merged = list(structured_resources)
    seen = {
        key
        for key in (resource_identity(item) for item in structured_resources)
        if key is not None
    }
    for item in derived_resources:
        key = resource_identity(item)
        if key is None or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def parse_answer_response(response_text: str) -> dict[str, Any]:
    normalized = response_text.strip()
    if normalized in SPECIAL_RESPONSES:
        return {
            "mode": "special_refusal",
            "answer": normalized,
            "reporting_period": None,
            "resources": [],
            "evidence": [],
            "raw_response": response_text,
        }

    sections = parse_sections(response_text)
    resources = parse_resources(sections.get("Resources", ""))
    evidence = parse_evidence(sections.get("Evidence", ""))
    resources = merge_resources(resources, evidence)

    if len(resources) == 1:
        resource = resources[0]
        for item in evidence:
            if item.get("page_number") in {None, ""}:
                item["page_number"] = resource.get("page_number")
            if not item.get("company"):
                item["company"] = resource.get("company", "")
            if not item.get("source_file"):
                item["source_file"] = resource.get("source_file", "")

    return {
        "mode": "grounded_answer",
        "answer": sections.get("Answer", normalized),
        "reporting_period": sections.get("Reporting Period") or None,
        "resources": resources,
        "evidence": evidence,
        "raw_response": response_text,
    }
