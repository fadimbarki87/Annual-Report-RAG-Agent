from __future__ import annotations

import re
from typing import Any

from agent_pipeline.answer_generation.scope_guard import (
    NO_STRONG_ANSWER_RESPONSE,
    UNSUPPORTED_RESPONSE,
)


SECTION_PATTERN = re.compile(
    r"(?m)^(Answer|Reporting Period|Resources|Evidence)\s*$"
)

SPECIAL_RESPONSES = {
    UNSUPPORTED_RESPONSE,
    NO_STRONG_ANSWER_RESPONSE,
    "I do not find sufficient data in the documents to compute this.",
    "I only have data from the 2024 annual reports unless prior-year information is explicitly stated in them.",
}


def strip_bullet_prefix(value: str) -> str:
    return re.sub(r"^\s*[-*•]\s*", "", value).strip()


def parse_page_number(value: str) -> int | str | None:
    cleaned = value.strip()
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
        title = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(response_text)
        sections[title] = response_text[start:end].strip()
    return sections


def parse_resources(raw_resources: str) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for line in raw_resources.splitlines():
        cleaned = strip_bullet_prefix(line)
        if not cleaned or cleaned.casefold() == "none":
            continue

        match = re.match(
            r"^(?P<company>.+?),\s*(?P<source_file>[^,]+?),\s*page\s*(?P<page>.+)$",
            cleaned,
            flags=re.I,
        )
        if not match:
            resources.append(
                {
                    "company": "",
                    "source_file": "",
                    "page_number": None,
                    "raw": cleaned,
                }
            )
            continue

        resources.append(
            {
                "company": match.group("company").strip(),
                "source_file": match.group("source_file").strip(),
                "page_number": parse_page_number(match.group("page")),
                "raw": cleaned,
            }
        )
    return resources


def parse_evidence(raw_evidence: str) -> list[dict[str, Any]]:
    evidence_items: list[dict[str, Any]] = []
    for line in raw_evidence.splitlines():
        cleaned = strip_bullet_prefix(line)
        if not cleaned or cleaned.casefold() == "none":
            continue

        page_match = re.match(
            r"^Page\s+(?P<page>[^:]+):\s*\"?(?P<text>.*)\"?$",
            cleaned,
            flags=re.I,
        )
        if page_match:
            evidence_items.append(
                {
                    "text": page_match.group("text").strip(),
                    "page_number": parse_page_number(page_match.group("page")),
                    "company": "",
                    "source_file": "",
                    "raw": cleaned,
                }
            )
            continue

        evidence_items.append(
            {
                "text": cleaned,
                "page_number": None,
                "company": "",
                "source_file": "",
                "raw": cleaned,
            }
        )
    return evidence_items


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
