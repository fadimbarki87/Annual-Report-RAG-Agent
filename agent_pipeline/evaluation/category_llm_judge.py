from __future__ import annotations

import json
import re
from typing import Any

from agent_pipeline.answer_generation.azure_chat_client import request_chat_completion
from agent_pipeline.answer_generation.settings import AnswerGenerationSettings


JUDGE_SYSTEM_PROMPT = """You are a strict evaluator for a grounded annual-report RAG stress test.

You will receive:
- the user question
- the expected behavior type
- expected company/document scope
- the generated answer

Evaluate the generated answer and return a JSON object only.

For supported questions, score each field using only these values:
0.0, 0.5, 1.0

Fields:
- relevance: Does the answer address the requested question?
- groundedness: Are the answer's claims supported by the generated Evidence section?
- citation_accuracy: Are the Resources and Evidence aligned with the answer?
- completeness: Does the answer cover the core requested information, while acknowledging any missing subparts when needed?
- instruction_following: Does the answer follow the requested answer format and constraints?
- notes: one short sentence

Important:
- Do not reward fabricated claims.
- If the answer refuses instead of answering a clearly supported question, score harshly.
- If the answer partially answers a multi-part question and clearly states which requested parts were not found, that can still receive partial credit.

Return only valid JSON with these exact keys.
"""


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Judge response did not contain valid JSON.")


def judge_supported_answer(
    *,
    question: str,
    expected_document_ids: list[str],
    generated_answer: str,
    settings: AnswerGenerationSettings,
) -> dict[str, Any]:
    prompt = {
        "question": question,
        "expected_behavior": "supported",
        "expected_document_ids": expected_document_ids,
        "generated_answer": generated_answer,
    }

    response = request_chat_completion(
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, indent=2)},
        ],
        settings=settings,
        temperature=0.0,
        max_output_tokens=250,
    )
    data = extract_json_object(response)

    return {
        "relevance": float(data.get("relevance", 0.0)),
        "groundedness": float(data.get("groundedness", 0.0)),
        "citation_accuracy": float(data.get("citation_accuracy", 0.0)),
        "completeness": float(data.get("completeness", 0.0)),
        "instruction_following": float(data.get("instruction_following", 0.0)),
        "notes": str(data.get("notes", "")).strip(),
    }
