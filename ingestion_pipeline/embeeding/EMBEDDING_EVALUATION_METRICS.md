# Embedding Evaluation Metrics

This document explains the embedding evaluation written to [embedding_quality_evaluation.json](data/embeddings/embedding_quality_evaluation.json).

The JSON file stores metrics only. Explanations and interpretation live in this document.

## What Was Evaluated

The embedding layer was evaluated against the chunk files, not against the original PDFs.

That is the correct reference for this stage because the embedding script embeds chunk text. The goal is to verify that every retrieval chunk has exactly one valid embedding and that the payload metadata stored beside the vector still matches the source chunk.

The original PDFs are useful for parsing evaluation. They are not the right direct reference for embedding artifact validation, because embeddings are generated from chunks, not directly from PDF pages.

## Metrics Used

- `source_chunk_count`
  Number of non-empty source chunks expected to be embedded.
- `embedded_record_count`
  Number of embedding records written to JSONL.
- `unique_embedded_id_count`
  Number of unique embedded chunk IDs.
- `embedding_coverage_rate`
  Share of expected chunks that have an embedding. `1.0` means every expected chunk was embedded.
- `missing_embedding_count`
  Number of chunks that should have embeddings but do not.
- `extra_embedding_count`
  Number of embedding records that do not map back to a source chunk.
- `duplicate_embedding_id_count`
  Number of repeated embedding IDs.
- `manifest_count_matches_jsonl_rate`
  Whether the manifest count agrees with the number of records in the embedding JSONL.
- `id_payload_match_rate`
  Share of records where the top-level embedding ID matches `payload.chunk_id`.
- `payload_text_exact_match_rate`
  Share of records where `payload.text` exactly matches the original chunk text.
- `payload_metadata_match_rate`
  Share of records where the stored payload metadata, including `table_metadata`, matches the original chunk metadata.
- `required_payload_field_presence_rate`
  Share of expected payload metadata fields present in embedding records.
- `nonempty_vector_rate`
  Share of records with a non-empty vector.
- `finite_vector_rate`
  Share of records where all vector values are valid finite numbers.
- `nonzero_vector_rate`
  Share of records where the vector norm is greater than zero.
- `vector_dimension`
  Embedding vector dimension reported by the manifest.
- `vector_dimension_consistency_rate`
  Share of records whose vector length matches the manifest dimension.
- `vector_norm_min`, `vector_norm_max`, `vector_norm_mean_macro`
  Basic vector norm checks. For this run, vectors are unit-normalized.

## Current Results

Overall metrics:

| Metric | Value |
| --- | ---: |
| `document_count` | `5` |
| `source_chunk_count` | `7426` |
| `embedded_record_count` | `7426` |
| `unique_embedded_id_count` | `7426` |
| `embedding_coverage_rate` | `1.0` |
| `missing_embedding_count` | `0` |
| `extra_embedding_count` | `0` |
| `duplicate_embedding_id_count` | `0` |
| `manifest_count_matches_jsonl_rate` | `1.0` |
| `id_payload_match_rate` | `1.0` |
| `payload_text_exact_match_rate` | `1.0` |
| `payload_metadata_match_rate` | `1.0` |
| `table_records_with_metadata` | `1495` |
| `table_metadata_presence_rate` | `1.0` |
| `required_payload_field_presence_rate` | `1.0` |
| `nonempty_vector_rate` | `1.0` |
| `finite_vector_rate` | `1.0` |
| `nonzero_vector_rate` | `1.0` |
| `vector_dimension` | `3072` |
| `vector_dimension_consistency_rate` | `1.0` |

Per document:

| Document | Source Chunks | Embedded Records | Coverage | Vector Dimension |
| --- | ---: | ---: | ---: | ---: |
| `bmw_2024` | `1834` | `1834` | `1.0` | `3072` |
| `bosch_2024` | `617` | `617` | `1.0` | `3072` |
| `mercedes_2024` | `1548` | `1548` | `1.0` | `3072` |
| `siemens_2024` | `1002` | `1002` | `1.0` | `3072` |
| `volkswagen_2024` | `2425` | `2425` | `1.0` | `3072` |

## What These Results Mean

The embedding artifact generation worked correctly.

Every expected chunk has an embedding, there are no missing or duplicate embedding IDs, and every embedding payload matches the source chunk text and metadata. The vectors are valid, non-empty, finite, nonzero, and dimensionally consistent.

Table chunk payloads also include `table_metadata`, so row ranges and table shape metadata are available downstream in Qdrant.

This means the embedding files are ready for vector database storage.

## Qdrant Readiness

The embeddings are ready to be inserted into Qdrant.

For Qdrant, each record already has the two things we need:

- `vector`
  The 3072-dimensional embedding from `text-embedding-3-large`.
- `payload`
  The chunk text and metadata needed for filtering, citations, and answer grounding.

The next step is to create a Qdrant collection with vector size `3072` and upsert these embedding records.

## What Is Not Measured Yet

These metrics do not prove final search or answer quality.

They prove that the embedding artifacts were generated correctly from chunks. Final retrieval quality still needs query-level evaluation after Qdrant retrieval is implemented, using metrics such as:

- `Recall@k`
- `MRR`
- `nDCG@k`
- `Hit@k`
- answer faithfulness
- answer correctness
