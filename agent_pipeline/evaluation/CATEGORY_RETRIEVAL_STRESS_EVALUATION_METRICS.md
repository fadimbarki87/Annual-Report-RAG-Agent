# Category Retrieval Stress Evaluation Metrics

This document explains the large retrieval stress benchmark written to [category_retrieval_stress_evaluation.json](C:/Users/hp/Downloads/rag_annual_reports/agent_pipeline/evaluation/data/category_retrieval_stress_evaluation.json).

The corresponding question bank is listed in [CATEGORY_QUESTION_BANK.md](C:/Users/hp/Downloads/rag_annual_reports/agent_pipeline/evaluation/CATEGORY_QUESTION_BANK.md) and stored as machine-readable data in [category_benchmark_cases.json](C:/Users/hp/Downloads/rag_annual_reports/agent_pipeline/evaluation/data/category_benchmark_cases.json).

## Benchmark Scope

This stress suite evaluates retrieval across:

- `30` question categories
- `150` total benchmark questions
- `130` supported retrieval cases used for retrieval scoring

The suite covers:

- simple lookup
- multi-value lookup
- comparison
- aggregation
- ranking
- derived metrics
- table questions
- evidence-location requests
- exact quote extraction
- narrative synthesis
- period-sensitive questions
- mixed and partial-data questions
- long-context questions

## Metrics Used

- `top1_expected_document_hit_rate`
  Whether the first retrieved chunk came from one of the expected report documents.
- `purity_at_5_mean`
  Share of top-5 retrieved chunks that belong to expected documents. Higher means less cross-company noise.
- `expected_document_recall_at_1`
  Fraction of expected documents represented in the first result.
- `expected_document_recall_at_3`
  Fraction of expected documents represented in the top 3.
- `expected_document_recall_at_5`
  Fraction of expected documents represented in the top 5.
- `expected_document_recall_at_10`
  Fraction of expected documents represented in the top 10.
- `expected_chunk_type_coverage_at_k`
  For questions that require a specific modality such as tables, this checks whether the needed chunk type appears within the top `k`.
- `mean_top_score`
  Average similarity score of the highest-ranked chunk returned by Qdrant.
- `mean_latency_seconds`
  Average retrieval latency for the stress suite.
- `p95_latency_seconds`
  95th percentile retrieval latency.

## Current Results

Overall stress-suite retrieval summary:

- `case_count = 130`
- `mean_latency_seconds = 6.112`
- `p95_latency_seconds = 22.024`
- `mean_top_score = 0.680933`
- `top1_expected_document_hit_rate = 1.0`
- `purity_at_5_mean = 1.0`
- `expected_document_recall_at_1_mean = 0.802820`
- `expected_document_recall_at_3_mean = 0.878205`
- `expected_document_recall_at_5_mean = 0.921795`
- `expected_document_recall_at_10_mean = 0.966923`
- `expected_chunk_type_coverage_at_3_mean = 0.75`
- `expected_chunk_type_coverage_at_5_mean = 0.75`
- `expected_chunk_type_coverage_at_10_mean = 0.75`

## Interpretation

These are strong results for a vector-only annual-report retriever.

What they mean in practice:

- the first returned chunk comes from the correct report set for every supported stress case
- the top 5 results stay clean, with `purity_at_5_mean = 1.0`
- by top 10, the retriever surfaces almost all expected report documents across multi-company questions
- table-sensitive retrieval works, but table/text cross-type coverage still has room to improve

The headline retrieval conclusion is:

- the current Azure OpenAI embedding + Qdrant setup is good enough to continue without a reranker

## Weak Areas

The main retrieval weaknesses are not basic fact lookup. They are harder categories such as:

- `Long Context Saturation`
  This category had `expected_document_recall_at_5_mean = 0.68`, showing that broad multi-company prompts can still drop some companies.
- `Ranking / Ordering`
  Retrieval is good, but multi-company coverage is not always complete in the top few results.
- `Cross-Type Retrieval`
  `expected_chunk_type_coverage_at_5_mean = 0.5` for that category, which means some text-plus-table questions still retrieve only one modality near the top.

## What These Metrics Do Not Measure

These metrics do not measure final answer correctness. They only measure whether the retriever finds the right documents and chunk types.

Final answer quality is measured separately in [CATEGORY_ANSWER_STRESS_EVALUATION_METRICS.md](C:/Users/hp/Downloads/rag_annual_reports/agent_pipeline/evaluation/CATEGORY_ANSWER_STRESS_EVALUATION_METRICS.md).

## CV-Friendly Retrieval Metrics

If you want concise headline retrieval metrics for your project description, the best ones from this stress suite are:

- `Top-1 expected document hit = 1.00`
- `Expected-document Recall@10 = 0.967`
- `Expected-document Recall@5 = 0.922`
- `Top-5 purity = 1.00`
- `Average retrieval latency ≈ 6.1 seconds`

Use these carefully: they describe the large stress-suite benchmark, not just a small hand-picked demo set.
