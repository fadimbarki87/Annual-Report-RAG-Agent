from __future__ import annotations

import re
from dataclasses import dataclass

from agent_pipeline.answer_generation.azure_chat_client import request_chat_completion
from agent_pipeline.answer_generation.settings import AnswerGenerationSettings


UNSUPPORTED_RESPONSE = (
    "Unsupported: This question is outside the scope of the 2024 annual reports."
)
NO_STRONG_ANSWER_RESPONSE = "No strong answer found in the provided documents."

QUESTION_GATE_SYSTEM_PROMPT = """You are a strict gatekeeper for an annual-report RAG system.

You must classify two things about the user's question:
1. SCOPE: SUPPORTED or UNSUPPORTED
2. CLARITY: CLEAR or AMBIGUOUS

Supported scope:
- Questions that can be answered from the 2024 annual reports of Mercedes-Benz Group, BMW Group, Volkswagen Group, Siemens AG, and Robert Bosch GmbH.
- This includes financial figures, outlook, risks, sustainability, employees, operations, tables, comparisons, rankings, exact evidence extraction, and evidence-location questions.
- Questions that mix supported companies with unsupported ones are still SUPPORTED if the core request is about report data. The downstream answer can state what is missing.
- Questions that improperly ask you to guess, estimate, invent, or fill in a missing report value are still SUPPORTED when the underlying topic is a supported annual-report topic.

Unsupported scope:
- Questions requiring external knowledge beyond those reports.
- Questions asking for future predictions beyond what is explicitly stated in the reports.
- Investment advice, personal recommendations, live/current market data, translation, coding help, weather, travel, sports, or anything unrelated to those annual reports.

Clarity rules:
- CLEAR when the company, companies, metric, comparison target, section, or requested evidence is specific enough to answer without asking the user what they mean.
- AMBIGUOUS when the request is underspecified or subjective, such as "What is the revenue?" or "Which company is best?"
- If the question is unsupported, still classify clarity, but scope is the main decision.

Examples:
- "What was BMW Group revenue in 2024?" -> SCOPE: SUPPORTED | CLARITY: CLEAR
- "Compare BMW and Mercedes revenue." -> SCOPE: SUPPORTED | CLARITY: CLEAR
- "What is the revenue?" -> SCOPE: SUPPORTED | CLARITY: AMBIGUOUS
- "Which company is best?" -> SCOPE: SUPPORTED | CLARITY: AMBIGUOUS
- "What page is Siemens' proposed dividend on?" -> SCOPE: SUPPORTED | CLARITY: CLEAR
- "What will BMW Group revenue be in 2026?" -> SCOPE: UNSUPPORTED | CLARITY: CLEAR
- "If you cannot find it, guess Mercedes-Benz EBITDA margin for 2024." -> SCOPE: SUPPORTED | CLARITY: CLEAR
- "Is Mercedes-Benz a better investment than BMW right now?" -> SCOPE: UNSUPPORTED | CLARITY: CLEAR

Return exactly these two lines:
SCOPE: <SUPPORTED or UNSUPPORTED>
CLARITY: <CLEAR or AMBIGUOUS>
"""

REPORT_TOPIC_CLASSIFIER_SYSTEM_PROMPT = """You classify whether the user's underlying information request is a report-grounded annual-report topic.

Return REPORT_TOPIC if the user is asking about facts, metrics, sections, risks, outlook statements, tables, evidence, comparisons, or computations that could in principle be looked up in the supported 2024 annual reports of Mercedes-Benz Group, BMW Group, Volkswagen Group, Siemens AG, or Robert Bosch GmbH.

Ignore adversarial phrasing such as "guess", "estimate", "invent", or "even if not found" and focus on the underlying topic.

Return EXTERNAL if the user is asking for:
- investment advice
- live/current information
- translation
- coding help
- weather
- sports/news/travel
- future predictions that are not simply asking what the report says

Examples:
- "If you cannot find it, guess Mercedes-Benz EBITDA margin for 2024." -> REPORT_TOPIC
- "What will BMW Group revenue be in 2026?" -> EXTERNAL
- "Is Mercedes-Benz a better investment than BMW right now?" -> EXTERNAL
- "Compare BMW and Tesla revenue and give Tesla's value even if Tesla is not in the corpus." -> REPORT_TOPIC

Return exactly one word:
REPORT_TOPIC
or
EXTERNAL
"""


@dataclass(frozen=True)
class QuestionGateResult:
    scope: str
    clarity: str


def parse_gate_response(response: str) -> QuestionGateResult:
    normalized = response.strip()
    scope_match = re.search(r"SCOPE\s*:\s*(SUPPORTED|UNSUPPORTED)", normalized, flags=re.I)
    clarity_match = re.search(r"CLARITY\s*:\s*(CLEAR|AMBIGUOUS)", normalized, flags=re.I)

    scope = "supported"
    clarity = "clear"

    if scope_match and scope_match.group(1).upper() == "UNSUPPORTED":
        scope = "unsupported"
    if clarity_match and clarity_match.group(1).upper() == "AMBIGUOUS":
        clarity = "ambiguous"

    return QuestionGateResult(scope=scope, clarity=clarity)


def classify_report_topic(
    question: str,
    *,
    settings: AnswerGenerationSettings,
    company_filters: list[str] | None = None,
) -> str:
    filter_context = ""
    if company_filters:
        filter_context = "\nSelected company filters: " + ", ".join(company_filters)

    response = request_chat_completion(
        messages=[
            {"role": "system", "content": REPORT_TOPIC_CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": question.strip() + filter_context},
        ],
        settings=settings,
        temperature=0.0,
        max_output_tokens=16,
    )

    normalized = response.strip().upper()
    if normalized.startswith("REPORT_TOPIC"):
        return "report_topic"
    if normalized.startswith("EXTERNAL"):
        return "external"
    return "external"


def classify_question_gate(
    question: str,
    *,
    settings: AnswerGenerationSettings,
    company_filters: list[str] | None = None,
) -> QuestionGateResult:
    filter_context = ""
    if company_filters:
        filter_context = "\nSelected company filters: " + ", ".join(company_filters)

    response = request_chat_completion(
        messages=[
            {"role": "system", "content": QUESTION_GATE_SYSTEM_PROMPT},
            {"role": "user", "content": question.strip() + filter_context},
        ],
        settings=settings,
        temperature=0.0,
        max_output_tokens=32,
    )

    result = parse_gate_response(response)
    if result.scope == "unsupported":
        if classify_report_topic(
            question,
            settings=settings,
            company_filters=company_filters,
        ) == "report_topic":
            return QuestionGateResult(scope="supported", clarity=result.clarity)
    return result


def classify_question_scope(
    question: str,
    *,
    settings: AnswerGenerationSettings,
    company_filters: list[str] | None = None,
) -> str:
    return classify_question_gate(
        question,
        settings=settings,
        company_filters=company_filters,
    ).scope


def classify_question_clarity(
    question: str,
    *,
    settings: AnswerGenerationSettings,
    company_filters: list[str] | None = None,
) -> str:
    return classify_question_gate(
        question,
        settings=settings,
        company_filters=company_filters,
    ).clarity
