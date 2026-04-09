from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CATEGORY_BANK_PATH = DATA_DIR / "category_question_bank.json"
CATEGORY_CASES_PATH = DATA_DIR / "category_benchmark_cases.json"
QUESTION_BANK_README_PATH = BASE_DIR / "CATEGORY_QUESTION_BANK.md"


def make_case(
    *,
    case_id: str,
    question: str,
    answer_expectation: str = "supported",
    company_filters: list[str] | None = None,
    chunk_types: list[str] | None = None,
    expected_document_ids: list[str] | None = None,
    expected_chunk_types: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "question": question,
        "answer_expectation": answer_expectation,
        "company_filters": company_filters or [],
        "chunk_types": chunk_types or [],
        "expected_document_ids": expected_document_ids or [],
        "expected_chunk_types": expected_chunk_types or [],
    }


CATEGORIES: list[dict[str, Any]] = []

CATEGORIES.extend(
    [
        {
            "category_id": "simple_fact_lookup",
            "category_name": "Simple Fact Lookup",
            "description": "Single-metric baseline questions anchored in one company report.",
            "cases": [
                make_case(
                    case_id="simple_bmw_revenue",
                    question="What were BMW Group revenues in 2024?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="simple_mercedes_fcf",
                    question="What was Mercedes-Benz free cash flow of the industrial business in 2024?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="simple_volkswagen_sales_revenue",
                    question="What was Volkswagen Group sales revenue in 2024?",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="simple_siemens_dividend",
                    question="What dividend did Siemens propose for fiscal 2024?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="simple_bosch_headcount",
                    question="What headcount did Bosch report at December 31, 2024?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "multi_value_lookup",
            "category_name": "Multi-Value Lookup",
            "description": "Multiple values from the same company must be retrieved and consolidated.",
            "cases": [
                make_case(
                    case_id="multivalue_bmw_revenue_ebt_employees",
                    question="Give BMW Group revenue, Group profit before tax, and employees at year-end for 2024.",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="multivalue_mercedes_revenue_ebit_net_profit",
                    question="Give Mercedes-Benz revenue, EBIT, and net profit for 2024.",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="multivalue_volkswagen_sales_revenue_operating_result_liquidity",
                    question="Give Volkswagen Group sales revenue, operating result, and Automotive Division net liquidity for 2024.",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="multivalue_siemens_revenue_fcf_dividend",
                    question="Give Siemens revenue, free cash flow, and dividend for fiscal 2024.",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="multivalue_bosch_revenue_ebit_profit",
                    question="Give Bosch sales revenue, EBIT, and profit after tax for 2024.",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "cross_company_comparison",
            "category_name": "Cross-Company Comparison",
            "description": "Two or more companies must be kept separate and compared correctly.",
            "cases": [
                make_case(
                    case_id="compare_bmw_mercedes_revenue",
                    question="Compare 2024 revenue for BMW Group and Mercedes-Benz Group.",
                    company_filters=["bmw", "mercedes"],
                    expected_document_ids=["bmw_2024", "mercedes_2024"],
                ),
                make_case(
                    case_id="compare_volkswagen_bosch_revenue",
                    question="Compare 2024 sales revenue for Volkswagen Group and Bosch Group.",
                    company_filters=["volkswagen", "bosch"],
                    expected_document_ids=["volkswagen_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="compare_bmw_mercedes_bosch_fcf",
                    question="Compare BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, and Bosch Group free cash flow for 2024.",
                    company_filters=["bmw", "mercedes", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="compare_bmw_mercedes_siemens_employees",
                    question="Compare employee counts reported by BMW, Mercedes-Benz, and Siemens.",
                    company_filters=["bmw", "mercedes", "siemens"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "siemens_2024"],
                ),
                make_case(
                    case_id="compare_volkswagen_siemens_outlook",
                    question="Compare Volkswagen Group and Siemens outlook for 2025.",
                    company_filters=["volkswagen", "siemens"],
                    expected_document_ids=["volkswagen_2024", "siemens_2024"],
                ),
            ],
        },
        {
            "category_id": "aggregation",
            "category_name": "Aggregation",
            "description": "Questions that require summation or averaging across multiple retrieved values.",
            "cases": [
                make_case(
                    case_id="aggregate_bmw_mercedes_revenue_total",
                    question="What is the total 2024 revenue of BMW Group and Mercedes-Benz Group?",
                    company_filters=["bmw", "mercedes"],
                    expected_document_ids=["bmw_2024", "mercedes_2024"],
                ),
                make_case(
                    case_id="aggregate_bmw_mercedes_volkswagen_revenue_total",
                    question="What is the total 2024 revenue of BMW, Mercedes-Benz, and Volkswagen Group?",
                    company_filters=["bmw", "mercedes", "volkswagen"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "volkswagen_2024"],
                ),
                make_case(
                    case_id="aggregate_bosch_siemens_revenue_total",
                    question="What is the total 2024 revenue of Bosch Group and Siemens?",
                    company_filters=["bosch", "siemens"],
                    expected_document_ids=["bosch_2024", "siemens_2024"],
                ),
                make_case(
                    case_id="aggregate_bmw_mercedes_bosch_average_employees",
                    question="What is the average employee count reported by BMW, Mercedes-Benz, and Bosch?",
                    company_filters=["bmw", "mercedes", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="aggregate_bmw_mercedes_bosch_fcf_total",
                    question="What is the total of BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, and Bosch Group free cash flow for 2024?",
                    company_filters=["bmw", "mercedes", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "ranking_ordering",
            "category_name": "Ranking / Ordering",
            "description": "Entities must be sorted correctly after retrieving multiple values.",
            "cases": [
                make_case(
                    case_id="rank_bmw_mercedes_volkswagen_revenue",
                    question="Rank BMW, Mercedes-Benz, and Volkswagen Group by 2024 revenue from highest to lowest.",
                    company_filters=["bmw", "mercedes", "volkswagen"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "volkswagen_2024"],
                ),
                make_case(
                    case_id="rank_bmw_siemens_bosch_employees",
                    question="Rank BMW, Siemens, and Bosch by reported employee count from highest to lowest.",
                    company_filters=["bmw", "siemens", "bosch"],
                    expected_document_ids=["bmw_2024", "siemens_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="rank_bmw_mercedes_bosch_fcf",
                    question="Rank BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, and Bosch Group free cash flow from highest to lowest.",
                    company_filters=["bmw", "mercedes", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="rank_bmw_mercedes_bosch_ebit",
                    question="Which company had the lowest 2024 EBIT among BMW, Mercedes-Benz, and Bosch?",
                    company_filters=["bmw", "mercedes", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="rank_siemens_segment_backlog",
                    question="Rank Siemens Digital Industries, Smart Infrastructure, and Mobility by order backlog at the end of fiscal 2024.",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
            ],
        },
    ]
)

CATEGORIES.extend(
    [
        {
            "category_id": "exactness_vs_approximation",
            "category_name": "Exactness vs Approximation",
            "description": "Questions that test whether the system respects exact or approximate wording.",
            "cases": [
                make_case(
                    case_id="exact_bmw_revenue",
                    question="What is the exact BMW Group revenue for 2024?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="approx_bmw_revenue",
                    question="Approximately what was BMW Group revenue in 2024?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="exact_mercedes_ebit",
                    question="What is the exact Mercedes-Benz EBIT for 2024?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="approx_bosch_fcf",
                    question="Approximately what was Bosch Group free cash flow in 2024?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
                make_case(
                    case_id="exact_siemens_dividend",
                    question="What is the exact Siemens dividend per share proposed for fiscal 2024?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
            ],
        },
        {
            "category_id": "missing_field_within_valid_query",
            "category_name": "Missing-Field Within Valid Query",
            "description": "Some requested fields exist while others appear missing.",
            "cases": [
                make_case(
                    case_id="missingfield_bmw_revenue_ebitda_margin",
                    question="Give BMW Group revenue and EBITDA margin for 2024.",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="missingfield_mercedes_revenue_ebitda_margin",
                    question="Give Mercedes-Benz revenue and EBITDA margin for 2024.",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="missingfield_vw_revenue_ebitda_margin",
                    question="Give Volkswagen sales revenue and EBITDA margin for 2024.",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="missingfield_siemens_revenue_q2",
                    question="Give Siemens revenue for fiscal 2024 and Siemens revenue for Q2 2024.",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="missingfield_bosch_revenue_ebitda_margin",
                    question="Give Bosch sales revenue and EBITDA margin for 2024.",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "cross_type_retrieval",
            "category_name": "Cross-Type Retrieval",
            "description": "Questions that need both narrative text and table evidence.",
            "cases": [
                make_case(
                    case_id="crosstype_bmw_revenue_and_decline_reason",
                    question="What was BMW Group revenue in 2024 and how does BMW explain the decline?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                    expected_chunk_types=["table", "text"],
                ),
                make_case(
                    case_id="crosstype_mercedes_ebit_and_decline_reason",
                    question="What was Mercedes-Benz EBIT in 2024 and what explanation does the report give for the decline?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                    expected_chunk_types=["table", "text"],
                ),
                make_case(
                    case_id="crosstype_vw_sales_revenue_and_letter_commentary",
                    question="What was Volkswagen sales revenue in 2024 and what does the shareholder letter say about operating result or cost structures?",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                    expected_chunk_types=["table", "text"],
                ),
                make_case(
                    case_id="crosstype_bosch_revenue_and_weakness_reason",
                    question="What was Bosch sales revenue in 2024 and what does Bosch say about why the year fell short of expectations?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                    expected_chunk_types=["table", "text"],
                ),
                make_case(
                    case_id="crosstype_siemens_fcf_and_dividend_policy",
                    question="What was Siemens free cash flow in fiscal 2024 and what does Siemens say about its dividend policy?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                    expected_chunk_types=["table", "text"],
                ),
            ],
        },
        {
            "category_id": "instruction_following_strictness",
            "category_name": "Instruction Following Strictness",
            "description": "Prompts that explicitly demand evidence, pages, and structure.",
            "cases": [
                make_case(
                    case_id="instruction_bmw_mercedes_revenue_evidence_pages",
                    question="Compare BMW and Mercedes-Benz revenue and give exact evidence and pages.",
                    company_filters=["bmw", "mercedes"],
                    expected_document_ids=["bmw_2024", "mercedes_2024"],
                ),
                make_case(
                    case_id="instruction_vw_outlook_evidence_pages",
                    question="Give Volkswagen's 2025 outlook with exact evidence and pages.",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="instruction_siemens_dividend_source_page",
                    question="Show Siemens' dividend proposal with the source file and page.",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="instruction_bosch_growth_forecast_evidence",
                    question="Show Bosch's 2025 sales revenue growth forecast with exact evidence and page.",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
                make_case(
                    case_id="instruction_bmw_reporting_period_citation",
                    question="Give BMW's reporting period and cite the page with exact evidence.",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
            ],
        },
        {
            "category_id": "adversarial_prompting",
            "category_name": "Adversarial Prompting",
            "description": "Prompts that try to coerce guessing or extra-corpus behavior.",
            "cases": [
                make_case(
                    case_id="adversarial_bmw_estimate_2026",
                    question="Even if the report does not say so, estimate BMW Group revenue in 2026.",
                    answer_expectation="no_strong_answer",
                    company_filters=["bmw"],
                ),
                make_case(
                    case_id="adversarial_mercedes_guess_ebitda_margin",
                    question="If you cannot find it, guess Mercedes-Benz EBITDA margin for 2024.",
                    answer_expectation="no_strong_answer",
                    company_filters=["mercedes"],
                ),
                make_case(
                    case_id="adversarial_vw_investment_advice",
                    question="Tell me whether Volkswagen or Siemens is the better investment, even if it is not in the documents.",
                    answer_expectation="unsupported",
                    company_filters=["volkswagen", "siemens"],
                ),
                make_case(
                    case_id="adversarial_bosch_forecast_invent",
                    question="Invent a likely Bosch revenue forecast for 2026 if needed.",
                    answer_expectation="no_strong_answer",
                    company_filters=["bosch"],
                ),
                make_case(
                    case_id="adversarial_tesla_fill_in",
                    question="Compare BMW and Tesla revenue and give Tesla's value even if Tesla is not in the corpus.",
                    answer_expectation="no_strong_answer",
                    company_filters=["bmw"],
                ),
            ],
        },
    ]
)

CATEGORIES.extend(
    [
        {
            "category_id": "multi_hop_retrieval",
            "category_name": "Multi-Hop Retrieval",
            "description": "Value lookup plus explanatory rationale from a different chunk or section.",
            "cases": [
                make_case(
                    case_id="multihop_bmw_revenue_and_reasons",
                    question="What was BMW Group revenue in 2024 and what reasons does BMW give for the decline?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="multihop_mercedes_revenue_and_reasons",
                    question="What was Mercedes-Benz revenue in 2024 and what reasons are given for the change?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="multihop_vw_operating_result_and_impact",
                    question="What was Volkswagen's operating result in 2024 and what impacted it?",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="multihop_bosch_revenue_and_why",
                    question="What was Bosch sales revenue in 2024 and what does Bosch say explains the weak development?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
                make_case(
                    case_id="multihop_siemens_backlog_and_conversion",
                    question="What was Siemens' total order backlog at September 30, 2024 and how much is expected to convert to revenue in fiscal 2025?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
            ],
        },
        {
            "category_id": "contradiction_multiple_mentions",
            "category_name": "Contradiction / Multiple Mentions",
            "description": "Facts that appear in more than one place and should remain consistent.",
            "cases": [
                make_case(
                    case_id="multi_mention_bmw_revenue",
                    question="What was BMW Group revenue in 2024? Use the most consistent figure in the report.",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="multi_mention_mercedes_ebit",
                    question="What was Mercedes-Benz EBIT in 2024? Use the report's consistent value.",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="multi_mention_volkswagen_sales_revenue",
                    question="What was Volkswagen Group sales revenue in 2024? Use the report's consistent value.",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="multi_mention_siemens_dividend",
                    question="What dividend did Siemens propose for fiscal 2024? Use the consistent report value.",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="multi_mention_bosch_fcf",
                    question="What was Bosch Group free cash flow in 2024? Use the consistent report value.",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "long_context_saturation",
            "category_name": "Long Context Saturation",
            "description": "Broad prompts that require maintaining company coverage under longer contexts.",
            "cases": [
                make_case(
                    case_id="longcontext_all_risks",
                    question="Summarize the major risks mentioned by BMW, Mercedes-Benz, Volkswagen Group, Siemens, and Bosch, with one example per company.",
                    company_filters=["bmw", "mercedes", "volkswagen", "siemens", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "volkswagen_2024", "siemens_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="longcontext_all_outlook",
                    question="Summarize the 2025 outlook across all five companies.",
                    company_filters=["bmw", "mercedes", "volkswagen", "siemens", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "volkswagen_2024", "siemens_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="longcontext_all_2024_environment",
                    question="Summarize how the five reports describe the 2024 business environment.",
                    company_filters=["bmw", "mercedes", "volkswagen", "siemens", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "volkswagen_2024", "siemens_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="longcontext_all_climate_targets",
                    question="Summarize climate or sustainability commitments mentioned across all five reports.",
                    company_filters=["bmw", "mercedes", "volkswagen", "siemens", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "volkswagen_2024", "siemens_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="longcontext_all_financial_strength",
                    question="Summarize how the five reports describe financial strength, liquidity, or financial robustness.",
                    company_filters=["bmw", "mercedes", "volkswagen", "siemens", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "volkswagen_2024", "siemens_2024", "bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "query_decomposition",
            "category_name": "Query Decomposition",
            "description": "Questions whose answer requires hidden multi-step retrieval and reasoning.",
            "cases": [
                make_case(
                    case_id="decompose_highest_revenue_all",
                    question="Which of BMW, Mercedes-Benz, Volkswagen Group, Siemens, and Bosch had the highest reported 2024 revenue, and what was the value?",
                    company_filters=["bmw", "mercedes", "volkswagen", "siemens", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "volkswagen_2024", "siemens_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="decompose_highest_employees_four",
                    question="Which of BMW, Mercedes-Benz, Siemens, and Bosch reported the highest employee count, and what was the value?",
                    company_filters=["bmw", "mercedes", "siemens", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "siemens_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="decompose_highest_fcf_bmw_mercedes_bosch_siemens",
                    question="Which is highest among BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, Bosch Group free cash flow, and Siemens free cash flow, and what is the value?",
                    company_filters=["bmw", "mercedes", "bosch", "siemens"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "bosch_2024", "siemens_2024"],
                ),
                make_case(
                    case_id="decompose_higher_revenue_siemens_bosch",
                    question="Which company reports the larger revenue, Siemens or Bosch, and what are the values?",
                    company_filters=["siemens", "bosch"],
                    expected_document_ids=["siemens_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="decompose_highest_siemens_segment_backlog",
                    question="Which Siemens segment had the highest reported order backlog at fiscal 2024 year-end, and what was the value?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
            ],
        },
        {
            "category_id": "noise_resistance",
            "category_name": "Noise / Irrelevant Context Resistance",
            "description": "Questions with distracting add-ons that should not derail the main answer.",
            "cases": [
                make_case(
                    case_id="noise_bmw_mercedes_revenue_and_chairmen",
                    question="Compare BMW and Mercedes-Benz revenue and also mention the chairman named in each shareholder letter.",
                    company_filters=["bmw", "mercedes"],
                    expected_document_ids=["bmw_2024", "mercedes_2024"],
                ),
                make_case(
                    case_id="noise_bosch_siemens_revenue_and_risk",
                    question="Compare Bosch and Siemens revenue and also mention whether each report discusses geopolitical risk.",
                    company_filters=["bosch", "siemens"],
                    expected_document_ids=["bosch_2024", "siemens_2024"],
                ),
                make_case(
                    case_id="noise_mercedes_revenue_bmw_dividend_only",
                    question="Give Mercedes-Benz revenue and BMW dividend, and nothing else.",
                    company_filters=["mercedes", "bmw"],
                    expected_document_ids=["mercedes_2024", "bmw_2024"],
                ),
                make_case(
                    case_id="noise_vw_bosch_outlook_with_evidence",
                    question="Compare Volkswagen and Bosch outlook for 2025 and include exact evidence.",
                    company_filters=["volkswagen", "bosch"],
                    expected_document_ids=["volkswagen_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="noise_siemens_vw_revenue_and_pages",
                    question="Compare Siemens revenue and Volkswagen sales revenue and also include the source pages.",
                    company_filters=["siemens", "volkswagen"],
                    expected_document_ids=["siemens_2024", "volkswagen_2024"],
                ),
            ],
        },
    ]
)

CATEGORIES.extend(
    [
        {
            "category_id": "partial_data_stress",
            "category_name": "Partial Data Stress Tests",
            "description": "Requests mixing in-corpus entities with out-of-corpus ones.",
            "cases": [
                make_case(
                    case_id="partial_bmw_tesla_siemens_revenue_total",
                    question="What is the total revenue of BMW, Tesla, and Siemens?",
                    answer_expectation="supported",
                    company_filters=["bmw", "siemens"],
                    expected_document_ids=["bmw_2024", "siemens_2024"],
                ),
                make_case(
                    case_id="partial_mercedes_bosch_tesla_compare",
                    question="Compare revenue for Mercedes-Benz, Bosch, and Tesla.",
                    answer_expectation="supported",
                    company_filters=["mercedes", "bosch"],
                    expected_document_ids=["mercedes_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="partial_siemens_vw_apple_dividends",
                    question="What is the average dividend of Siemens, Volkswagen preferred shares, and Apple?",
                    answer_expectation="supported",
                    company_filters=["siemens", "volkswagen"],
                    expected_document_ids=["siemens_2024", "volkswagen_2024"],
                ),
                make_case(
                    case_id="partial_bmw_mercedes_tesla_headcount",
                    question="Sum BMW and Mercedes-Benz employee counts and add Tesla headcount.",
                    answer_expectation="supported",
                    company_filters=["bmw", "mercedes"],
                    expected_document_ids=["bmw_2024", "mercedes_2024"],
                ),
                make_case(
                    case_id="partial_vw_tesla_revenue",
                    question="Which is higher, Volkswagen sales revenue or Tesla revenue?",
                    answer_expectation="supported",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
            ],
        },
        {
            "category_id": "entity_disambiguation",
            "category_name": "Entity Disambiguation",
            "description": "Queries about segments, divisions, or similarly named business units.",
            "cases": [
                make_case(
                    case_id="entity_bmw_automotive_revenue",
                    question="What was BMW Automotive segment revenue in 2024?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="entity_mercedes_cars_revenue",
                    question="What was Mercedes-Benz Cars segment revenue in 2024?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="entity_vw_passenger_cars_revenue",
                    question="What was Volkswagen Passenger Cars brand sales revenue in 2024?",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="entity_siemens_mobility_backlog",
                    question="What was Siemens Mobility's order backlog at the end of fiscal 2024?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="entity_bosch_mobility_growth_target",
                    question="What average annual sales revenue growth target does Bosch set for the Mobility business sector by 2030?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "section_specific_queries",
            "category_name": "Section-Specific Queries",
            "description": "Questions that reference named sections like risk or outlook.",
            "cases": [
                make_case(
                    case_id="section_bmw_risk_report",
                    question="What does BMW say in the detailed risk report about geopolitical risks?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="section_mercedes_outlook",
                    question="What does Mercedes-Benz say in its outlook for the 2025 financial year?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="section_volkswagen_about_report",
                    question="What does Volkswagen say in the 'About this report' section about the basis for financial information?",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="section_siemens_risk_management",
                    question="What does Siemens say in the Risk management section about its ERM approach?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="section_bosch_hybrid_globalization",
                    question="What does Bosch say in its risk report about hybrid globalization?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "unit_scale_sensitivity",
            "category_name": "Unit / Scale Sensitivity",
            "description": "Numerical answers should preserve units and scale correctly.",
            "cases": [
                make_case(
                    case_id="units_bmw_revenue_million",
                    question="Give BMW Group revenue in millions of euros.",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="units_mercedes_revenue_billion",
                    question="Give Mercedes-Benz revenue in billions of euros.",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="units_vw_revenue_operating_result_billion",
                    question="State Volkswagen sales revenue and operating result in billions of euros.",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="units_siemens_fcf_and_dividend",
                    question="Give Siemens free cash flow in billions of euros and its dividend per share in euros.",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="units_bosch_revenue_and_ebit_margin",
                    question="Give Bosch sales revenue and EBIT margin for 2024 without mixing units.",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "currency_awareness",
            "category_name": "Currency Awareness",
            "description": "Comparisons should note currency consistency or differences.",
            "cases": [
                make_case(
                    case_id="currency_bmw_mercedes_revenue",
                    question="Compare BMW and Mercedes-Benz revenue and note the currency and unit used.",
                    company_filters=["bmw", "mercedes"],
                    expected_document_ids=["bmw_2024", "mercedes_2024"],
                ),
                make_case(
                    case_id="currency_siemens_vw_dividend",
                    question="Compare the Siemens dividend and the Volkswagen preferred-share dividend and note the units.",
                    company_filters=["siemens", "volkswagen"],
                    expected_document_ids=["siemens_2024", "volkswagen_2024"],
                ),
                make_case(
                    case_id="currency_bosch_bmw_revenue",
                    question="Compare Bosch sales revenue and BMW Group revenue and say whether they are reported in different currencies.",
                    company_filters=["bosch", "bmw"],
                    expected_document_ids=["bosch_2024", "bmw_2024"],
                ),
                make_case(
                    case_id="currency_mercedes_siemens_fcf",
                    question="Compare Mercedes-Benz industrial free cash flow and Siemens free cash flow and note the units used.",
                    company_filters=["mercedes", "siemens"],
                    expected_document_ids=["mercedes_2024", "siemens_2024"],
                ),
                make_case(
                    case_id="currency_vw_bosch_revenue",
                    question="Compare Volkswagen Group sales revenue and Bosch Group sales revenue and note whether the currency differs.",
                    company_filters=["volkswagen", "bosch"],
                    expected_document_ids=["volkswagen_2024", "bosch_2024"],
                ),
            ],
        },
    ]
)

CATEGORIES.extend(
    [
        {
            "category_id": "period_sensitive",
            "category_name": "Period-Sensitive Questions",
            "description": "Questions that require fiscal dates or reporting-period awareness.",
            "cases": [
                make_case(
                    case_id="period_bmw_reporting_period",
                    question="What reporting period does BMW Group Report 2024 cover?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="period_mercedes_employee_date",
                    question="As of what date does Mercedes-Benz report its employee count?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="period_volkswagen_sales_revenue_period",
                    question="For what period does Volkswagen report 2024 sales revenue in its key figures?",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="period_siemens_employee_date",
                    question="As of what date does Siemens report its employee count?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="period_bosch_headcount_date",
                    question="As of what date does Bosch report headcount in its key data table?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "mixed_queries",
            "category_name": "Mixed Queries",
            "description": "Realistic prompts that combine comparison, evidence, and computed or structured outputs.",
            "cases": [
                make_case(
                    case_id="mixed_bmw_mercedes_revenue_employees",
                    question="Compare BMW and Mercedes-Benz on 2024 revenue and employee count.",
                    company_filters=["bmw", "mercedes"],
                    expected_document_ids=["bmw_2024", "mercedes_2024"],
                ),
                make_case(
                    case_id="mixed_siemens_bosch_growth_outlook",
                    question="Compare Bosch and Siemens outlook for 2025 and say which one expects higher revenue growth.",
                    company_filters=["bosch", "siemens"],
                    expected_document_ids=["bosch_2024", "siemens_2024"],
                ),
                make_case(
                    case_id="mixed_bmw_mercedes_bosch_fcf_pages",
                    question="Compare BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, and Bosch free cash flow, and include the pages.",
                    company_filters=["bmw", "mercedes", "bosch"],
                    expected_document_ids=["bmw_2024", "mercedes_2024", "bosch_2024"],
                ),
                make_case(
                    case_id="mixed_volkswagen_sales_operating_result_evidence",
                    question="Give Volkswagen sales revenue and operating result for 2024 with exact evidence and page numbers.",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="mixed_bmw_vw_siemens_resources",
                    question="Compare BMW revenue, Volkswagen sales revenue, and Siemens revenue, and cite the source pages.",
                    company_filters=["bmw", "volkswagen", "siemens"],
                    expected_document_ids=["bmw_2024", "volkswagen_2024", "siemens_2024"],
                ),
            ],
        },
        {
            "category_id": "negative_not_found",
            "category_name": "Negative / Not Found",
            "description": "In-scope but unsupported-by-evidence questions that should fail safely.",
            "cases": [
                make_case(
                    case_id="notfound_bmw_ebitda_margin",
                    question="What was BMW's EBITDA margin in 2024?",
                    answer_expectation="no_strong_answer",
                    company_filters=["bmw"],
                ),
                make_case(
                    case_id="notfound_mercedes_ebitda_margin",
                    question="What was Mercedes-Benz EBITDA margin in 2024?",
                    answer_expectation="no_strong_answer",
                    company_filters=["mercedes"],
                ),
                make_case(
                    case_id="notfound_volkswagen_ebitda_margin",
                    question="What was Volkswagen Group EBITDA margin in 2024?",
                    answer_expectation="no_strong_answer",
                    company_filters=["volkswagen"],
                ),
                make_case(
                    case_id="notfound_siemens_q2_revenue",
                    question="What was Siemens revenue in Q2 2024 only?",
                    answer_expectation="no_strong_answer",
                    company_filters=["siemens"],
                ),
                make_case(
                    case_id="notfound_bosch_2027_revenue_target",
                    question="What revenue target did Bosch set for 2027?",
                    answer_expectation="no_strong_answer",
                    company_filters=["bosch"],
                ),
            ],
        },
        {
            "category_id": "out_of_scope",
            "category_name": "Out-of-Scope Questions",
            "description": "Questions that fall outside the annual-report corpus and should be refused as unsupported.",
            "cases": [
                make_case(
                    case_id="unsupported_bmw_2026_revenue",
                    question="What will BMW Group revenue be in 2026?",
                    answer_expectation="unsupported",
                    company_filters=["bmw"],
                ),
                make_case(
                    case_id="unsupported_mercedes_investment_advice",
                    question="Is Mercedes-Benz a better investment than BMW right now?",
                    answer_expectation="unsupported",
                    company_filters=["mercedes", "bmw"],
                ),
                make_case(
                    case_id="unsupported_volkswagen_stock_price_today",
                    question="What is Volkswagen's stock price today?",
                    answer_expectation="unsupported",
                    company_filters=["volkswagen"],
                ),
                make_case(
                    case_id="unsupported_siemens_weather",
                    question="What is the weather in Munich today for Siemens headquarters?",
                    answer_expectation="unsupported",
                    company_filters=["siemens"],
                ),
                make_case(
                    case_id="unsupported_bosch_translation",
                    question="Translate Bosch's annual report into Arabic.",
                    answer_expectation="unsupported",
                    company_filters=["bosch"],
                ),
            ],
        },
        {
            "category_id": "ambiguous_questions",
            "category_name": "Ambiguous Questions",
            "description": "Underspecified questions that should fail safely rather than guessing.",
            "cases": [
                make_case(
                    case_id="ambiguous_revenue",
                    question="What is the revenue?",
                    answer_expectation="no_strong_answer",
                ),
                make_case(
                    case_id="ambiguous_dividend",
                    question="What is the dividend?",
                    answer_expectation="no_strong_answer",
                ),
                make_case(
                    case_id="ambiguous_best_company",
                    question="Which company is best?",
                    answer_expectation="no_strong_answer",
                ),
                make_case(
                    case_id="ambiguous_outlook",
                    question="What is the outlook?",
                    answer_expectation="no_strong_answer",
                ),
                make_case(
                    case_id="ambiguous_page_reference",
                    question="What page is it on?",
                    answer_expectation="no_strong_answer",
                ),
            ],
        },
    ]
)

CATEGORIES.extend(
    [
        {
            "category_id": "derived_metrics",
            "category_name": "Derived Metrics",
            "description": "The system must compute ratios or per-capita values from retrieved facts.",
            "cases": [
                make_case(
                    case_id="derived_bmw_revenue_per_employee",
                    question="What was BMW Group revenue per employee in 2024 using reported revenue and reported employees?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="derived_mercedes_revenue_per_employee",
                    question="What was Mercedes-Benz revenue per employee in 2024 using the reported figures?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="derived_bosch_capex_ratio",
                    question="What was Bosch capital expenditure as a percentage of sales revenue in 2024?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
                make_case(
                    case_id="derived_siemens_fcf_to_revenue",
                    question="What was Siemens free cash flow as a percentage of revenue in fiscal 2024?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="derived_bmw_vs_bosch_revenue_per_employee",
                    question="Which company had higher revenue per employee in 2024, BMW or Bosch, and what were the values?",
                    company_filters=["bmw", "bosch"],
                    expected_document_ids=["bmw_2024", "bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "table_based_questions",
            "category_name": "Table-Based Questions",
            "description": "Queries that should rely primarily on table chunks.",
            "cases": [
                make_case(
                    case_id="table_bmw_group_revenue",
                    question="From BMW's figures table, what was Group revenue in 2024?",
                    company_filters=["bmw"],
                    chunk_types=["table"],
                    expected_document_ids=["bmw_2024"],
                    expected_chunk_types=["table"],
                ),
                make_case(
                    case_id="table_mercedes_ebit",
                    question="From the Mercedes-Benz condensed consolidated statement of income, what was EBIT in 2024?",
                    company_filters=["mercedes"],
                    chunk_types=["table"],
                    expected_document_ids=["mercedes_2024"],
                    expected_chunk_types=["table"],
                ),
                make_case(
                    case_id="table_volkswagen_apac_sales_revenue",
                    question="From Volkswagen Group's market table, what was Asia-Pacific sales revenue in 2024?",
                    company_filters=["volkswagen"],
                    chunk_types=["table"],
                    expected_document_ids=["volkswagen_2024"],
                    expected_chunk_types=["table"],
                ),
                make_case(
                    case_id="table_siemens_book_to_bill_and_backlog",
                    question="From Siemens' orders and revenue section, what were the book-to-bill ratio and order backlog for fiscal 2024?",
                    company_filters=["siemens"],
                    chunk_types=["table"],
                    expected_document_ids=["siemens_2024"],
                    expected_chunk_types=["table"],
                ),
                make_case(
                    case_id="table_bosch_profit_after_tax",
                    question="From Bosch's key data table, what was profit after tax in 2024?",
                    company_filters=["bosch"],
                    chunk_types=["table"],
                    expected_document_ids=["bosch_2024"],
                    expected_chunk_types=["table"],
                ),
            ],
        },
        {
            "category_id": "evidence_location",
            "category_name": "Evidence-Location Questions",
            "description": "Traceability questions that ask where a statement appears.",
            "cases": [
                make_case(
                    case_id="location_bmw_outlook_page",
                    question="On which page is BMW's Automotive EBIT margin outlook stated?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="location_mercedes_revenue_page",
                    question="On which page is Mercedes-Benz 2024 revenue reported?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="location_volkswagen_outlook_page",
                    question="On which page does Volkswagen state its 2025 sales revenue and operating return on sales outlook?",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="location_siemens_dividend_page",
                    question="On which page does Siemens propose the dividend for fiscal 2024?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="location_bosch_growth_forecast_page",
                    question="On which page does Bosch forecast 2025 sales revenue growth of 1 to 3 percent?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "exact_evidence_extraction",
            "category_name": "Exact Evidence Extraction",
            "description": "Questions that explicitly require quoted wording from the reports.",
            "cases": [
                make_case(
                    case_id="quote_bmw_geopolitical_risk",
                    question="Quote what BMW says about geopolitical risk scenarios in the detailed risk report.",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="quote_mercedes_geopolitical_situation",
                    question="Quote what Mercedes-Benz says about the geopolitical situation in 2024.",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="quote_volkswagen_2025_outlook",
                    question="Quote Volkswagen's statement about expected 2025 sales revenue and operating return on sales.",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="quote_siemens_order_backlog",
                    question="Quote Siemens' statement about its total order backlog as of September 30, 2024.",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="quote_bosch_scope3_target",
                    question="Quote Bosch's statement about its Scope 3 reduction target.",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
        {
            "category_id": "narrative_synthesis",
            "category_name": "Narrative Synthesis",
            "description": "Multi-sentence synthesis questions that should stay grounded in retrieved text.",
            "cases": [
                make_case(
                    case_id="narrative_bmw_market_conditions",
                    question="What market conditions does BMW describe for 2024?",
                    company_filters=["bmw"],
                    expected_document_ids=["bmw_2024"],
                ),
                make_case(
                    case_id="narrative_mercedes_2024_challenges",
                    question="What challenges does Mercedes-Benz say characterized 2024?",
                    company_filters=["mercedes"],
                    expected_document_ids=["mercedes_2024"],
                ),
                make_case(
                    case_id="narrative_volkswagen_environment",
                    question="How does Volkswagen describe the business environment in 2024?",
                    company_filters=["volkswagen"],
                    expected_document_ids=["volkswagen_2024"],
                ),
                make_case(
                    case_id="narrative_siemens_2025_environment",
                    question="How does Siemens describe the macroeconomic environment for 2025?",
                    company_filters=["siemens"],
                    expected_document_ids=["siemens_2024"],
                ),
                make_case(
                    case_id="narrative_bosch_2024_challenges",
                    question="Why does Bosch say 2024 was challenging?",
                    company_filters=["bosch"],
                    expected_document_ids=["bosch_2024"],
                ),
            ],
        },
    ]
)


def build_flat_cases(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat_cases: list[dict[str, Any]] = []

    for category in categories:
        for index, case in enumerate(category["cases"], start=1):
            flat_cases.append(
                {
                    **case,
                    "category_id": category["category_id"],
                    "category_name": category["category_name"],
                    "category_description": category["description"],
                    "category_case_index": index,
                }
            )

    return flat_cases


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=False, indent=2)


def build_markdown(categories: list[dict[str, Any]]) -> str:
    lines = [
        "# Category Question Bank",
        "",
        "This file lists the large annual-report stress suite used for the category benchmark.",
        "Each category contains five questions grounded in the five 2024 annual reports where possible.",
        "",
    ]

    for category in categories:
        lines.append(f"## {category['category_name']}")
        lines.append("")
        lines.append(category["description"])
        lines.append("")
        for case in category["cases"]:
            filters = ", ".join(case["company_filters"]) if case["company_filters"] else "none"
            expectation = case["answer_expectation"]
            lines.append(f"- `{case['case_id']}`: {case['question']}")
            lines.append(f"  Filters: `{filters}` | Expectation: `{expectation}`")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    nested_output = {"categories": CATEGORIES}
    flat_output = {"cases": build_flat_cases(CATEGORIES)}

    save_json(nested_output, CATEGORY_BANK_PATH)
    save_json(flat_output, CATEGORY_CASES_PATH)
    QUESTION_BANK_README_PATH.write_text(
        build_markdown(CATEGORIES),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
