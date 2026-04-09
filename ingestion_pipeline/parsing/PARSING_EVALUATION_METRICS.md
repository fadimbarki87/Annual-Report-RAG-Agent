# Parsing Evaluation

This document explains the parsing evaluation written to [parsing_quality_evaluation.json](C:/Users/hp/Downloads/rag_annual_reports/ingestion_pipeline/parsing/data/processed/parsing_quality_evaluation.json).

The JSON file now stores metrics only. Explanations and interpretation live in this document.

## What Was Evaluated

The parsing layer was evaluated against two references:

- `raw_azure`
  This checks whether normalization preserved the Azure Document Intelligence output without losing structure or content.
- `pdfs`
  This acts as a silver text reference by extracting text directly from the source PDF and comparing it to the processed page text.

This is the right engineering split for the current project:

- preservation metrics tell us whether normalization damaged the Azure output
- PDF-text fidelity metrics tell us how close the processed text is to the source document text

## Metrics Used

- `raw_page_count_agreement_rate`
  Agreement between processed page count and raw Azure page count. `1.0` means exact agreement.
- `raw_line_preservation_rate`
  Agreement between processed `raw_lines` count and raw Azure non-empty line count. `1.0` means no loss at that level.
- `content_accounting_rate`
  Agreement between raw Azure non-empty line count and processed `clean_lines + removed_lines`. `1.0` means all raw line content is still accounted for.
- `table_preservation_rate`
  Agreement between processed table count and raw Azure table count.
- `paragraph_preservation_rate`
  Agreement between processed and raw Azure paragraph counts.
- `section_preservation_rate`
  Agreement between processed and raw Azure section counts.
- `style_preservation_rate`
  Agreement between processed and raw Azure style counts.
- `figure_preservation_rate`
  Agreement between processed and raw Azure figure counts.
- `silver_pdf_word_error_rate`
  Word error rate against text extracted directly from the source PDF. Lower is better.
- `silver_pdf_word_precision`
  How much of the processed text matches the source PDF text. Higher is better.
- `silver_pdf_word_recall`
  How much of the source PDF text appears in the processed text. Higher is better.
- `silver_pdf_word_f1`
  Combined precision and recall against the source PDF text. Higher is better.
- `silver_pdf_page_wer_median`
  Median page-level word error rate. Lower is better.
- `silver_pdf_page_wer_p90`
  90th percentile page-level word error rate. Lower is better. This is useful for spotting harder pages.

## Current Results

### Preservation Against Raw Azure

Across all five reports:

- `raw_page_count_agreement_rate = 1.0`
- `raw_line_preservation_rate = 1.0`
- `content_accounting_rate = 1.0`
- `table_preservation_rate = 1.0`
- `paragraph_preservation_rate = 1.0`
- `section_preservation_rate = 1.0`
- `style_preservation_rate = 1.0`
- `figure_preservation_rate = 1.0`

Interpretation:

- the normalizer is preserving the Azure output exactly in the dimensions we measured
- it is not dropping pages, lines, or tables
- it is preserving optional Azure structures when they exist

That is a strong result for a conservative normalization layer.

### Text Fidelity Against Source PDFs

Overall means:

- `silver_pdf_word_error_rate = 0.107860`
- `silver_pdf_word_precision = 0.978485`
- `silver_pdf_word_recall = 0.978622`
- `silver_pdf_word_f1 = 0.978549`
- `silver_pdf_page_wer_median = 0.088707`
- `silver_pdf_page_wer_p90 = 0.292720`

Per document:

| Document | Silver PDF WER | Silver PDF F1 | Page WER P90 |
| --- | ---: | ---: | ---: |
| `volkswagen_2024` | `0.051628` | `0.980160` | `0.185995` |
| `siemens_2024` | `0.055947` | `0.985626` | `0.185874` |
| `bmw_2024` | `0.086133` | `0.969581` | `0.285919` |
| `mercedes_2024` | `0.139305` | `0.989942` | `0.304361` |
| `bosch_2024` | `0.206289` | `0.967438` | `0.501452` |

Interpretation:

- `Volkswagen` and `Siemens` are the cleanest relative to source PDF text.
- `BMW` is still strong, but somewhat noisier.
- `Mercedes` has high overlap overall, but more page-level variation.
- `Bosch` is the weakest parsing source and has the noisiest pages.

## What These Results Mean

The parsing layer is in good shape for its intended job.

It is doing two important things correctly:

- preserving Azure structure safely
- keeping processed text close to the source document text

This does **not** mean the parsing is perfect. It means the normalization stage is conservative and trustworthy enough for downstream chunking.

## Retrieval Readiness

For parsing alone:

- the processed outputs are **ready as input to chunking and retrieval**
- the parsing layer does **not** look like the current bottleneck

System-level retrieval readiness still depends more on chunk quality than on parsing quality, but the parsing output is strong enough to support retrieval work now.

## What Is Not Measured Yet

These standard metrics were not computed because the required labeled data is not available:

- `CER` with human-labeled OCR transcripts
- layout `IoU / mAP` with labeled regions
- table `TEDS` with labeled table structure

If a gold benchmark is added later, those would be the next metrics to compute.
