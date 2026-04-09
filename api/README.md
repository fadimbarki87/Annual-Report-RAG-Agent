# API

This folder contains the minimal web API for the annual-report RAG agent.

It wraps the existing backend pipeline:

```text
POST /api/answer
-> agent_pipeline.answer_generation.answer_generator.answer_question()
-> retrieval
-> grounded answer generation
-> parsed JSON response for the UI
```

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Simple health check. |
| `GET /api/companies` | Returns the supported companies and document IDs. |
| `POST /api/answer` | Generates a grounded answer for the UI. |

## Request Body

```json
{
  "question": "What were BMW Group revenues in 2024?",
  "company_filters": [],
  "chunk_types": [],
  "retrieval_limit": 12
}
```

`company_filters`, `chunk_types`, and `retrieval_limit` are optional.

## Response Shape

```json
{
  "mode": "grounded_answer",
  "answer": "...",
  "reporting_period": "...",
  "resources": [],
  "evidence": [],
  "raw_response": "...",
  "duration_seconds": 4.218
}
```

Special refusal cases come back with `mode = "special_refusal"` and empty resources/evidence arrays.

## Run Locally

Install the API dependencies:

```powershell
cd C:\Users\hp\Downloads\rag_annual_reports
.\.venv\Scripts\python.exe -m pip install -r .\api\requirements.txt
```

Then start the server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.app:app --reload
```

The React UI can then call `http://localhost:8000/api/answer`.

## CORS

By default the API allows local Vite origins such as:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

You can override this with the environment variable:

```text
ANNUAL_REPORT_UI_ORIGINS
```

Use a comma-separated list of origins when you deploy.
