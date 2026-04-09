# Parsing Pipeline

This document explains what [normalize_azure_output.py](normalize_azure_output.py) does to Azure Document Intelligence output before the data is passed to chunking.

The short version: the parsing step is a conservative normalization layer. It does not try to be clever. It takes raw Azure layout JSON, reshapes it into a consistent processed JSON format, preserves the important Azure structures, and marks possible repeated headers/footers without deleting them.

## Inputs And Outputs

Input folder:

```text
ingestion_pipeline/parsing/data/raw_azure
```

Output folder:

```text
ingestion_pipeline/parsing/data/processed
```

For each raw Azure JSON file, the parser writes one processed JSON file. For example:

```text
volkswagen_2024_layout.json -> volkswagen_2024_processed.json
```

If the raw input file does not end in `_layout.json`, the script appends `_processed.json`.

## What The Parser Does

1. It loads raw Azure JSON files from `data/raw_azure`.

2. It finds the Azure result root. The code supports raw files where the useful result is stored under `result`, under `analyzeResult`, or directly at the JSON root.

3. It extracts document-level metadata:

```text
source_file
model_id
page_count
table_count
unmapped_table_count
api_version
content_format
string_index_type
```

4. It reads every Azure page and builds normalized page records.

Each processed page stores:

```text
page_number
width
height
unit
raw_lines
clean_lines
header_footer_candidate_lines
removed_lines
tables
page_type
```

5. It converts Azure page lines into stable line records.

For each non-empty Azure line, the parser keeps:

```text
text
polygon
left
right
top
bottom
```

The `text` is whitespace-normalized. The polygon is preserved. The `left`, `right`, `top`, and `bottom` fields are derived from the polygon so later stages can reason about page position.

6. It creates `clean_lines` as a copy of `raw_lines`.

This is important: the parser does not remove text during normalization. In the current design, `clean_lines` is intentionally conservative and `removed_lines` is empty.

7. It maps Azure tables to pages.

The parser uses each table's Azure `boundingRegions` and `pageNumber` to attach tables to the processed page where they appear. Tables without page information are counted as `unmapped_table_count`.

8. It classifies each page with a simple generic `page_type`.

The page type is one of:

```text
text
mixed
visual_or_table
visual_or_cover
```

This classification is based only on line count and table count. It is a rough routing signal for chunking, not a deep layout classifier.

9. It detects repeated header/footer candidates.

The parser checks lines near the top or bottom margins of pages. If a normalized line appears on enough pages, it is recorded as a repeated header/footer candidate.

The detection output is stored in:

```text
detected_repeated_lines.header_footer_candidates
pages[*].header_footer_candidate_lines
```

This is only a flag. The parser does not delete these lines.

10. It preserves optional Azure document structures.

If present in the Azure result, the parser keeps:

```text
paragraphs
sections
styles
figures
```

This matters because chunking can use Azure paragraphs when they are good enough, while still falling back to lines when paragraph quality is weak.

## What The Parser Does Not Do

The parser does not:

- perform OCR itself
- correct OCR mistakes
- translate text
- summarize text
- remove repeated headers or footers
- reconstruct tables into Markdown
- split documents into retrieval chunks
- create embeddings
- apply company-specific rules for Volkswagen, BMW, Bosch, Mercedes, or Siemens

That is deliberate. This stage is meant to preserve Azure's output safely and make it easier for downstream stages to consume.

## Processed JSON Shape

The top-level processed JSON looks like this:

```text
source_file
model_id
document_metadata
detected_repeated_lines
pages
paragraphs
sections
styles
figures
```

The optional fields `paragraphs`, `sections`, `styles`, and `figures` only appear when Azure provided them.

## Why This Design Is Conservative

Annual reports contain covers, tables, footnotes, page numbers, charts, section titles, and repeated headers. If the parser removes or rewrites too much at this stage, downstream retrieval can lose information.

So this parser uses a safer approach:

- preserve the raw Azure content
- add useful metadata
- mark possible noise instead of deleting it
- leave hard decisions to chunking and retrieval

This makes the processed files trustworthy inputs for the next stage.

## Relation To Evaluation Files

The files named `parsing_quality_evaluation.json` and `chunking_quality_evaluation.json` are not produced by this parser. They are produced by separate evaluation scripts:

```text
ingestion_pipeline/parsing/evaluate_parsing_quality.py
ingestion_pipeline/chunking/evaluate_chunking_quality.py
```

Those evaluation scripts were added to measure the pipeline outputs. Their JSON outputs are reproducible program outputs, not manually typed result files.
