from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib import error, parse, request

from agent_pipeline.answer_generation.settings import AnswerGenerationSettings


MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3

logger = logging.getLogger(__name__)


def build_chat_url(settings: AnswerGenerationSettings) -> str:
    deployment = parse.quote(settings.chat_deployment, safe="")
    api_version = parse.quote(settings.api_version, safe="")
    return (
        f"{settings.endpoint}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )


def request_chat_completion(
    *,
    messages: list[dict[str, str]],
    settings: AnswerGenerationSettings,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> str:
    url = build_chat_url(settings)
    payload = json.dumps(
        {
            "messages": messages,
            "temperature": settings.temperature if temperature is None else temperature,
            "max_tokens": (
                settings.max_output_tokens
                if max_output_tokens is None
                else max_output_tokens
            ),
        }
    ).encode("utf-8")

    for attempt in range(1, MAX_RETRIES + 1):
        req = request.Request(
            url=url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "api-key": settings.api_key,
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=180) as response:
                body = response.read().decode("utf-8")
            result = json.loads(body)
            choices: list[dict[str, Any]] = result.get("choices", []) or []
            if not choices:
                raise ValueError("Azure OpenAI chat completion returned no choices.")
            message = choices[0].get("message") or {}
            content = str(message.get("content") or "").strip()
            if not content:
                raise ValueError("Azure OpenAI chat completion returned empty content.")
            return content
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Azure OpenAI answer generation failed with HTTP {exc.code}: "
                    f"{response_body}"
                ) from exc
            logger.warning(
                "Answer generation failed on attempt %s/%s with HTTP %s. "
                "Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                exc.code,
                RETRY_SLEEP_SECONDS,
            )
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            logger.warning(
                "Answer generation failed on attempt %s/%s. Retrying in %ss.",
                attempt,
                MAX_RETRIES,
                RETRY_SLEEP_SECONDS,
            )

        time.sleep(RETRY_SLEEP_SECONDS * attempt)

    raise RuntimeError("Answer generation failed unexpectedly.")
