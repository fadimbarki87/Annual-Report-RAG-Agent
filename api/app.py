from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent_pipeline.answer_generation.answer_generator import answer_question
from agent_pipeline.retrieval.document_registry import DOCUMENTS
from api.response_parser import parse_answer_response


def allowed_origins() -> list[str]:
    configured = os.environ.get("ANNUAL_REPORT_UI_ORIGINS", "").strip()
    if configured:
        return [value.strip() for value in configured.split(",") if value.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]


class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question for the RAG agent.")
    company_filters: list[str] = Field(default_factory=list)
    chunk_types: list[str] = Field(default_factory=list)
    retrieval_limit: int | None = Field(default=None, ge=1, le=50)


class ResourceItem(BaseModel):
    company: str = ""
    source_file: str = ""
    page_number: int | str | None = None
    raw: str = ""


class EvidenceItem(BaseModel):
    text: str
    page_number: int | str | None = None
    company: str = ""
    source_file: str = ""
    raw: str = ""


class AnswerResponse(BaseModel):
    mode: str
    answer: str
    reporting_period: str | None = None
    resources: list[ResourceItem] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    raw_response: str
    duration_seconds: float


app = FastAPI(
    title="Annual Report RAG API",
    version="0.1.0",
    description="API wrapper around the annual-report grounded answer generator.",
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "ingestion_pipeline" / "parsing" / "data" / "pdfs"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if REPORTS_DIR.exists():
    app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/companies")
def list_companies() -> dict[str, list[dict[str, Any]]]:
    return {
        "companies": [
            {
                "document_id": document.document_id,
                "company_name": document.company_name,
                "source_file": document.source_file,
                "aliases": list(document.aliases),
            }
            for document in DOCUMENTS.values()
        ]
    }


@app.post("/api/answer", response_model=AnswerResponse)
def create_answer(payload: AnswerRequest) -> AnswerResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    started_at = time.perf_counter()
    try:
        raw_response = answer_question(
            question=question,
            company_filters=payload.company_filters,
            chunk_types=payload.chunk_types,
            retrieval_limit=payload.retrieval_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {exc}") from exc

    parsed = parse_answer_response(raw_response)
    return AnswerResponse(
        **parsed,
        duration_seconds=round(time.perf_counter() - started_at, 3),
    )
