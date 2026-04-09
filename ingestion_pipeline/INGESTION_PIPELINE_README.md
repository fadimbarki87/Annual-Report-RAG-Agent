# Ingestion Pipeline Overview

This document explains the end-to-end ingestion pipeline built for the annual reports RAG project.

The current pipeline takes annual report PDFs through these stages:

```text
PDFs
-> Azure Document Intelligence raw layout output
-> conservative parsing / normalization
-> conservative chunking
-> Azure OpenAI embeddings
-> Qdrant Cloud vector storage
```

The goal is to produce retrieval-ready chunks with strong source traceability, so a later RAG agent can answer questions from the annual reports with citations.

## 1. Azure Document Intelligence

The first stage uses Azure Document Intelligence with the `prebuilt-layout` model.

Azure Document Intelligence extracts layout information from the PDFs, including:

- pages
- lines
- tables
- paragraphs
- sections
- styles
- figures
- bounding regions and polygons

The raw Azure outputs are stored here:

```text
ingestion_pipeline/parsing/data/raw_azure
```

These files are treated as the source layout extraction layer. The rest of the ingestion pipeline is built on top of them.

## 2. Conservative Parsing / Normalization

The parsing stage is implemented here:

```text
ingestion_pipeline/parsing/normalize_azure_output.py
```

Its output is stored here:

```text
ingestion_pipeline/parsing/data/processed
```

The detailed parsing documentation is here:

```text
ingestion_pipeline/parsing/AZURE_OUTPUT_NORMALIZATION.md
```

### What Conservative Parsing Means

The parser does not try to aggressively rewrite or clean the document.

Instead, it safely normalizes Azure's raw layout output into a stable internal JSON format. The design is conservative because annual reports are complex: they contain covers, repeated headers, tables, footnotes, charts, page numbers, and mixed layouts.

The parser does the following:

- reads raw Azure JSON files
- finds the Azure result root under `result`, `analyzeResult`, or the JSON root
- extracts document metadata such as `source_file`, `model_id`, page count, table count, API version, content format, and string index type
- converts Azure page lines into normalized line records
- preserves line text, polygon coordinates, and derived bounds (`left`, `right`, `top`, `bottom`)
- creates `raw_lines` and `clean_lines`
- keeps `clean_lines` as a copy of `raw_lines`
- keeps `removed_lines` empty
- maps Azure tables to the pages where they appear using `boundingRegions`
- assigns a simple page type such as `text`, `mixed`, `visual_or_table`, or `visual_or_cover`
- detects repeated header/footer candidates near page margins
- flags repeated header/footer candidates without deleting them
- preserves optional Azure structures: `paragraphs`, `sections`, `styles`, and `figures`

This is intentionally non-destructive. The parser marks potential noise but does not remove content from the document.

## 3. Parsing Evaluation

The parsing evaluation script is:

```text
ingestion_pipeline/parsing/evaluate_parsing_quality.py
```

The metrics output is:

```text
ingestion_pipeline/parsing/data/processed/parsing_quality_evaluation.json
```

The metric interpretation document is:

```text
ingestion_pipeline/parsing/PARSING_EVALUATION_METRICS.md
```

The parsing evaluation compares processed files against:

- raw Azure output, for preservation checks
- source PDF text, as a silver text reference

Important result:

```text
Parsing preservation metrics are 1.0 across page, line, table, paragraph, section, style, and figure preservation.
```

This means the normalization layer did not drop the measured Azure structures.

## 4. Conservative Chunking

The chunking stage is implemented here:

```text
ingestion_pipeline/chunking/conservative_chunker.py
```

The output chunks are stored here:

```text
ingestion_pipeline/chunking/data/chunks
```

The detailed chunking documentation is here:

```text
ingestion_pipeline/chunking/CHUNKING_PIPELINE.md
```

### What Conservative Chunking Means

The chunker turns processed documents into retrieval-ready chunks without trying to overfit one company's layout.

The chunker does the following:

- reads only real `*_processed.json` files
- skips evaluation JSON files
- uses Azure paragraphs when they are usable
- falls back to cleaned line groups when paragraph structure is weak
- keeps text chunks within the same page
- keeps tables separate from normal narrative text chunks
- avoids table text leaking into normal text chunks using table bounding regions
- carries forward source metadata such as source file, model ID, page numbers, page types, and section titles
- uses conservative chunk size targets around `800` to `1500` characters
- splits oversized text at sentence or punctuation boundaries when possible
- applies a narrow anti-fragmentation pass to merge only safe adjacent same-page small chunks

The chunker stores each chunk with metadata like:

```text
chunk_id
chunk_index
source_file
model_id
chunk_type
content_source
page_numbers
page_start
page_end
page_types
section_titles
text
char_count
line_count
table_count
paragraph_count
table_metadata
```

The `chunk_index` preserves document order. That means adjacent source content generally remains adjacent in chunk order, assuming Azure's reading order was correct.

## 5. Chunking Evaluation

The chunking evaluation script is:

```text
ingestion_pipeline/chunking/evaluate_chunking_quality.py
```

The metrics output is:

```text
ingestion_pipeline/chunking/data/chunks/chunking_quality_evaluation.json
```

The metric interpretation document is:

```text
ingestion_pipeline/chunking/CHUNKING_EVALUATION_METRICS.md
```

Important results:

```text
page_coverage_rate = 1.0
table_coverage_rate = 1.0
chunk_token_precision = 0.997718
chunk_token_f1 = 0.893005
heading_coverage_rate = 0.989035
small_text_chunk_rate_chars_lt_400 = 0.163433
```

Interpretation:

- all pages are covered
- all tables are covered
- chunks are highly precise against source processed text
- headings are mostly preserved as metadata
- small chunks remain the main known weakness, but the issue was improved with a conservative anti-fragmentation merge

This makes the chunk output ready for baseline retrieval experiments.

## 6. Azure OpenAI Embeddings

The embedding stage is implemented here:

```text
ingestion_pipeline/embeeding/azure_openai_embed_chunks.py
```

The project currently uses the folder name `embeeding` because that was the chosen project folder name earlier.

The embedding config template is:

```text
ingestion_pipeline/embeeding/azure_openai_config.template.json
```

The private local config is:

```text
ingestion_pipeline/embeeding/azure_openai_config.json
```

The private config is ignored by Git because it contains secrets.

The embedding output is stored here:

```text
ingestion_pipeline/embeeding/data/embeddings
```

The embedding stage uses Azure OpenAI with:

```text
text-embedding-3-large
```

This produces:

```text
3072-dimensional vectors
```

For each annual report, the embedding stage writes:

```text
manifest.json
<document_id>_embeddings.jsonl
```

Each JSONL row contains:

- the chunk ID
- the embedding vector
- the chunk text
- source metadata needed for filtering and citations

## 7. Embedding Evaluation

The embedding evaluation script is:

```text
ingestion_pipeline/embeeding/evaluate_embedding_quality.py
```

The metrics output is:

```text
ingestion_pipeline/embeeding/data/embeddings/embedding_quality_evaluation.json
```

The metric interpretation document is:

```text
ingestion_pipeline/embeeding/EMBEDDING_EVALUATION_METRICS.md
```

Important results:

```text
source_chunk_count = 7426
embedded_record_count = 7426
embedding_coverage_rate = 1.0
missing_embedding_count = 0
extra_embedding_count = 0
duplicate_embedding_id_count = 0
payload_text_exact_match_rate = 1.0
payload_metadata_match_rate = 1.0
table_records_with_metadata = 1495
table_metadata_presence_rate = 1.0
nonempty_vector_rate = 1.0
finite_vector_rate = 1.0
nonzero_vector_rate = 1.0
vector_dimension = 3072
vector_dimension_consistency_rate = 1.0
```

Interpretation:

- every chunk has an embedding
- every vector is valid
- all embedding payloads match the source chunks
- table chunk payloads include `table_metadata`
- embeddings are ready for vector storage

## 8. Qdrant Cloud Vector Storage

The Qdrant storage stage is implemented here:

```text
ingestion_pipeline/vector_storage/qdrant/upsert_embeddings_to_qdrant.py
```

The Qdrant config template is:

```text
ingestion_pipeline/vector_storage/qdrant/qdrant_config.template.json
```

The private local config is:

```text
ingestion_pipeline/vector_storage/qdrant/qdrant_config.json
```

The Qdrant storage documentation is:

```text
ingestion_pipeline/vector_storage/qdrant/QDRANT_STORAGE.md
```

The project uses Qdrant Cloud free tier from the beginning because the final RAG website is intended to run online through Render.

The Qdrant collection is:

```text
annual_report_chunks
```

The collection uses:

```text
vector size: 3072
distance: Cosine
```

This matches the Azure OpenAI `text-embedding-3-large` vectors.

The Qdrant upsert summary is stored here:

```text
ingestion_pipeline/vector_storage/qdrant/data/qdrant_upsert_summary.json
```

Important result:

```text
documents_upserted = 5
points_upserted = 7426
collection_points_count_after_upsert = 7426
collection_count_matches_upserted_points = true
```

Interpretation:

- all embedded chunks were uploaded to Qdrant Cloud
- Qdrant's final collection point count matches the expected number of embeddings
- the vector database is ready for retrieval testing

## Current State

The ingestion pipeline is complete through vector storage.

The current completed stages are:

```text
Azure Document Intelligence raw extraction
-> parsing / normalization
-> parsing evaluation
-> chunking
-> chunking evaluation
-> Azure OpenAI embeddings
-> embedding evaluation
-> Qdrant Cloud storage
```

The next stage is retrieval.

We should not jump directly into a full agent until retrieval works. The correct next sequence is:

1. build a retrieval script
2. embed a user query
3. search Qdrant
4. return top chunks with document ID, page numbers, section titles, and text
5. test company-specific queries
6. test cross-company comparison queries
7. then build the RAG answer agent

## Retrieval Behavior We Are Preparing For

The Qdrant payload contains metadata such as:

```text
document_id
source_file
chunk_id
chunk_index
chunk_type
page_numbers
section_titles
text
```

This means later retrieval can support:

- BMW-only questions using `document_id = bmw_2024`
- Volkswagen-only questions using `document_id = volkswagen_2024`
- cross-company comparison by searching multiple document IDs
- citations using page numbers and source files
- neighbor expansion using `chunk_index`

Qdrant retrieves chunks. The later RAG agent will use those chunks to generate answers.

## What Is Not Done Yet

The following stages are not implemented yet:

- query embedding
- Qdrant retrieval script
- retrieval evaluation with `Recall@k`, `MRR`, `nDCG@k`, or `Hit@k`
- PII redaction
- answer generation
- RAG agent
- web app / Render deployment

The next planned step is to work on retrieval and PII redaction step by step.
