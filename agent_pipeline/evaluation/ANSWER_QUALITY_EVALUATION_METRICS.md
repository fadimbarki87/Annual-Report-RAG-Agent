# Answer Quality Evaluation Metrics

This document explains the answer-quality benchmark written to `agent_pipeline/evaluation/data/answer_quality_evaluation.json`.

The benchmark uses the same curated dataset stored in `agent_pipeline/evaluation/data/benchmark_cases.json`.

## Benchmark Scope

Current answer evaluation covers `16` cases:

- `12` supported answer cases
- `2` unsupported cases
- `2` no-strong-answer cases

This benchmark tests:

- factual answers
- outlook answers
- table-based answers
- cross-company answers
- unsupported-question refusal
- no-evidence refusal

## Metrics Used

### Rule-Based Metrics

- `unsupported_refusal_accuracy`
  Exact-match accuracy for unsupported questions.
- `no_strong_answer_accuracy`
  Exact-match accuracy for questions that should return `No strong answer found in the provided documents.`
- `format_compliance_rule_rate`
  Share of supported answers that contain the required sections.
- `resource_presence_rule_rate`
  Share of supported answers where the expected company, source file, and page are present in the response.
- `mean_latency_seconds`
  Average answer-generation latency.
- `p95_latency_seconds`
  95th percentile answer-generation latency.

### LLM-Based Metrics

These are judged by an LLM evaluator against the question, gold answer, expected resources, and generated answer.

- `llm_correctness_mean`
  Whether the answer is semantically correct.
- `llm_groundedness_mean`
  Whether the answer is supported by its own evidence section.
- `llm_citation_accuracy_mean`
  Whether citations and resources align with the answer and expected sources.
- `llm_completeness_mean`
  Whether the answer covers the core requested information.
- `llm_format_compliance_mean`
  Whether the answer follows the requested response structure.
- `llm_answer_quality_mean`
  Mean of the LLM-judged answer-quality dimensions above.

## Current Results

Current benchmark summary:

- `case_count = 16`
- `supported_case_count = 12`
- `unsupported_case_count = 2`
- `no_strong_answer_case_count = 2`
- `mean_latency_seconds = 11.664`
- `p95_latency_seconds = 44.064`
- `unsupported_refusal_accuracy = 1.0`
- `no_strong_answer_accuracy = 1.0`
- `format_compliance_rule_rate = 1.0`
- `resource_presence_rule_rate = 0.916667`
- `llm_correctness_mean = 0.958333`
- `llm_groundedness_mean = 1.0`
- `llm_citation_accuracy_mean = 0.958333`
- `llm_completeness_mean = 0.958333`
- `llm_format_compliance_mean = 1.0`
- `llm_answer_quality_mean = 0.975`

## Interpretation

The current answer-generation results are strong in quality and strong in refusal behavior.

What the metrics say:

- unsupported questions are refused correctly
- no-evidence questions are refused correctly
- supported answers are consistently grounded in retrieved evidence
- supported answers are usually correct, complete, and well-cited
- the required response format is being followed

The strongest quality signal here is:

- `llm_groundedness_mean = 1.0`

That means the benchmarked answers were fully supported by their evidence according to the LLM judge.

Other strong signals:

- `llm_correctness_mean = 0.958333`
- `llm_citation_accuracy_mean = 0.958333`
- `llm_completeness_mean = 0.958333`
- `unsupported_refusal_accuracy = 1.0`
- `no_strong_answer_accuracy = 1.0`

## Main Remaining Weakness

The main weakness is latency variability:

- `mean_latency_seconds = 11.664`
- `p95_latency_seconds = 44.064`

This answer path currently includes:

- AI scope classification
- query embedding
- Qdrant retrieval
- final grounded answer generation

So the answer quality is strong, but latency is not yet deployment-optimized.

There is also a smaller citation issue:

- `resource_presence_rule_rate = 0.916667`

This means a few otherwise-correct answers cited extra pages or slightly different source pages than the benchmark expected.

## LLM-Based Evaluation Interpretation

The LLM-based metrics are useful, but they are not the same as human judgment.

They should be interpreted as:

- a structured quality signal
- helpful for comparing versions of the system
- not a final scientific truth

For this project, the LLM judge is especially useful for:

- groundedness
- citation quality
- completeness
- answer correctness

The LLM-based results are strong enough to support the claim that the system is producing high-quality grounded answers on this benchmark.

## Recommendation

The current recommendation is:

- keep the current retrieval and answer-generation architecture
- do not add a reranker yet
- improve latency next if deployment responsiveness matters
- expand the benchmark set over time, especially for harder comparison and multi-hop questions

## CV-Friendly Metrics

If you want headline answer-quality metrics for a project description, the strongest ones here are:

- `Groundedness = 1.00`
- `Correctness = 0.958`
- `Citation Accuracy = 0.958`
- `Refusal Accuracy (unsupported) = 1.00`
- `Refusal Accuracy (no strong answer) = 1.00`

