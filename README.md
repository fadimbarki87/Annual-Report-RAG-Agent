# Annual Report RAG Agent

This project is a grounded Retrieval-Augmented Generation (RAG) system for answering questions from the 2024 annual reports of:

- Volkswagen Group
- Mercedes-Benz Group
- BMW Group
- Siemens AG
- Robert Bosch GmbH

The system extracts and normalizes report structure, builds retrieval-ready chunks, embeds them with Azure OpenAI, stores them in Qdrant Cloud, and answers user questions through a grounded agent with source traceability.

## End-to-End Architecture

```text
Annual report PDFs
-> Azure Document Intelligence layout extraction
-> conservative parsing / normalization
-> conservative chunking
-> Azure OpenAI embeddings
-> Qdrant Cloud vector storage
-> query embedding + retrieval
-> grounded answer generation
-> FastAPI backend
-> React frontend
```

## What The Project Does

- answers annual-report questions only from retrieved document evidence
- supports fact lookup, comparison, ranking, aggregation, and evidence-location questions
- returns grounded answers with exact evidence and page-level source references
- exposes the agent through a FastAPI API and a React web interface

## Ingestion Pipeline

The ingestion pipeline lives in:

```text
ingestion_pipeline/
```

Its job is to convert raw annual report PDFs into structured, retrieval-ready vectors.

### Steps

1. Azure Document Intelligence extracts pages, lines, tables, paragraphs, sections, and layout metadata from the PDFs.
2. Conservative parsing normalizes the raw Azure output into a stable JSON format without destructively removing document structure.
3. Conservative chunking creates retrieval-ready text and table chunks while preserving metadata such as page numbers, section titles, chunk order, and source file.
4. Azure OpenAI generates `text-embedding-3-large` vectors for every chunk.
5. Qdrant Cloud stores the final vectors and metadata in the `annual_report_chunks` collection.

### Ingestion Outputs

The pipeline currently covers five annual reports and stores:

- parsed annual report structures
- retrieval-ready text and table chunks
- chunk embeddings
- Qdrant Cloud vector records with metadata for filtering and citations

Key ingestion documentation:

- `ingestion_pipeline/INGESTION_PIPELINE_README.md`
- `ingestion_pipeline/parsing/AZURE_OUTPUT_NORMALIZATION.md`
- `ingestion_pipeline/chunking/CHUNKING_PIPELINE.md`
- `ingestion_pipeline/vector_storage/qdrant/QDRANT_STORAGE.md`

## Agent Pipeline

The agent pipeline lives in:

```text
agent_pipeline/
```

It contains the retrieval, grounded answer-generation, and evaluation layers.

### Retrieval Layer

The retrieval layer:

- embeds user questions with the same Azure OpenAI embedding model
- searches Qdrant Cloud
- supports company-aware retrieval across the five annual reports
- returns ranked chunks with source metadata such as company, PDF file, page number, and section title

Key retrieval documentation:

- `agent_pipeline/retrieval/RETRIEVAL_README.md`

### Answer-Generation Layer

The answer-generation layer:

- retrieves evidence candidates from Qdrant
- builds grounded context from those chunks
- uses Azure OpenAI chat completion to generate the answer
- returns answer, resources, and exact evidence
- refuses out-of-scope questions and fails safely when strong evidence is missing

Key answer-generation documentation:

- `agent_pipeline/answer_generation/ANSWER_GENERATION_README.md`

### Evaluation Layer

The evaluation layer measures:

- retrieval quality
- answer quality
- groundedness
- citation quality
- refusal behavior
- latency

Key evaluation documentation:

- `agent_pipeline/evaluation/RETRIEVAL_EVALUATION_METRICS.md`
- `agent_pipeline/evaluation/ANSWER_QUALITY_EVALUATION_METRICS.md`
- `agent_pipeline/evaluation/CATEGORY_RETRIEVAL_STRESS_EVALUATION_METRICS.md`
- `agent_pipeline/evaluation/CATEGORY_ANSWER_STRESS_EVALUATION_METRICS.md`

## API And UI

The project includes:

- a FastAPI backend in `api/`
- a React frontend in `ui/`

The frontend provides:

- a chat interface for grounded question answering
- curated example questions
- embedded original annual reports for source inspection

## Local Secrets

Real Azure OpenAI and Qdrant credentials are kept out of GitHub.

Ignored local config files include:

- `ingestion_pipeline/embeeding/azure_openai_config.json`
- `ingestion_pipeline/vector_storage/qdrant/qdrant_config.json`
- `agent_pipeline/answer_generation/answer_generation_config.json`

Only safe template files such as `*.template.json` are committed.

## Deployment

The project is prepared for:

- GitHub source control
- Render deployment for backend and frontend
- Azure OpenAI for embeddings and chat generation
- Qdrant Cloud for vector storage

Deployment notes:

- `GITHUB_RENDER_PREP.md`
- `api/README.md`
- `ui/README.md`

## Repository Structure

```text
rag_annual_reports/
  ingestion_pipeline/
  agent_pipeline/
  api/
  ui/
  requirements.txt
  README.md
```

## Status

Current implemented system:

- ingestion pipeline complete through Qdrant Cloud storage
- retrieval layer implemented and tested
- grounded answer generation implemented
- evaluation suite implemented
- FastAPI backend implemented
- React frontend implemented

Planned next step:

- deploy the application on Render
