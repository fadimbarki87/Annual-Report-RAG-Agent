# Category Question Bank

This file lists the large annual-report stress suite used for the category benchmark.
Each category contains five questions grounded in the five 2024 annual reports where possible.

## Simple Fact Lookup

Single-metric baseline questions anchored in one company report.

- `simple_bmw_revenue`: What were BMW Group revenues in 2024?
  Filters: `bmw` | Expectation: `supported`
- `simple_mercedes_fcf`: What was Mercedes-Benz free cash flow of the industrial business in 2024?
  Filters: `mercedes` | Expectation: `supported`
- `simple_volkswagen_sales_revenue`: What was Volkswagen Group sales revenue in 2024?
  Filters: `volkswagen` | Expectation: `supported`
- `simple_siemens_dividend`: What dividend did Siemens propose for fiscal 2024?
  Filters: `siemens` | Expectation: `supported`
- `simple_bosch_headcount`: What headcount did Bosch report at December 31, 2024?
  Filters: `bosch` | Expectation: `supported`

## Multi-Value Lookup

Multiple values from the same company must be retrieved and consolidated.

- `multivalue_bmw_revenue_ebt_employees`: Give BMW Group revenue, Group profit before tax, and employees at year-end for 2024.
  Filters: `bmw` | Expectation: `supported`
- `multivalue_mercedes_revenue_ebit_net_profit`: Give Mercedes-Benz revenue, EBIT, and net profit for 2024.
  Filters: `mercedes` | Expectation: `supported`
- `multivalue_volkswagen_sales_revenue_operating_result_liquidity`: Give Volkswagen Group sales revenue, operating result, and Automotive Division net liquidity for 2024.
  Filters: `volkswagen` | Expectation: `supported`
- `multivalue_siemens_revenue_fcf_dividend`: Give Siemens revenue, free cash flow, and dividend for fiscal 2024.
  Filters: `siemens` | Expectation: `supported`
- `multivalue_bosch_revenue_ebit_profit`: Give Bosch sales revenue, EBIT, and profit after tax for 2024.
  Filters: `bosch` | Expectation: `supported`

## Cross-Company Comparison

Two or more companies must be kept separate and compared correctly.

- `compare_bmw_mercedes_revenue`: Compare 2024 revenue for BMW Group and Mercedes-Benz Group.
  Filters: `bmw, mercedes` | Expectation: `supported`
- `compare_volkswagen_bosch_revenue`: Compare 2024 sales revenue for Volkswagen Group and Bosch Group.
  Filters: `volkswagen, bosch` | Expectation: `supported`
- `compare_bmw_mercedes_bosch_fcf`: Compare BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, and Bosch Group free cash flow for 2024.
  Filters: `bmw, mercedes, bosch` | Expectation: `supported`
- `compare_bmw_mercedes_siemens_employees`: Compare employee counts reported by BMW, Mercedes-Benz, and Siemens.
  Filters: `bmw, mercedes, siemens` | Expectation: `supported`
- `compare_volkswagen_siemens_outlook`: Compare Volkswagen Group and Siemens outlook for 2025.
  Filters: `volkswagen, siemens` | Expectation: `supported`

## Aggregation

Questions that require summation or averaging across multiple retrieved values.

- `aggregate_bmw_mercedes_revenue_total`: What is the total 2024 revenue of BMW Group and Mercedes-Benz Group?
  Filters: `bmw, mercedes` | Expectation: `supported`
- `aggregate_bmw_mercedes_volkswagen_revenue_total`: What is the total 2024 revenue of BMW, Mercedes-Benz, and Volkswagen Group?
  Filters: `bmw, mercedes, volkswagen` | Expectation: `supported`
- `aggregate_bosch_siemens_revenue_total`: What is the total 2024 revenue of Bosch Group and Siemens?
  Filters: `bosch, siemens` | Expectation: `supported`
- `aggregate_bmw_mercedes_bosch_average_employees`: What is the average employee count reported by BMW, Mercedes-Benz, and Bosch?
  Filters: `bmw, mercedes, bosch` | Expectation: `supported`
- `aggregate_bmw_mercedes_bosch_fcf_total`: What is the total of BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, and Bosch Group free cash flow for 2024?
  Filters: `bmw, mercedes, bosch` | Expectation: `supported`

## Ranking / Ordering

Entities must be sorted correctly after retrieving multiple values.

- `rank_bmw_mercedes_volkswagen_revenue`: Rank BMW, Mercedes-Benz, and Volkswagen Group by 2024 revenue from highest to lowest.
  Filters: `bmw, mercedes, volkswagen` | Expectation: `supported`
- `rank_bmw_siemens_bosch_employees`: Rank BMW, Siemens, and Bosch by reported employee count from highest to lowest.
  Filters: `bmw, siemens, bosch` | Expectation: `supported`
- `rank_bmw_mercedes_bosch_fcf`: Rank BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, and Bosch Group free cash flow from highest to lowest.
  Filters: `bmw, mercedes, bosch` | Expectation: `supported`
- `rank_bmw_mercedes_bosch_ebit`: Which company had the lowest 2024 EBIT among BMW, Mercedes-Benz, and Bosch?
  Filters: `bmw, mercedes, bosch` | Expectation: `supported`
- `rank_siemens_segment_backlog`: Rank Siemens Digital Industries, Smart Infrastructure, and Mobility by order backlog at the end of fiscal 2024.
  Filters: `siemens` | Expectation: `supported`

## Exactness vs Approximation

Questions that test whether the system respects exact or approximate wording.

- `exact_bmw_revenue`: What is the exact BMW Group revenue for 2024?
  Filters: `bmw` | Expectation: `supported`
- `approx_bmw_revenue`: Approximately what was BMW Group revenue in 2024?
  Filters: `bmw` | Expectation: `supported`
- `exact_mercedes_ebit`: What is the exact Mercedes-Benz EBIT for 2024?
  Filters: `mercedes` | Expectation: `supported`
- `approx_bosch_fcf`: Approximately what was Bosch Group free cash flow in 2024?
  Filters: `bosch` | Expectation: `supported`
- `exact_siemens_dividend`: What is the exact Siemens dividend per share proposed for fiscal 2024?
  Filters: `siemens` | Expectation: `supported`

## Missing-Field Within Valid Query

Some requested fields exist while others appear missing.

- `missingfield_bmw_revenue_ebitda_margin`: Give BMW Group revenue and EBITDA margin for 2024.
  Filters: `bmw` | Expectation: `supported`
- `missingfield_mercedes_revenue_ebitda_margin`: Give Mercedes-Benz revenue and EBITDA margin for 2024.
  Filters: `mercedes` | Expectation: `supported`
- `missingfield_vw_revenue_ebitda_margin`: Give Volkswagen sales revenue and EBITDA margin for 2024.
  Filters: `volkswagen` | Expectation: `supported`
- `missingfield_siemens_revenue_q2`: Give Siemens revenue for fiscal 2024 and Siemens revenue for Q2 2024.
  Filters: `siemens` | Expectation: `supported`
- `missingfield_bosch_revenue_ebitda_margin`: Give Bosch sales revenue and EBITDA margin for 2024.
  Filters: `bosch` | Expectation: `supported`

## Cross-Type Retrieval

Questions that need both narrative text and table evidence.

- `crosstype_bmw_revenue_and_decline_reason`: What was BMW Group revenue in 2024 and how does BMW explain the decline?
  Filters: `bmw` | Expectation: `supported`
- `crosstype_mercedes_ebit_and_decline_reason`: What was Mercedes-Benz EBIT in 2024 and what explanation does the report give for the decline?
  Filters: `mercedes` | Expectation: `supported`
- `crosstype_vw_sales_revenue_and_letter_commentary`: What was Volkswagen sales revenue in 2024 and what does the shareholder letter say about operating result or cost structures?
  Filters: `volkswagen` | Expectation: `supported`
- `crosstype_bosch_revenue_and_weakness_reason`: What was Bosch sales revenue in 2024 and what does Bosch say about why the year fell short of expectations?
  Filters: `bosch` | Expectation: `supported`
- `crosstype_siemens_fcf_and_dividend_policy`: What was Siemens free cash flow in fiscal 2024 and what does Siemens say about its dividend policy?
  Filters: `siemens` | Expectation: `supported`

## Instruction Following Strictness

Prompts that explicitly demand evidence, pages, and structure.

- `instruction_bmw_mercedes_revenue_evidence_pages`: Compare BMW and Mercedes-Benz revenue and give exact evidence and pages.
  Filters: `bmw, mercedes` | Expectation: `supported`
- `instruction_vw_outlook_evidence_pages`: Give Volkswagen's 2025 outlook with exact evidence and pages.
  Filters: `volkswagen` | Expectation: `supported`
- `instruction_siemens_dividend_source_page`: Show Siemens' dividend proposal with the source file and page.
  Filters: `siemens` | Expectation: `supported`
- `instruction_bosch_growth_forecast_evidence`: Show Bosch's 2025 sales revenue growth forecast with exact evidence and page.
  Filters: `bosch` | Expectation: `supported`
- `instruction_bmw_reporting_period_citation`: Give BMW's reporting period and cite the page with exact evidence.
  Filters: `bmw` | Expectation: `supported`

## Adversarial Prompting

Prompts that try to coerce guessing or extra-corpus behavior.

- `adversarial_bmw_estimate_2026`: Even if the report does not say so, estimate BMW Group revenue in 2026.
  Filters: `bmw` | Expectation: `no_strong_answer`
- `adversarial_mercedes_guess_ebitda_margin`: If you cannot find it, guess Mercedes-Benz EBITDA margin for 2024.
  Filters: `mercedes` | Expectation: `no_strong_answer`
- `adversarial_vw_investment_advice`: Tell me whether Volkswagen or Siemens is the better investment, even if it is not in the documents.
  Filters: `volkswagen, siemens` | Expectation: `unsupported`
- `adversarial_bosch_forecast_invent`: Invent a likely Bosch revenue forecast for 2026 if needed.
  Filters: `bosch` | Expectation: `no_strong_answer`
- `adversarial_tesla_fill_in`: Compare BMW and Tesla revenue and give Tesla's value even if Tesla is not in the corpus.
  Filters: `bmw` | Expectation: `no_strong_answer`

## Multi-Hop Retrieval

Value lookup plus explanatory rationale from a different chunk or section.

- `multihop_bmw_revenue_and_reasons`: What was BMW Group revenue in 2024 and what reasons does BMW give for the decline?
  Filters: `bmw` | Expectation: `supported`
- `multihop_mercedes_revenue_and_reasons`: What was Mercedes-Benz revenue in 2024 and what reasons are given for the change?
  Filters: `mercedes` | Expectation: `supported`
- `multihop_vw_operating_result_and_impact`: What was Volkswagen's operating result in 2024 and what impacted it?
  Filters: `volkswagen` | Expectation: `supported`
- `multihop_bosch_revenue_and_why`: What was Bosch sales revenue in 2024 and what does Bosch say explains the weak development?
  Filters: `bosch` | Expectation: `supported`
- `multihop_siemens_backlog_and_conversion`: What was Siemens' total order backlog at September 30, 2024 and how much is expected to convert to revenue in fiscal 2025?
  Filters: `siemens` | Expectation: `supported`

## Contradiction / Multiple Mentions

Facts that appear in more than one place and should remain consistent.

- `multi_mention_bmw_revenue`: What was BMW Group revenue in 2024? Use the most consistent figure in the report.
  Filters: `bmw` | Expectation: `supported`
- `multi_mention_mercedes_ebit`: What was Mercedes-Benz EBIT in 2024? Use the report's consistent value.
  Filters: `mercedes` | Expectation: `supported`
- `multi_mention_volkswagen_sales_revenue`: What was Volkswagen Group sales revenue in 2024? Use the report's consistent value.
  Filters: `volkswagen` | Expectation: `supported`
- `multi_mention_siemens_dividend`: What dividend did Siemens propose for fiscal 2024? Use the consistent report value.
  Filters: `siemens` | Expectation: `supported`
- `multi_mention_bosch_fcf`: What was Bosch Group free cash flow in 2024? Use the consistent report value.
  Filters: `bosch` | Expectation: `supported`

## Long Context Saturation

Broad prompts that require maintaining company coverage under longer contexts.

- `longcontext_all_risks`: Summarize the major risks mentioned by BMW, Mercedes-Benz, Volkswagen Group, Siemens, and Bosch, with one example per company.
  Filters: `bmw, mercedes, volkswagen, siemens, bosch` | Expectation: `supported`
- `longcontext_all_outlook`: Summarize the 2025 outlook across all five companies.
  Filters: `bmw, mercedes, volkswagen, siemens, bosch` | Expectation: `supported`
- `longcontext_all_2024_environment`: Summarize how the five reports describe the 2024 business environment.
  Filters: `bmw, mercedes, volkswagen, siemens, bosch` | Expectation: `supported`
- `longcontext_all_climate_targets`: Summarize climate or sustainability commitments mentioned across all five reports.
  Filters: `bmw, mercedes, volkswagen, siemens, bosch` | Expectation: `supported`
- `longcontext_all_financial_strength`: Summarize how the five reports describe financial strength, liquidity, or financial robustness.
  Filters: `bmw, mercedes, volkswagen, siemens, bosch` | Expectation: `supported`

## Query Decomposition

Questions whose answer requires hidden multi-step retrieval and reasoning.

- `decompose_highest_revenue_all`: Which of BMW, Mercedes-Benz, Volkswagen Group, Siemens, and Bosch had the highest reported 2024 revenue, and what was the value?
  Filters: `bmw, mercedes, volkswagen, siemens, bosch` | Expectation: `supported`
- `decompose_highest_employees_four`: Which of BMW, Mercedes-Benz, Siemens, and Bosch reported the highest employee count, and what was the value?
  Filters: `bmw, mercedes, siemens, bosch` | Expectation: `supported`
- `decompose_highest_fcf_bmw_mercedes_bosch_siemens`: Which is highest among BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, Bosch Group free cash flow, and Siemens free cash flow, and what is the value?
  Filters: `bmw, mercedes, bosch, siemens` | Expectation: `supported`
- `decompose_higher_revenue_siemens_bosch`: Which company reports the larger revenue, Siemens or Bosch, and what are the values?
  Filters: `siemens, bosch` | Expectation: `supported`
- `decompose_highest_siemens_segment_backlog`: Which Siemens segment had the highest reported order backlog at fiscal 2024 year-end, and what was the value?
  Filters: `siemens` | Expectation: `supported`

## Noise / Irrelevant Context Resistance

Questions with distracting add-ons that should not derail the main answer.

- `noise_bmw_mercedes_revenue_and_chairmen`: Compare BMW and Mercedes-Benz revenue and also mention the chairman named in each shareholder letter.
  Filters: `bmw, mercedes` | Expectation: `supported`
- `noise_bosch_siemens_revenue_and_risk`: Compare Bosch and Siemens revenue and also mention whether each report discusses geopolitical risk.
  Filters: `bosch, siemens` | Expectation: `supported`
- `noise_mercedes_revenue_bmw_dividend_only`: Give Mercedes-Benz revenue and BMW dividend, and nothing else.
  Filters: `mercedes, bmw` | Expectation: `supported`
- `noise_vw_bosch_outlook_with_evidence`: Compare Volkswagen and Bosch outlook for 2025 and include exact evidence.
  Filters: `volkswagen, bosch` | Expectation: `supported`
- `noise_siemens_vw_revenue_and_pages`: Compare Siemens revenue and Volkswagen sales revenue and also include the source pages.
  Filters: `siemens, volkswagen` | Expectation: `supported`

## Partial Data Stress Tests

Requests mixing in-corpus entities with out-of-corpus ones.

- `partial_bmw_tesla_siemens_revenue_total`: What is the total revenue of BMW, Tesla, and Siemens?
  Filters: `bmw, siemens` | Expectation: `supported`
- `partial_mercedes_bosch_tesla_compare`: Compare revenue for Mercedes-Benz, Bosch, and Tesla.
  Filters: `mercedes, bosch` | Expectation: `supported`
- `partial_siemens_vw_apple_dividends`: What is the average dividend of Siemens, Volkswagen preferred shares, and Apple?
  Filters: `siemens, volkswagen` | Expectation: `supported`
- `partial_bmw_mercedes_tesla_headcount`: Sum BMW and Mercedes-Benz employee counts and add Tesla headcount.
  Filters: `bmw, mercedes` | Expectation: `supported`
- `partial_vw_tesla_revenue`: Which is higher, Volkswagen sales revenue or Tesla revenue?
  Filters: `volkswagen` | Expectation: `supported`

## Entity Disambiguation

Queries about segments, divisions, or similarly named business units.

- `entity_bmw_automotive_revenue`: What was BMW Automotive segment revenue in 2024?
  Filters: `bmw` | Expectation: `supported`
- `entity_mercedes_cars_revenue`: What was Mercedes-Benz Cars segment revenue in 2024?
  Filters: `mercedes` | Expectation: `supported`
- `entity_vw_passenger_cars_revenue`: What was Volkswagen Passenger Cars brand sales revenue in 2024?
  Filters: `volkswagen` | Expectation: `supported`
- `entity_siemens_mobility_backlog`: What was Siemens Mobility's order backlog at the end of fiscal 2024?
  Filters: `siemens` | Expectation: `supported`
- `entity_bosch_mobility_growth_target`: What average annual sales revenue growth target does Bosch set for the Mobility business sector by 2030?
  Filters: `bosch` | Expectation: `supported`

## Section-Specific Queries

Questions that reference named sections like risk or outlook.

- `section_bmw_risk_report`: What does BMW say in the detailed risk report about geopolitical risks?
  Filters: `bmw` | Expectation: `supported`
- `section_mercedes_outlook`: What does Mercedes-Benz say in its outlook for the 2025 financial year?
  Filters: `mercedes` | Expectation: `supported`
- `section_volkswagen_about_report`: What does Volkswagen say in the 'About this report' section about the basis for financial information?
  Filters: `volkswagen` | Expectation: `supported`
- `section_siemens_risk_management`: What does Siemens say in the Risk management section about its ERM approach?
  Filters: `siemens` | Expectation: `supported`
- `section_bosch_hybrid_globalization`: What does Bosch say in its risk report about hybrid globalization?
  Filters: `bosch` | Expectation: `supported`

## Unit / Scale Sensitivity

Numerical answers should preserve units and scale correctly.

- `units_bmw_revenue_million`: Give BMW Group revenue in millions of euros.
  Filters: `bmw` | Expectation: `supported`
- `units_mercedes_revenue_billion`: Give Mercedes-Benz revenue in billions of euros.
  Filters: `mercedes` | Expectation: `supported`
- `units_vw_revenue_operating_result_billion`: State Volkswagen sales revenue and operating result in billions of euros.
  Filters: `volkswagen` | Expectation: `supported`
- `units_siemens_fcf_and_dividend`: Give Siemens free cash flow in billions of euros and its dividend per share in euros.
  Filters: `siemens` | Expectation: `supported`
- `units_bosch_revenue_and_ebit_margin`: Give Bosch sales revenue and EBIT margin for 2024 without mixing units.
  Filters: `bosch` | Expectation: `supported`

## Currency Awareness

Comparisons should note currency consistency or differences.

- `currency_bmw_mercedes_revenue`: Compare BMW and Mercedes-Benz revenue and note the currency and unit used.
  Filters: `bmw, mercedes` | Expectation: `supported`
- `currency_siemens_vw_dividend`: Compare the Siemens dividend and the Volkswagen preferred-share dividend and note the units.
  Filters: `siemens, volkswagen` | Expectation: `supported`
- `currency_bosch_bmw_revenue`: Compare Bosch sales revenue and BMW Group revenue and say whether they are reported in different currencies.
  Filters: `bosch, bmw` | Expectation: `supported`
- `currency_mercedes_siemens_fcf`: Compare Mercedes-Benz industrial free cash flow and Siemens free cash flow and note the units used.
  Filters: `mercedes, siemens` | Expectation: `supported`
- `currency_vw_bosch_revenue`: Compare Volkswagen Group sales revenue and Bosch Group sales revenue and note whether the currency differs.
  Filters: `volkswagen, bosch` | Expectation: `supported`

## Period-Sensitive Questions

Questions that require fiscal dates or reporting-period awareness.

- `period_bmw_reporting_period`: What reporting period does BMW Group Report 2024 cover?
  Filters: `bmw` | Expectation: `supported`
- `period_mercedes_employee_date`: As of what date does Mercedes-Benz report its employee count?
  Filters: `mercedes` | Expectation: `supported`
- `period_volkswagen_sales_revenue_period`: For what period does Volkswagen report 2024 sales revenue in its key figures?
  Filters: `volkswagen` | Expectation: `supported`
- `period_siemens_employee_date`: As of what date does Siemens report its employee count?
  Filters: `siemens` | Expectation: `supported`
- `period_bosch_headcount_date`: As of what date does Bosch report headcount in its key data table?
  Filters: `bosch` | Expectation: `supported`

## Mixed Queries

Realistic prompts that combine comparison, evidence, and computed or structured outputs.

- `mixed_bmw_mercedes_revenue_employees`: Compare BMW and Mercedes-Benz on 2024 revenue and employee count.
  Filters: `bmw, mercedes` | Expectation: `supported`
- `mixed_siemens_bosch_growth_outlook`: Compare Bosch and Siemens outlook for 2025 and say which one expects higher revenue growth.
  Filters: `bosch, siemens` | Expectation: `supported`
- `mixed_bmw_mercedes_bosch_fcf_pages`: Compare BMW Automotive free cash flow, Mercedes-Benz industrial free cash flow, and Bosch free cash flow, and include the pages.
  Filters: `bmw, mercedes, bosch` | Expectation: `supported`
- `mixed_volkswagen_sales_operating_result_evidence`: Give Volkswagen sales revenue and operating result for 2024 with exact evidence and page numbers.
  Filters: `volkswagen` | Expectation: `supported`
- `mixed_bmw_vw_siemens_resources`: Compare BMW revenue, Volkswagen sales revenue, and Siemens revenue, and cite the source pages.
  Filters: `bmw, volkswagen, siemens` | Expectation: `supported`

## Negative / Not Found

In-scope but unsupported-by-evidence questions that should fail safely.

- `notfound_bmw_ebitda_margin`: What was BMW's EBITDA margin in 2024?
  Filters: `bmw` | Expectation: `no_strong_answer`
- `notfound_mercedes_ebitda_margin`: What was Mercedes-Benz EBITDA margin in 2024?
  Filters: `mercedes` | Expectation: `no_strong_answer`
- `notfound_volkswagen_ebitda_margin`: What was Volkswagen Group EBITDA margin in 2024?
  Filters: `volkswagen` | Expectation: `no_strong_answer`
- `notfound_siemens_q2_revenue`: What was Siemens revenue in Q2 2024 only?
  Filters: `siemens` | Expectation: `no_strong_answer`
- `notfound_bosch_2027_revenue_target`: What revenue target did Bosch set for 2027?
  Filters: `bosch` | Expectation: `no_strong_answer`

## Out-of-Scope Questions

Questions that fall outside the annual-report corpus and should be refused as unsupported.

- `unsupported_bmw_2026_revenue`: What will BMW Group revenue be in 2026?
  Filters: `bmw` | Expectation: `unsupported`
- `unsupported_mercedes_investment_advice`: Is Mercedes-Benz a better investment than BMW right now?
  Filters: `mercedes, bmw` | Expectation: `unsupported`
- `unsupported_volkswagen_stock_price_today`: What is Volkswagen's stock price today?
  Filters: `volkswagen` | Expectation: `unsupported`
- `unsupported_siemens_weather`: What is the weather in Munich today for Siemens headquarters?
  Filters: `siemens` | Expectation: `unsupported`
- `unsupported_bosch_translation`: Translate Bosch's annual report into Arabic.
  Filters: `bosch` | Expectation: `unsupported`

## Ambiguous Questions

Underspecified questions that should fail safely rather than guessing.

- `ambiguous_revenue`: What is the revenue?
  Filters: `none` | Expectation: `no_strong_answer`
- `ambiguous_dividend`: What is the dividend?
  Filters: `none` | Expectation: `no_strong_answer`
- `ambiguous_best_company`: Which company is best?
  Filters: `none` | Expectation: `no_strong_answer`
- `ambiguous_outlook`: What is the outlook?
  Filters: `none` | Expectation: `no_strong_answer`
- `ambiguous_page_reference`: What page is it on?
  Filters: `none` | Expectation: `no_strong_answer`

## Derived Metrics

The system must compute ratios or per-capita values from retrieved facts.

- `derived_bmw_revenue_per_employee`: What was BMW Group revenue per employee in 2024 using reported revenue and reported employees?
  Filters: `bmw` | Expectation: `supported`
- `derived_mercedes_revenue_per_employee`: What was Mercedes-Benz revenue per employee in 2024 using the reported figures?
  Filters: `mercedes` | Expectation: `supported`
- `derived_bosch_capex_ratio`: What was Bosch capital expenditure as a percentage of sales revenue in 2024?
  Filters: `bosch` | Expectation: `supported`
- `derived_siemens_fcf_to_revenue`: What was Siemens free cash flow as a percentage of revenue in fiscal 2024?
  Filters: `siemens` | Expectation: `supported`
- `derived_bmw_vs_bosch_revenue_per_employee`: Which company had higher revenue per employee in 2024, BMW or Bosch, and what were the values?
  Filters: `bmw, bosch` | Expectation: `supported`

## Table-Based Questions

Queries that should rely primarily on table chunks.

- `table_bmw_group_revenue`: From BMW's figures table, what was Group revenue in 2024?
  Filters: `bmw` | Expectation: `supported`
- `table_mercedes_ebit`: From the Mercedes-Benz condensed consolidated statement of income, what was EBIT in 2024?
  Filters: `mercedes` | Expectation: `supported`
- `table_volkswagen_apac_sales_revenue`: From Volkswagen Group's market table, what was Asia-Pacific sales revenue in 2024?
  Filters: `volkswagen` | Expectation: `supported`
- `table_siemens_book_to_bill_and_backlog`: From Siemens' orders and revenue section, what were the book-to-bill ratio and order backlog for fiscal 2024?
  Filters: `siemens` | Expectation: `supported`
- `table_bosch_profit_after_tax`: From Bosch's key data table, what was profit after tax in 2024?
  Filters: `bosch` | Expectation: `supported`

## Evidence-Location Questions

Traceability questions that ask where a statement appears.

- `location_bmw_outlook_page`: On which page is BMW's Automotive EBIT margin outlook stated?
  Filters: `bmw` | Expectation: `supported`
- `location_mercedes_revenue_page`: On which page is Mercedes-Benz 2024 revenue reported?
  Filters: `mercedes` | Expectation: `supported`
- `location_volkswagen_outlook_page`: On which page does Volkswagen state its 2025 sales revenue and operating return on sales outlook?
  Filters: `volkswagen` | Expectation: `supported`
- `location_siemens_dividend_page`: On which page does Siemens propose the dividend for fiscal 2024?
  Filters: `siemens` | Expectation: `supported`
- `location_bosch_growth_forecast_page`: On which page does Bosch forecast 2025 sales revenue growth of 1 to 3 percent?
  Filters: `bosch` | Expectation: `supported`

## Exact Evidence Extraction

Questions that explicitly require quoted wording from the reports.

- `quote_bmw_geopolitical_risk`: Quote what BMW says about geopolitical risk scenarios in the detailed risk report.
  Filters: `bmw` | Expectation: `supported`
- `quote_mercedes_geopolitical_situation`: Quote what Mercedes-Benz says about the geopolitical situation in 2024.
  Filters: `mercedes` | Expectation: `supported`
- `quote_volkswagen_2025_outlook`: Quote Volkswagen's statement about expected 2025 sales revenue and operating return on sales.
  Filters: `volkswagen` | Expectation: `supported`
- `quote_siemens_order_backlog`: Quote Siemens' statement about its total order backlog as of September 30, 2024.
  Filters: `siemens` | Expectation: `supported`
- `quote_bosch_scope3_target`: Quote Bosch's statement about its Scope 3 reduction target.
  Filters: `bosch` | Expectation: `supported`

## Narrative Synthesis

Multi-sentence synthesis questions that should stay grounded in retrieved text.

- `narrative_bmw_market_conditions`: What market conditions does BMW describe for 2024?
  Filters: `bmw` | Expectation: `supported`
- `narrative_mercedes_2024_challenges`: What challenges does Mercedes-Benz say characterized 2024?
  Filters: `mercedes` | Expectation: `supported`
- `narrative_volkswagen_environment`: How does Volkswagen describe the business environment in 2024?
  Filters: `volkswagen` | Expectation: `supported`
- `narrative_siemens_2025_environment`: How does Siemens describe the macroeconomic environment for 2025?
  Filters: `siemens` | Expectation: `supported`
- `narrative_bosch_2024_challenges`: Why does Bosch say 2024 was challenging?
  Filters: `bosch` | Expectation: `supported`
