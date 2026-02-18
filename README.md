# Fascist Language Analyzer — Chapter 2 (LangExtract Deep Dive)

Chapter 1 is preserved in `README_chapter1.md`.

This Chapter 2 README reframes the project around the entity extraction stack (`langextract`) and how it connects back to the Ur-Fascism rhetorical analysis.

## Table of Contents

- [What Chapter 2 Covers](#what-chapter-2-covers)
- [System Overview](#system-overview)
- [Analysis Highlights (First Release)](#analysis-highlights-first-release)
- [LangExtract Deep Dive](#langextract-deep-dive)
- [Entity ↔ Theme Linking (New in Chapter 2)](#entity--theme-linking-new-in-chapter-2)
- [LangChain Summary (Condensed)](#langchain-summary-condensed)
- [Setup & Run (Chapter 2)](#setup--run-chapter-2)
- [GitHub Pages Artifact Sync](#github-pages-artifact-sync)
- [Known Limits (Chapter 2)](#known-limits-chapter-2)
- [Next Merge-Ready Targets](#next-merge-ready-targets)

## What Chapter 2 Covers

- A technical deep dive into the LangExtract pipeline.
- A condensed summary of the existing LangChain trait-classification system.
- The static + interactive publish flow for themes, entities, and entity↔theme links.

## System Overview

The repo now has two complementary tracks:

1. **Trait analysis track (LangChain)**
   - Input: `data/project_2025.txt`
   - Output: `data/analysis_results.json`
   - Purpose: classify quotes into Eco’s 14 Ur-Fascism properties.

2. **Entity extraction track (LangExtract)**
   - Input: `data/project_2025.txt`
   - Outputs:
     - `data/entities_langextract.jsonl`
     - `data/entities_langextract.normalized*.jsonl`
     - `data/entities_langextract.normalization_report*.json`
   - Purpose: extract grounded named entities/policies/laws/locations and normalize aliases.

These tracks are fused in Chapter 2 visualizations through `scripts/build_entity_theme_links.py`.

## Analysis Highlights (First Release)

This first release uses `--score-mode raw` for ranking in entity↔theme links, with lift/PMI available for analysis.

- Dominant linked themes (by aggregate edge weight) are **Selective Populism**, **Obsession with a Plot**, and **Machismo and Weaponry**.
- Relationship mass is led by **government_agency** entities; location and person classes are secondary contributors.
- Top recurring entity-side terms include broad governance labels (for example `State`, `Administration`, `President`, `department`), indicating strong institutional framing in theme-bearing passages.
- Strongest edges repeatedly connect executive/administrative actors to Selective Populism and Obsession-with-a-Plot language.
- Each edge now carries evidence with `quote`, `chunk_id`, and `source_url` for auditability.

Quick interpretation guidance:

- Treat this as a **macro rhetorical map** first, not final actor attribution.
- Generic high-frequency entities can dominate raw rankings; lift/PMI is included to help de-bias follow-up analysis.

## LangExtract Deep Dive

### 1) Extraction Contract

Extraction is constrained to six classes in `scripts/extract_entities_langextract.py`:

- `person`
- `organization`
- `government_agency`
- `policy_program`
- `legal_reference`
- `location`

The prompt enforces:

- exact span grounding (no paraphrase)
- in-order extraction
- non-overlapping spans
- optional lightweight attributes for graph utility

### 2) Few-Shot Biasing

`EXAMPLES` in `scripts/extract_entities_langextract.py` acts as a schema prior:

- demonstrates span precision
- demonstrates class boundaries
- demonstrates attribute style

This is the main guardrail that keeps extraction coherent across long political prose.

### 3) Long-Document Strategy

Key extraction parameters:

- `--extraction-passes` (default 2): multiple sweeps for higher recall
- `--max-workers` (default 20): parallelization
- `--batch-length` (default 20): chunk processing cadence
- `--max-char-buffer` (default 1200): local context radius

Operationally, recall and precision trade off against `max_char_buffer`; higher values increase contextual disambiguation but can increase noisy captures in dense lists.

### 4) Provider Routing

`build_extract_kwargs()` supports:

- `native` provider mode (direct model key)
- `poe` mode (OpenAI-compatible Poe endpoint)
- `auto` mode (environment-driven fallback)

This lets one script run across Gemini/OpenAI-like backends with minimal changes.

### 5) Grounded Output Shape

LangExtract records include:

- `extraction_text`
- `extraction_class`
- `char_interval.start_pos` / `end_pos`
- `alignment_status`
- optional `attributes`

Because offsets are preserved, downstream snippet generation can anchor context windows directly in original source text.

### 6) Normalization Layer

`scripts/normalize_entities.py` adds canonical identity fields:

- `canonical_id`
- `canonical_label`
- `normalization_method`
- `normalized` (boolean)

Modes:

- `lenient` (default): acronym + parenthetical + title-boundary aware matching
- `strict`: exact alias matching only

Additional normalization supports:

- person alias bootstrap from `data/gold/entities_gold_v0.jsonl`
- alias expansion catalog (`data/normalization_aliases_v2.json`)
- collision reporting in normalization report

### 7) Evaluation & Diagnostics

Gold/eval scripts:

- `scripts/predict_gold_langextract.py`
- `scripts/evaluate_entity_gold.py`

Reports provide strict/lenient diagnostics and unresolved top mentions, which are critical for iterative alias curation.

### 8) Publishing Layer (Chapter 2)

Entity publish path is now intentionally SEO-friendly:

- Grouped static pages by class in `docs/entities/`
- Per-page caps for controlled page bloat
- Longer context snippets with boundary-aware trimming
- Bold mention highlighting in snippet text

Script:

- `scripts/generate_entity_index_pages.py`

Key switches:

- `--max-entities-per-class 50`
- `--max-snippets 0` (all mentions)
- `--snippet-context-chars 180`

## Entity ↔ Theme Linking (New in Chapter 2)

`scripts/build_entity_theme_links.py` computes co-mention edges by matching entity aliases inside trait quote/explanation text.

Release note for v1:

- supports `--score-mode raw|lift|pmi` (default `raw`)
- every edge evidence item now includes `chunk_id` and `source_url`

Output:

- `web/public/entity_theme_data.json`
- `docs/graph/entity_theme_data.json`

Current edge weight:

- weighted sum of concept confidences
- match count per edge
- quote evidence attached to edges

Interactive view:

- route: `#/entity-themes`
- filtered graph with edge-threshold and link-count controls
- top-link panel with evidence and click-through to entity detail

## LangChain Summary (Condensed)

The LangChain track remains the rhetorical backbone:

- taxonomy constrained to Eco’s 14 properties via Pydantic schema (`src/schema.py`)
- structured output for quote + explanation + confidence
- parallel chunk analysis over `project_2025.txt`
- outputs consumed by static and React visualizations

Chapter 2 does not replace this track; it makes it explainable through concrete actors/institutions/policies linked to trait rhetoric.

## Setup & Run (Chapter 2)

```bash
# Python + web deps
pip install -r requirements.txt
npm install --prefix web

# 1) Trait analysis (LangChain)
python src/main.py

# 2) Static theme pages (capped)
python src/generate_site.py --max-items-per-theme 50

# 3) Entity extraction (LangExtract)
python scripts/extract_entities_langextract.py \
  --model-id Gemini-3-Flash \
  --provider-mode auto \
  --extraction-passes 2 \
  --max-workers 20 \
  --max-char-buffer 1200

# 4) Entity normalization
python scripts/normalize_entities.py \
  --mode lenient \
  --input data/entities_langextract.jsonl \
  --output data/entities_langextract.normalized.v2.jsonl \
  --report data/entities_langextract.normalization_report.v2.json

# 5) Static entity pages + Vite entity data
python scripts/generate_entity_index_pages.py \
  --max-entities-per-class 50 \
  --max-snippets 0 \
  --snippet-context-chars 180

# 6) Build entity↔theme link data
python scripts/build_entity_theme_links.py --score-mode raw

# 7) Build React app
npm run build --prefix web
```

## GitHub Pages Artifact Sync

After web build, sync to `docs/graph`:

```bash
rm -rf docs/graph/assets
cp -R web/dist/assets docs/graph/assets
cp web/dist/index.html docs/graph/index.html
cp web/public/data.json docs/graph/data.json
cp web/public/graph_data.json docs/graph/graph_data.json
cp web/public/entities_data.json docs/graph/entities_data.json
cp web/public/entity_theme_data.json docs/graph/entity_theme_data.json
```

## Known Limits (Chapter 2)

- Alias matching in entity↔theme linking is lexical and can over-link generic terms.
- High-frequency entities can dominate when using `--score-mode raw`; use `--score-mode lift` or `--score-mode pmi` for normalized views.
- Table-of-contents style sections still introduce noisy entity contexts.

## Next Merge-Ready Targets

- Add PMI/lift-normalized edge score in `build_entity_theme_links.py`.
- Add chapter-level partitioning in static entity pages (A–M / N–Z) if payloads grow.
- Add a dedicated “evidence-only” toggle in the entity↔theme view.
