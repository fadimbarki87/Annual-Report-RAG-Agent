# Chunking Evaluation

This document explains the chunking evaluation written to [chunking_quality_evaluation.json](C:/Users/hp/Downloads/rag_annual_reports/ingestion_pipeline/chunking/data/chunks/chunking_quality_evaluation.json).

The JSON file now stores metrics only. Explanations and interpretation live in this document.

## What Was Evaluated

The chunking layer was evaluated by comparing chunk outputs against the processed source documents.

The evaluation focuses on four practical engineering questions:

- Do the chunks cover all pages and tables?
- Do the chunks preserve the important source text?
- Are the chunks reasonably sized for retrieval?
- Is the chunk set low-noise enough to use for baseline retrieval now?

This is the right evaluation for the current stage because true retrieval benchmark metrics need labeled relevance data, which is not available yet.

## Metrics Used

- `page_coverage_rate`
  Share of source pages represented by at least one chunk. `1.0` means full page coverage.
- `table_coverage_rate`
  Share of processed tables represented by table chunks. `1.0` means no table loss.
- `source_token_recall`
  How much of the source narrative text is present in the chunk text. Higher is better.
- `chunk_token_precision`
  How much of the chunk narrative text matches the source narrative text. Higher is better.
- `chunk_token_f1`
  Combined precision and recall between source narrative text and chunk text. Higher is better.
- `heading_coverage_rate`
  Share of source heading paragraphs that appear in chunk text or chunk section metadata.
- `chunk_text_to_source_token_ratio`
  Total chunk narrative token count divided by total source narrative token count. Values near `1.0` mean the chunk set is close in size to the source text. Values above `1.0` would suggest more redundancy or overlap.
- `target_text_chunk_rate_chars_800_1500`
  Share of text chunks inside the intended size band.
- `small_text_chunk_rate_chars_lt_400`
  Share of text chunks under 400 characters. Lower is better.
- `oversized_text_chunk_rate_chars_gt_1500`
  Share of text chunks above 1500 characters. Lower is better.
- `cross_page_text_chunk_rate`
  Share of text chunks spanning multiple pages. Lower is better for traceability.
- `pages_using_paragraphs_rate`
  Share of pages chunked using Azure paragraphs.
- `pages_using_line_fallback_rate`
  Share of pages chunked using `clean_lines` fallback.

## Current Results

Overall means:

- `page_coverage_rate = 1.0`
- `table_coverage_rate = 1.0`
- `source_token_recall = 0.809258`
- `chunk_token_precision = 0.997718`
- `chunk_token_f1 = 0.893005`
- `heading_coverage_rate = 0.989035`
- `chunk_text_to_source_token_ratio = 0.811097`
- `target_text_chunk_rate_chars_800_1500 = 0.537039`
- `small_text_chunk_rate_chars_lt_400 = 0.163433`
- `oversized_text_chunk_rate_chars_gt_1500 = 0.010160`
- `cross_page_text_chunk_rate = 0.0`
- `pages_using_paragraphs_rate = 0.770777`
- `pages_using_line_fallback_rate = 0.229223`

Interpretation:

- coverage is excellent
- heading preservation is excellent
- chunk text is very precise relative to the source text
- recall is good but not perfect, which is expected because chunking is selective and tables are kept separate
- oversize chunks are well controlled
- the conservative merge pass reduced fragmentation, but small chunks are still the main remaining weakness

## Per-Document View

| Document | Source Recall | Chunk Precision | Chunk F1 | Target Size Rate | Small Chunk Rate | Oversized Rate | Line Fallback Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `volkswagen_2024` | `0.858555` | `0.999672` | `0.923755` | `0.566019` | `0.114101` | `0.014948` | `0.132939` |
| `mercedes_2024` | `0.854568` | `0.998446` | `0.920921` | `0.560440` | `0.158556` | `0.004710` | `0.158940` |
| `bmw_2024` | `0.800745` | `0.998863` | `0.888899` | `0.553952` | `0.147079` | `0.006873` | `0.231481` |
| `bosch_2024` | `0.793444` | `0.992236` | `0.881775` | `0.416309` | `0.257511` | `0.006438` | `0.343478` |
| `siemens_2024` | `0.738980` | `0.999374` | `0.849674` | `0.588477` | `0.139918` | `0.017833` | `0.279279` |

Interpretation:

- `Volkswagen` and `Mercedes` are the strongest chunking outputs overall.
- `BMW` is solid and usable.
- `Bosch` is the weakest because it has the highest small-chunk rate and highest fallback dependence.
- `Siemens` has good size control, but lower source recall than the others.

## What These Results Mean

The chunks are behaving like a practical first retrieval index:

- every page is represented
- every processed table is represented
- chunks almost never cross page boundaries
- chunk precision is extremely high
- heading preservation is excellent

The main remaining quality gap is chunk granularity:

- a bit more than half of text chunks now fall into the target `800-1500` character band
- the small-chunk rate improved from about `20%` to about `16%`

That means the chunker is safer than before and less fragmented, but not yet fully optimized.

## Retrieval Readiness

Current answer:

- the chunk output is **retrieval ready for baseline indexing and first RAG experiments**

Why:

- full page coverage
- full table coverage
- very high precision
- high heading coverage
- low oversized-chunk rate
- no cross-page chunking noise

What still limits quality:

- small-chunk fragmentation
- some dependence on line fallback, especially in `Bosch` and `Siemens`
- source recall is good, but not yet as high as a more refined chunker could achieve

So the honest engineering conclusion is:

- **yes, retrieval ready**
- **not yet fully optimized**

## What Is Not Measured Yet

These are standard retrieval metrics, but they require labeled relevance data:

- `Recall@k`
- `MRR`
- `nDCG@k`
- `MAP`

To compute those properly, we would need:

- a set of user queries
- known relevant chunks for each query

Until then, the current report gives a strong structural and coverage-based evaluation, but not a final retrieval benchmark.
