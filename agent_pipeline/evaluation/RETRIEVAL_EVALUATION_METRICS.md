# Retrieval Evaluation Metrics

This document explains the retrieval benchmark written to `agent_pipeline/evaluation/data/retrieval_quality_evaluation.json`.

The benchmark uses a small curated gold dataset stored in `agent_pipeline/evaluation/data/benchmark_cases.json`.

## Benchmark Scope

Retrieval evaluation currently covers `12` supported annual-report questions across:

- BMW Group
- Volkswagen Group
- Mercedes-Benz Group
- Siemens AG
- Robert Bosch GmbH

The benchmark includes:

- direct fact lookup
- outlook questions
- sustainability target questions
- table-based retrieval
- cross-company comparison retrieval

Each supported case includes one or more gold `relevant_chunk_ids`.

## Metrics Used

- `Hit@1`
  Whether at least one relevant chunk appears in the first result.
- `Hit@3`
  Whether at least one relevant chunk appears in the top 3.
- `Hit@5`
  Whether at least one relevant chunk appears in the top 5.
- `Hit@10`
  Whether at least one relevant chunk appears in the top 10.
- `Recall@1`
  Share of all relevant chunks recovered in the first result.
- `Recall@3`
  Share of all relevant chunks recovered in the top 3.
- `Recall@5`
  Share of all relevant chunks recovered in the top 5.
- `Recall@10`
  Share of all relevant chunks recovered in the top 10.
- `MRR@10`
  Mean reciprocal rank of the first relevant chunk in the top 10. Higher is better.
- `nDCG@10`
  Ranking quality within the top 10 with position discounting. Higher is better.
- `MAP@10`
  Mean average precision in the top 10. Higher is better.
- `mean_latency_seconds`
  Average end-to-end retrieval latency for the benchmark queries.
- `p95_latency_seconds`
  95th percentile retrieval latency. Useful for worst-case user experience.

## Current Results

Current benchmark summary:

- `case_count = 12`
- `search_limit = 10`
- `mean_latency_seconds = 2.241`
- `p95_latency_seconds = 5.676`
- `hit_at_1 = 0.916667`
- `recall_at_1 = 0.875`
- `hit_at_3 = 0.916667`
- `recall_at_3 = 0.916667`
- `hit_at_5 = 1.0`
- `recall_at_5 = 0.944444`
- `hit_at_10 = 1.0`
- `recall_at_10 = 0.972222`
- `mrr_at_10 = 0.9375`
- `ndcg_at_10 = 0.945846`
- `map_at_10 = 0.930556`

## Interpretation

These retrieval results are strong for a baseline vector-only RAG system.

What the metrics say:

- relevant evidence is always found within the top `5`
- relevant evidence is always found within the top `10`
- the first relevant chunk is usually ranked at or near the top
- table retrieval is working
- company filtering is working
- cross-company retrieval is working

The most important practical conclusion:

- retrieval is already good enough to continue without adding a reranker

Why that is a reasonable conclusion:

- `Hit@5 = 1.0`
- `Hit@10 = 1.0`
- `MRR@10 = 0.9375`
- `nDCG@10 = 0.945846`

This means the current retrieval stack is already finding the right material quickly and ranking it well.

## What Is Still Not Perfect

- `Hit@1` is not `1.0`, so the best chunk is not always first
- `Recall@1` is lower for questions with multiple relevant chunks
- a reranker could still improve the ordering of some comparison or multi-evidence questions

However, the current benchmark does not justify the extra complexity of a reranker yet.

## Recommendation

For this project, the current recommendation is:

- keep the existing Azure OpenAI embedding + Qdrant retrieval stack
- do not add a reranker yet
- only revisit reranking if future manual tests show that important evidence often lands in the top `10` but not in the top `3`

## CV-Friendly Metrics

If you want headline retrieval metrics for a project description, the strongest ones here are:

- `Hit@5 = 1.00`
- `Recall@10 = 0.972`
- `MRR@10 = 0.938`
- `nDCG@10 = 0.946`

