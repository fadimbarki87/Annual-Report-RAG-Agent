# Chunking Pipeline

This document explains what [conservative_chunker.py](conservative_chunker.py) does after parsing.

The short version: the chunker turns processed document pages into retrieval-ready chunks while preserving source metadata, page traceability, section context, and table structure.

## Inputs And Outputs

Input folder:

```text
ingestion_pipeline/parsing/data/processed
```

Output folder:

```text
ingestion_pipeline/chunking/data/chunks
```

The chunker only reads real processed document files ending in:

```text
_processed.json
```

It ignores evaluation JSON files.

For each processed file, it writes one chunk file. For example:

```text
volkswagen_2024_processed.json -> volkswagen_2024_chunks.json
```

## What The Chunker Does

1. It loads each processed document from the parsing output folder.

2. It builds a paragraph index from preserved Azure paragraphs.

Paragraphs are grouped by page when they have exactly one page number in their Azure `boundingRegions`.

3. It decides whether each page should use Azure paragraphs or line fallback.

The chunker prefers paragraphs when they look usable. It falls back to `clean_lines` when paragraphs look too fragmented, too heading-heavy, ambiguous, or weak for narrative chunking.

4. It excludes obvious non-narrative paragraph roles.

The excluded Azure paragraph roles are:

```text
pageHeader
pageFooter
pageNumber
```

5. It avoids mixing table text into normal text chunks.

The chunker uses table bounding regions to avoid including lines or paragraphs that sit inside table regions in normal text chunks.

6. It uses repeated header/footer candidates conservatively.

The parser marks repeated header/footer candidates. The chunker can skip obvious short repeated candidate lines when building fallback line chunks, but it does this conservatively and does not modify the original processed input.

7. It builds text chunks per page.

Text chunks stay on their source page. The chunker does not merge text across pages. This keeps source citations simple and traceable.

Target size settings:

```text
target text size: 1100 characters
preferred minimum: 800 characters
hard maximum: 1500 characters
soft maximum: 1400 characters
```

8. It splits oversized text conservatively.

When a text unit is too large, the chunker splits at sentence or punctuation boundaries where possible, instead of cutting blindly through the middle of text.

9. It applies a small anti-fragmentation merge.

After initial text chunks are created, the chunker merges only safe adjacent small chunks when:

- both chunks are text-like chunks
- both chunks are on the same page
- both chunks come from the same content source
- the merged chunk stays under the maximum text size

This is intentionally narrow. It reduces tiny chunks without aggressively mixing topics.

10. It builds separate table chunks.

Tables are kept as table chunks, not mixed into narrative text chunks. The chunker renders table rows into readable text with row and cell labels such as:

```text
Row 1 [columnHeader]: C1=...
```

Large tables can be split across multiple table chunks by row range.

11. It writes chunk metadata.

Each chunk stores metadata such as:

```text
chunk_id
chunk_index
source_file
model_id
chunk_type
content_source
page_start
page_end
page_numbers
page_types
section_titles
text
char_count
line_count
table_count
paragraph_count
header_footer_candidates_present
table_metadata
```

## Chunk Types

The main chunk types are:

```text
text
table
visual
```

`visual` is used for pages that are mostly cover-like or visual/table-like with limited text.

## What The Chunker Does Not Do

The chunker does not:

- create embeddings
- store vectors
- call Azure OpenAI
- call Qdrant
- answer questions
- rerank retrieval results
- perform company-specific chunking rules
- optimize against a labeled retrieval benchmark

It only creates structured chunk files for the next stage.

## Why This Design Is Conservative

The chunker is designed for annual reports, which contain long narrative sections, dense tables, page headers, footnotes, and visual pages.

The conservative choices are:

- keep page traceability
- keep tables separate
- use paragraphs only when they are usable
- fall back to lines when paragraphs are weak
- merge small chunks only when the merge is safe
- preserve section titles as metadata instead of rewriting the text

This makes the chunks suitable for baseline retrieval and later vector indexing.
