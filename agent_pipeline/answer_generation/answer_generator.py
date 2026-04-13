from __future__ import annotations

import re

from agent_pipeline.answer_generation.azure_chat_client import request_chat_completion
from agent_pipeline.answer_generation.context_builder import build_context
from agent_pipeline.answer_generation.location_answerer import (
    answer_location_question,
    is_evidence_location_question,
)
from agent_pipeline.answer_generation.scope_guard import (
    NO_STRONG_ANSWER_RESPONSE,
    UNSUPPORTED_RESPONSE,
    classify_question_gate,
    classify_question_operation,
)
from agent_pipeline.answer_generation.settings import (
    AnswerGenerationSettings,
    load_answer_generation_settings,
)
from agent_pipeline.retrieval.document_registry import (
    detect_document_ids_in_text,
    document_info,
    resolve_document_ids,
)
from agent_pipeline.retrieval.retrieval_service import retrieve_chunks


SYSTEM_PROMPT = """You are an annual-report RAG answer writer.

Scope:
- Answer only from the retrieved evidence chunks.
- The only supported documents are the 2024 annual reports for Mercedes-Benz Group, BMW Group, Volkswagen Group, Siemens AG, and Robert Bosch GmbH.
- Never use external knowledge.
- Never guess missing values, relationships, reporting periods, or conclusions.
- If the question names specific companies, answer only for those companies and do not introduce any other company.
- If the question asks for a comparison, ranking, or computation across named companies, use only those named companies.

Refusal behavior:
- If the question is outside the annual-report scope, answer exactly: Unsupported: This question is outside the scope of the 2024 annual reports.
- If the question is in scope but the retrieved evidence is not enough, answer exactly: No strong answer found in the provided documents.
- If a computation is requested but key values are missing, answer exactly: I do not find sufficient data in the documents to compute this.
- If a question asks for multiple fields and only some are supported by the retrieved evidence, answer the supported parts and explicitly say which requested parts were not found.
- For trend questions, only answer trends explicitly stated in the retrieved evidence. Otherwise answer exactly: I only have data from the 2024 annual reports unless prior-year information is explicitly stated in them.

Output format:
Answer
- Direct and concise.
- Keep companies separated for multi-company answers.

Reporting Period
- Include only if relevant to financial values, comparisons, aggregations, or period-related questions.
- If not relevant, omit this section.

Resources
- Ordered by appearance in the answer.
- Include company, source file, and page number.
- Use one line per resource in the format: - Company, source_file.pdf, page 123

Evidence
- Exact text copied from the retrieved evidence.
- Include only evidence used in the answer.
- Do not paraphrase evidence.
- Use one line per evidence item in the format: - "Exact quote" (Company, source_file.pdf, page 123)
"""

def build_user_prompt(
    question: str,
    context: str,
    *,
    requested_company_names: list[str] | None = None,
    computation_guidance: str = "",
) -> str:
    company_scope = ""
    if requested_company_names:
        company_scope = (
            "\nRequested companies:\n"
            + ", ".join(requested_company_names)
            + "\nOnly answer for these companies unless a requested company is missing from the evidence."
        )
    return f"""Question:
{question}
{company_scope}
{computation_guidance}

Retrieved evidence chunks:
{context}

Write the answer using only the retrieved evidence chunks."""


def build_computation_guidance(operation: str) -> str:
    guidance: list[str] = []
    if operation == "aggregation":
        guidance.append(
            "Computation instruction:\n- Extract the requested company values from the evidence and compute the total explicitly.\n- Do not stop after listing the individual company values.\n- Include a final line in the Answer section in the form: - Total: <computed value>."
        )
    elif operation == "ranking":
        guidance.append(
            "Computation instruction:\n- Extract the requested company values from the evidence and rank only those requested companies from highest to lowest.\n- Include the ordered ranking explicitly in the Answer section."
        )
    elif operation == "comparison":
        guidance.append(
            "Computation instruction:\n- Compare only the requested companies.\n- State each requested company value clearly and identify which is higher when the evidence supports it."
        )

    if not guidance:
        return ""
    return "\n" + "\n".join(guidance)


def normalize_special_refusal(response: str) -> str:
    normalized = response.strip()
    exact_special_responses = {
        UNSUPPORTED_RESPONSE,
        NO_STRONG_ANSWER_RESPONSE,
        "I do not find sufficient data in the documents to compute this.",
        "I only have data from the 2024 annual reports unless prior-year information is explicitly stated in them.",
    }
    if normalized in exact_special_responses:
        return normalized

    match = re.fullmatch(
        r"Answer\s+(Unsupported: This question is outside the scope of the 2024 annual reports\.|No strong answer found in the provided documents\.|I do not find sufficient data in the documents to compute this\.|I only have data from the 2024 annual reports unless prior-year information is explicitly stated in them\.)",
        normalized,
        flags=re.DOTALL,
    )
    if match:
        return match.group(1).strip()

    special_response_patterns = [
        (
            NO_STRONG_ANSWER_RESPONSE,
            r"Answer\s+No strong answer found in the provided documents\.\s+Resources\s+None\s+Evidence\s+None",
        ),
        (
            UNSUPPORTED_RESPONSE,
            r"Answer\s+Unsupported: This question is outside the scope of the 2024 annual reports\.\s+Resources\s+None\s+Evidence\s+None",
        ),
    ]
    for special_response, pattern in special_response_patterns:
        if re.fullmatch(pattern, normalized, flags=re.DOTALL):
            return special_response

    if re.fullmatch(
        r"Answer\s+.*(does not provide|do not provide|not provide|not provided|no information|no explicit|not find).*\s+Resources\s+None\s+Evidence\s+None",
        normalized,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        return NO_STRONG_ANSWER_RESPONSE

    if re.fullmatch(
        r"Answer\s+.*No strong answer found in the provided documents\.\s+Resources\s+None\s+Evidence\s+None",
        normalized,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        return NO_STRONG_ANSWER_RESPONSE

    return response


def has_strong_retrieval(
    retrieved_scores: list[float],
    *,
    minimum_top_score: float,
) -> bool:
    if not retrieved_scores:
        return False
    return max(retrieved_scores) >= minimum_top_score


def answer_question(
    *,
    question: str,
    company_filters: list[str] | None = None,
    chunk_types: list[str] | None = None,
    retrieval_limit: int | None = None,
    settings: AnswerGenerationSettings | None = None,
) -> str:
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty.")

    settings = settings or load_answer_generation_settings()

    question_gate = classify_question_gate(
        question,
        settings=settings,
        company_filters=company_filters,
    )
    if question_gate.scope == "unsupported":
        return UNSUPPORTED_RESPONSE

    if question_gate.clarity == "ambiguous":
        return NO_STRONG_ANSWER_RESPONSE

    explicit_company_filters = [
        value for value in (company_filters or []) if value and value.strip()
    ]
    inferred_document_ids = (
        detect_document_ids_in_text(question) if not explicit_company_filters else []
    )
    requested_document_ids = (
        resolve_document_ids(explicit_company_filters)
        if explicit_company_filters
        else inferred_document_ids
    )
    requested_company_names = [
        document.company_name
        for document_id in requested_document_ids
        if (document := document_info(document_id)) is not None
    ]
    is_location_question = is_evidence_location_question(question)
    question_operation = classify_question_operation(
        question,
        settings=settings,
        company_filters=company_filters,
    )
    is_computation_question = question_operation in {
        "aggregation",
        "ranking",
        "comparison",
    }
    effective_retrieval_limit = retrieval_limit or settings.retrieval_limit
    if is_location_question:
        effective_retrieval_limit = max(effective_retrieval_limit, 20)
    if is_computation_question and len(requested_document_ids) > 1:
        effective_retrieval_limit = max(effective_retrieval_limit, 20)

    chunks = retrieve_chunks(
        query=question,
        company_filters=explicit_company_filters,
        document_ids=requested_document_ids,
        chunk_types=chunk_types,
        limit=effective_retrieval_limit,
        balance_across_documents=len(requested_document_ids) > 1,
    )
    scores = [chunk.score for chunk in chunks]
    if not has_strong_retrieval(scores, minimum_top_score=settings.minimum_top_score):
        return NO_STRONG_ANSWER_RESPONSE

    if is_location_question:
        location_response = answer_location_question(
            question,
            chunks,
            settings=settings,
        )
        normalized_location_response = normalize_special_refusal(location_response)
        if question_gate.scope == "supported" and normalized_location_response == UNSUPPORTED_RESPONSE:
            return NO_STRONG_ANSWER_RESPONSE
        return normalized_location_response

    context = build_context(
        chunks,
        max_context_characters=settings.max_context_characters,
        max_chunk_characters=settings.max_chunk_characters,
    )
    if not context.strip():
        return NO_STRONG_ANSWER_RESPONSE

    response = request_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(
                    question,
                    context,
                    requested_company_names=requested_company_names,
                    computation_guidance=build_computation_guidance(
                        question_operation
                    ),
                ),
            },
        ],
        settings=settings,
    )
    normalized_response = normalize_special_refusal(response)
    if question_gate.scope == "supported" and normalized_response == UNSUPPORTED_RESPONSE:
        return NO_STRONG_ANSWER_RESPONSE
    return normalized_response
