# Category Answer Stress Evaluation Metrics

This document explains the large answer-quality stress benchmark written to [category_answer_stress_evaluation.json](C:/Users/hp/Downloads/rag_annual_reports/agent_pipeline/evaluation/data/category_answer_stress_evaluation.json).

The benchmark questions come from [CATEGORY_QUESTION_BANK.md](C:/Users/hp/Downloads/rag_annual_reports/agent_pipeline/evaluation/CATEGORY_QUESTION_BANK.md).

## Benchmark Scope

This answer benchmark uses:

- `30` categories
- `150` total questions
- `130` supported answer cases
- `14` in-scope `no strong answer` cases
- `6` out-of-scope refusal cases

It evaluates both:

- rule-based behavior for refusal and format
- LLM-based judgment for supported answers

## Rule-Based Metrics

- `unsupported_refusal_accuracy`
  Exact-match accuracy for the required unsupported response:
  `Unsupported: This question is outside the scope of the 2024 annual reports.`
- `no_strong_answer_accuracy`
  Exact-match accuracy for the required in-scope failure response:
  `No strong answer found in the provided documents.`
- `supported_format_compliance_rate`
  Whether supported answers follow the required structure with `Answer`, `Resources`, and `Evidence`.
- `supported_resource_presence_rate`
  Whether supported answers include non-empty resources and evidence sections.
- `supported_expected_document_presence_rate`
  Whether supported answers mention the expected company/document source information.
- `supported_nonrefusal_rate`
  Whether supported questions actually receive a substantive answer rather than a refusal.

## LLM-Based Metrics

The LLM judge is only used for supported cases.

- `llm_relevance`
  Does the answer actually address the user’s question?
- `llm_groundedness`
  Are the answer’s claims supported by the cited evidence instead of invented?
- `llm_citation_accuracy`
  Do the cited resources and evidence match the answer content?
- `llm_completeness`
  Does the answer cover the important parts of the request?
- `llm_instruction_following`
  Does the answer follow the required output behavior and constraints?
- `llm_answer_quality_mean`
  Mean of the five LLM-judge dimensions above.

Important note:

- these LLM-based scores are useful quality signals, not absolute ground truth
- refusal behavior is judged with exact-match rules, not LLM opinions

## Current Results

Overall answer stress-suite summary:

- `case_count = 150`
- `supported_case_count = 130`
- `unsupported_case_count = 6`
- `no_strong_answer_case_count = 14`
- `mean_latency_seconds = 18.102`
- `p95_latency_seconds = 34.601`
- `unsupported_refusal_accuracy = 1.0`
- `no_strong_answer_accuracy = 0.785714`
- `supported_format_compliance_rate = 0.961538`
- `supported_resource_presence_rate = 0.961538`
- `supported_expected_document_presence_rate = 0.915385`
- `supported_nonrefusal_rate = 0.961538`
- `llm_relevance_mean = 0.950000`
- `llm_groundedness_mean = 0.961538`
- `llm_citation_accuracy_mean = 0.961538`
- `llm_completeness_mean = 0.934615`
- `llm_instruction_following_mean = 0.957692`
- `llm_answer_quality_mean = 0.953077`

## Interpretation

These results show that the current RAG agent is strong on supported, document-grounded answering.

What stands out:

- supported answers are usually well grounded
- citation quality is strong
- format following is strong
- out-of-scope refusal is now fully correct on this benchmark

The most important positive signal is:

- `llm_groundedness_mean = 0.961538`

That means the system is usually answering from retrieved evidence instead of drifting into unsupported claims.

## Weak Areas

The current weakest areas are:

- `Negative / Not Found`
  `no_strong_answer_accuracy = 0.6`
  The system still sometimes gives a partial narrative instead of the exact required refusal string.
- `Evidence-Location Questions`
  `llm_answer_quality_mean = 0.38`
  This is the weakest supported category. The agent is weaker when the task is “tell me exactly where in the report this appears.”
- `Partial Data Stress Tests`
  `llm_answer_quality_mean = 0.8`
  The agent is decent, but still not fully reliable when a query mixes supported companies with unsupported entities like Tesla or Apple.
- `Long Context Saturation`
  One of the hard cases dropped companies from the answer instead of explicitly acknowledging what was missing.

So the honest conclusion is:

- supported grounded answering is strong
- refusal behavior is good for unsupported questions
- refusal behavior for in-scope but missing-answer cases still needs more tightening
- evidence-location behavior remains the main supported-category weakness

## Latency Interpretation

This benchmark measures full answer time, not just retrieval. It includes:

- scope classification
- clarity handling
- query embedding
- Qdrant retrieval
- context building
- final Azure OpenAI answer generation

So the most useful latency line for your CV is:

- `Average end-to-end grounded answer latency ≈ 18.1 seconds`

If you want a paired retrieval metric, combine it with the retrieval-only stress metric from [CATEGORY_RETRIEVAL_STRESS_EVALUATION_METRICS.md](C:/Users/hp/Downloads/rag_annual_reports/agent_pipeline/evaluation/CATEGORY_RETRIEVAL_STRESS_EVALUATION_METRICS.md):

- `Average retrieval latency ≈ 6.1 seconds`

## CV-Friendly Answer Metrics

Good headline metrics for a project description are:

- `LLM groundedness = 0.962`
- `LLM citation accuracy = 0.962`
- `LLM answer quality = 0.953`
- `Unsupported refusal accuracy = 1.00`
- `Average end-to-end answer latency ≈ 18.1 seconds`

If you mention refusal quality, be honest and include the caveat:

- `No-strong-answer refusal accuracy = 0.786`, so this is an area still being improved
