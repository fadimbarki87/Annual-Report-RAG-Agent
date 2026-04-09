# Retrieval Foundation

This folder contains the first agent-pipeline layer: query-time retrieval.

It does not generate final answers. It only:

- embeds a user query with the existing Azure OpenAI embedding deployment
- searches the existing Qdrant Cloud collection
- applies optional company and chunk-type filters
- prints retrieved chunks with scores, source files, page numbers, section titles, and exact text previews

The purpose is to verify that retrieval finds the right evidence before building the final RAG agent.

## Inputs

The retrieval layer reuses the existing ingestion configuration files:

- Azure OpenAI embeddings: `ingestion_pipeline/embeeding/azure_openai_config.json`
- Qdrant Cloud: `ingestion_pipeline/vector_storage/qdrant/qdrant_config.json`

It expects Qdrant to contain the `annual_report_chunks` collection populated from the embedding JSONL files.

## How The Files Work Together

Retrieval runs in this order:

```text
retrieve_chunks.py
-> document_registry.py
-> settings.py
-> azure_query_embedder.py
-> qdrant_retriever.py
-> retrieval_service.py returns ranked chunks
-> retrieve_chunks.py prints the retrieved evidence candidates
```

The user-facing entry point is `retrieve_chunks.py`. It parses the terminal command, resolves company filters, calls the retrieval service, and prints the retrieved chunks. It does not answer the question.

`retrieval_service.py` is the orchestration layer. It receives the query and filters, embeds the query with Azure OpenAI, searches Qdrant, and returns ranked `RetrievedChunk` objects.

`document_registry.py` stores the supported annual reports and company aliases. This is where `bmw`, `volkswagen`, `vw`, `bosch`, `mercedes`, and `siemens` are mapped to document IDs like `bmw_2024` and `volkswagen_2024`.

`settings.py` loads the existing Azure OpenAI and Qdrant configs from the ingestion pipeline. This avoids copying secrets or duplicating config files inside the agent pipeline.

`azure_query_embedder.py` turns the user query into a vector using the same Azure OpenAI embedding deployment used during ingestion.

`qdrant_retriever.py` sends the query vector to Qdrant Cloud, applies filters such as `document_id` and `chunk_type`, and converts the response into typed retrieval results.

`__init__.py` marks the folder as a Python package so the retrieval modules can import each other cleanly.

## File Responsibilities

| File | Responsibility |
| --- | --- |
| `retrieve_chunks.py` | CLI test script for running retrieval from the terminal. |
| `evaluate_baseline_retrieval.py` | Diagnostic benchmark for checking whether baseline retrieval finds expected evidence. |
| `retrieval_service.py` | Coordinates query embedding and Qdrant search. |
| `document_registry.py` | Maps company aliases to document IDs and source files. |
| `settings.py` | Loads Azure OpenAI and Qdrant settings from existing config files. |
| `azure_query_embedder.py` | Calls Azure OpenAI to embed a user query. |
| `qdrant_retriever.py` | Calls Qdrant Cloud and returns ranked chunks. |
| `RETRIEVAL_README.md` | Explains this retrieval layer. |
| `__init__.py` | Keeps the retrieval folder importable as a package. |

## Company Filters

The registry supports:

- `bmw`
- `bosch`
- `mercedes`
- `siemens`
- `volkswagen`
- `vw`

If no company is supplied, retrieval searches all documents.

## Run Examples

From the project root:

```powershell
python .\agent_pipeline\retrieval\retrieve_chunks.py "What does Volkswagen expect for 2025?" --company volkswagen --limit 5
```

```powershell
python .\agent_pipeline\retrieval\retrieve_chunks.py "What was BMW revenue in 2024?" --company bmw --limit 5
```

```powershell
python .\agent_pipeline\retrieval\retrieve_chunks.py "Compare BMW and Volkswagen outlook for 2025" --company bmw --company volkswagen --limit 8
```

For table-only retrieval:

```powershell
python .\agent_pipeline\retrieval\retrieve_chunks.py "cash flow statement 2024" --company bosch --chunk-type table --limit 5
```

## Baseline Retrieval Diagnostic

Before adding a reranker, run the baseline diagnostic:

```powershell
python .\agent_pipeline\retrieval\evaluate_baseline_retrieval.py
```

This runs curated annual-report queries against the current Azure OpenAI + Qdrant retrieval stack and saves the output to:

```text
agent_pipeline/retrieval/data/baseline_retrieval_diagnostics.json
```

Current diagnostic result:

- `case_count = 12`
- `mean_latency_seconds = 1.663`
- `max_latency_seconds = 2.97`
- `hit_at_1_rate = 0.75`
- `hit_at_3_rate = 0.9166666666666666`
- `hit_at_5_rate = 0.9166666666666666`
- `hit_at_10_rate = 1.0`
- `hit_at_20_rate = 1.0`
- `missed_case_ids = []`

Interpretation:

- baseline retrieval is already strong enough to continue without a reranker
- the main reason to add a reranker later would be if manual tests show the right evidence often appears in top 10-20 but not top 3-5
- for now, keeping retrieval simple is better than adding a heavy model dependency

## What Is Not Implemented Yet

This is intentionally not the full agent. The following are still later stages:

- final answer generation
- numeric computation layer
- unsupported/not-found refusal layer
- reranking
- PII redaction
- voice input
- web API
- UI

This keeps the next step focused: prove that Qdrant retrieves the right chunks first.
