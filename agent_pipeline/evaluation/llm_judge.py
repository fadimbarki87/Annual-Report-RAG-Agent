from __future__ import annotations

import json
import re
from typing import Any

from agent_pipeline.answer_generation.azure_chat_client import request_chat_completion
from agent_pipeline.answer_generation.settings import AnswerGenerationSettings


JUDGE_SYSTEM_PROMPT = """You are a strict evaluator for a grounded annual-report RAG system.

You will receive:
- the user question
- the expected answer behavior
- a gold reference answer
- expected resources
- the generated answer

Evaluate the generated answer and return a JSON object only.

Score each field using only these values:
0.0, 0.5, 1.0

Fields:
- correctness: Is the answer semantically correct against the gold reference?
- groundedness: Are the answer's claims supported by the generated Evidence section?
- citation_accuracy: Are the Resources and Evidence aligned with the answer and expected resources?
- completeness: Does the answer cover the core requested information?
- format_compliance: Does the output follow the requested structure well enough?
- notes: one short sentence

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
    gold_answer: str,
    expected_resources: list[dict[str, Any]],
    generated_answer: str,
    settings: AnswerGenerationSettings,
) -> dict[str, Any]:
    prompt = {
        "question": question,
        "gold_answer": gold_answer,
        "expected_resources": expected_resources,
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
        "correctness": float(data.get("correctness", 0.0)),
        "groundedness": float(data.get("groundedness", 0.0)),
        "citation_accuracy": float(data.get("citation_accuracy", 0.0)),
        "completeness": float(data.get("completeness", 0.0)),
        "format_compliance": float(data.get("format_compliance", 0.0)),
        "notes": str(data.get("notes", "")).strip(),
    }

