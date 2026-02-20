import argparse
import bisect
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

DEFAULT_INPUT = "data/entities_langextract.normalized.v2.jsonl"
DEFAULT_FALLBACK_INPUT = "data/entities_langextract.normalized.jsonl"
DEFAULT_TEXT = "data/project_2025.txt"
DEFAULT_DOCS_DIR = "docs/entities"
DEFAULT_WEB_DATA = "web/public/entities_data.json"
DEFAULT_DOCS_GRAPH_DATA = "docs/graph/entities_data.json"
DEFAULT_MAX_SNIPPETS = 0
DEFAULT_MAX_ENTITIES_PER_CLASS = 50
DEFAULT_SNIPPET_CONTEXT_CHARS = 180
DEFAULT_SOURCE_DOC_URL = "https://www.project2025.observer/en"
DEFAULT_SOURCE_PAGES_PER_HTML = 25
SENTENCE_SCAN_LIMIT = 260

CLASS_ORDER = [
    "government_agency",
    "organization",
    "person",
    "policy_program",
    "legal_reference",
    "location",
]

CLASS_LABELS = {
    "government_agency": "Government Agencies",
    "organization": "Organizations",
    "person": "People",
    "policy_program": "Policy Programs",
    "legal_reference": "Legal References",
    "location": "Locations",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate grouped static entity index pages and web entity data."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Normalized entities JSONL path")
    parser.add_argument("--fallback-input", default=DEFAULT_FALLBACK_INPUT, help="Fallback JSONL path")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Raw source text path for snippets")
    parser.add_argument("--docs-dir", default=DEFAULT_DOCS_DIR, help="Output directory for static entity HTML")
    parser.add_argument("--web-data", default=DEFAULT_WEB_DATA, help="Output JSON path for Vite app")
    parser.add_argument(
        "--docs-graph-data",
        default=DEFAULT_DOCS_GRAPH_DATA,
        help="Output JSON path for the deployed docs/graph app",
    )
    parser.add_argument(
        "--max-entities-per-class",
        type=int,
        default=DEFAULT_MAX_ENTITIES_PER_CLASS,
        help="Cap per class for static pages only (0 means no cap)",
    )
    parser.add_argument(
        "--max-snippets",
        type=int,
        default=DEFAULT_MAX_SNIPPETS,
        help="Max snippet examples per entity (0 means all mentions)",
    )
    parser.add_argument(
        "--snippet-context-chars",
        type=int,
        default=DEFAULT_SNIPPET_CONTEXT_CHARS,
        help="Characters of left/right context around each extracted mention",
    )
    parser.add_argument(
        "--source-doc-url",
        default=DEFAULT_SOURCE_DOC_URL,
        help="Canonical source document URL used for quote/source links",
    )
    parser.add_argument(
        "--source-pages-per-html",
        type=int,
        default=DEFAULT_SOURCE_PAGES_PER_HTML,
        help="Must match source splitting; used for local source URLs",
    )
    return parser.parse_args()


def canonicalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_text_fragment(text: str) -> str:
    normalized = canonicalize_whitespace(text or "")
    if not normalized:
        return ""
    words = normalized.split(" ")
    probe = " ".join([w for w in words if w][:8])
    return "#:~:text=" + quote(probe, safe="")


def source_html_filename_for_page(page: int | None, pages_per_html: int) -> str:
    if not page:
        return "p2025-1.html"
    per_file = max(1, int(pages_per_html))
    group = (max(1, int(page)) - 1) // per_file + 1
    return f"p2025-{group}.html"


def build_local_source_url(page: int | None, snippet_text: str, pages_per_html: int, depth: int) -> str:
    root = "../" * depth
    filename = source_html_filename_for_page(page, pages_per_html)
    fragment = build_text_fragment(snippet_text)
    return f"{root}source/{filename}{fragment}"


def build_app_source_url(page: int | None, snippet_text: str, pages_per_html: int) -> str:
    # For the SPA (served at site root), use a relative path that stays within the repo base.
    filename = source_html_filename_for_page(page, pages_per_html)
    fragment = build_text_fragment(snippet_text)
    return f"source/{filename}{fragment}"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def highlight_terms_html(text: str, terms: list[str]) -> str:
    clean_terms = [t for t in terms if t]
    if not text or not clean_terms:
        return escape_html(text)

    ordered = sorted(set(clean_terms), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(term) for term in ordered), re.IGNORECASE)

    chunks: list[str] = []
    pos = 0
    for match in pattern.finditer(text):
        start, end = match.span()
        if start > pos:
            chunks.append(escape_html(text[pos:start]))
        chunks.append(f"<strong>{escape_html(text[start:end])}</strong>")
        pos = end

    if pos < len(text):
        chunks.append(escape_html(text[pos:]))

    return "".join(chunks)


def clamp_word_start(text: str, idx: int) -> int:
    idx = max(0, min(idx, len(text)))
    if idx == 0 or idx >= len(text):
        return idx
    if text[idx - 1].isalnum() and text[idx].isalnum():
        while idx > 0 and text[idx - 1].isalnum():
            idx -= 1
    return idx


def clamp_word_end(text: str, idx: int) -> int:
    idx = max(0, min(idx, len(text)))
    if idx == 0 or idx >= len(text):
        return idx
    if text[idx - 1].isalnum() and text[idx].isalnum():
        while idx < len(text) and text[idx].isalnum():
            idx += 1
    return idx


def maybe_sentence_aligned_bounds(
    text: str, start: int, end: int, left: int, right: int, min_length: int
) -> tuple[int, int]:
    left = clamp_word_start(text, left)
    right = clamp_word_end(text, right)

    left_search_start = max(left, start - SENTENCE_SCAN_LIMIT)
    right_search_end = min(right, end + SENTENCE_SCAN_LIMIT)

    sentence_starts = ".!?"

    # Prefer a nearby sentence boundary before the entity.
    best_left = left
    for i in range(start - 1, left_search_start - 1, -1):
        if text[i] in sentence_starts:
            candidate = i + 1
            while candidate < len(text) and text[candidate].isspace():
                candidate += 1
            if candidate < start:
                best_left = max(left, candidate)
                break

    # Prefer a nearby sentence boundary after the entity.
    best_right = right
    for i in range(end, right_search_end):
        if text[i] in sentence_starts:
            candidate = i + 1
            while candidate < len(text) and text[candidate].isspace():
                candidate += 1
            best_right = min(right, candidate)
            break

    if best_right <= best_left:
        return left, right

    # Keep sentence alignment only if it doesn't become too short.
    if (best_right - best_left) < min_length:
        return left, right

    return best_left, best_right


def load_extractions(input_path: Path, fallback_path: Path) -> list[dict]:
    selected = input_path if input_path.exists() else fallback_path
    if not selected.exists():
        raise FileNotFoundError(
            f"No normalized entity file found. Tried: {input_path} and {fallback_path}"
        )

    content = selected.read_text(encoding="utf-8").strip()
    if not content:
        return []

    lines = [line for line in content.splitlines() if line.strip()]
    if len(lines) == 1:
        payload = json.loads(lines[0])
        return payload.get("extractions", [])

    extractions: list[dict] = []
    for line in lines:
        row = json.loads(line)
        if isinstance(row, dict) and "extractions" in row:
            extractions.extend(row.get("extractions", []))
        elif isinstance(row, dict):
            extractions.append(row)
    return extractions


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def clean_source_for_offsets(raw_text: str) -> str:
    text = re.sub(r"\n\s*--- PAGE BREAK ---\s*\n", "\n", raw_text)
    text = re.sub(r"\bPAGE\s+BREAK\b", "", text)
    return text


def build_page_index(raw_text: str) -> tuple[list[int], list[int]]:
    marker = re.compile(r"\n\s*--- PAGE BREAK ---\s*\n")
    pages = re.split(marker, raw_text)

    starts: list[int] = []
    page_numbers: list[int] = []
    cursor = 0
    total_pages = len(pages)

    for idx, page_text in enumerate(pages, start=1):
        cleaned_page = re.sub(r"\bPAGE\s+BREAK\b", "", page_text)
        starts.append(cursor)
        page_numbers.append(idx)
        cursor += len(cleaned_page)
        if idx < total_pages:
            cursor += 1

    return starts, page_numbers


def estimate_page_for_offset(offset: int | None, page_starts: list[int], page_numbers: list[int]) -> int | None:
    if offset is None or not page_starts:
        return None
    pos = bisect.bisect_right(page_starts, offset) - 1
    if pos < 0:
        return page_numbers[0]
    if pos >= len(page_numbers):
        return page_numbers[-1]
    return page_numbers[pos]


def build_entity_records(
    extractions: list[dict],
    cleaned_text: str,
    page_starts: list[int],
    page_numbers: list[int],
    source_doc_url: str,
    source_pages_per_html: int,
    max_snippets: int,
    snippet_context_chars: int,
) -> dict:
    entities: dict[str, dict] = {}

    for item in extractions:
        entity_class = item.get("extraction_class") or "unknown"
        mention_raw = item.get("extraction_text") or ""
        mention = canonicalize_whitespace(mention_raw)

        canonical_id = item.get("canonical_id")
        canonical_label = canonicalize_whitespace(item.get("canonical_label") or mention)

        if canonical_id:
            entity_id = canonical_id
        else:
            entity_id = f"raw.{entity_class}.{slugify(canonical_label or mention or 'unknown')}"

        interval = item.get("char_interval") or {}
        start = interval.get("start_pos")
        end = interval.get("end_pos")

        rec = entities.get(entity_id)
        if rec is None:
            rec = {
                "id": entity_id,
                "label": canonical_label or mention or "(unknown)",
                "entity_class": entity_class,
                "count": 0,
                "normalized_count": 0,
                "first_pos": start if isinstance(start, int) else None,
                "last_pos": end if isinstance(end, int) else None,
                "mentions": Counter(),
                "page_counts": Counter(),
                "snippets": [],
            }
            entities[entity_id] = rec

        rec["count"] += 1
        if item.get("normalized"):
            rec["normalized_count"] += 1
        if mention:
            rec["mentions"][mention] += 1

        if isinstance(start, int):
            page = estimate_page_for_offset(start, page_starts, page_numbers)
            if page is not None:
                rec["page_counts"][page] += 1
            if rec["first_pos"] is None or start < rec["first_pos"]:
                rec["first_pos"] = start
        if isinstance(end, int):
            if rec["last_pos"] is None or end > rec["last_pos"]:
                rec["last_pos"] = end

        snippet_unlimited = max_snippets <= 0
        can_add_snippet = snippet_unlimited or len(rec["snippets"]) < max_snippets

        if cleaned_text and isinstance(start, int) and isinstance(end, int) and can_add_snippet:
            left = max(0, start - snippet_context_chars)
            right = min(len(cleaned_text), end + snippet_context_chars)
            left, right = maybe_sentence_aligned_bounds(
                cleaned_text,
                start,
                end,
                left,
                right,
                min_length=max(140, snippet_context_chars),
            )
            snippet = canonicalize_whitespace(cleaned_text[left:right])
            page = estimate_page_for_offset(start, page_starts, page_numbers)
            app_source = build_app_source_url(page, snippet, pages_per_html=source_pages_per_html)
            snippet_obj = {
                "text": snippet,
                "char_start": start,
                "estimated_page": page,
                "source_url": app_source or source_doc_url,
            }
            if snippet and (
                snippet_unlimited
                or snippet not in [s.get("text", "") if isinstance(s, dict) else s for s in rec["snippets"]]
            ):
                rec["snippets"].append(snippet_obj)

    classes = defaultdict(list)
    for entity in entities.values():
        mention_samples = [m for m, _ in entity["mentions"].most_common(3)]
        normalized_rate = round(
            (entity["normalized_count"] / entity["count"] * 100.0) if entity["count"] else 0.0,
            2,
        )

        entity_payload = {
            "id": entity["id"],
            "label": entity["label"],
            "entity_class": entity["entity_class"],
            "count": entity["count"],
            "normalized_count": entity["normalized_count"],
            "normalized_rate_percent": normalized_rate,
            "first_pos": entity["first_pos"],
            "last_pos": entity["last_pos"],
            "top_estimated_pages": [p for p, _ in entity["page_counts"].most_common(3)],
            "mention_samples": mention_samples,
            "snippets": entity["snippets"],
        }
        classes[entity["entity_class"]].append(entity_payload)

    for cls in classes:
        classes[cls].sort(key=lambda e: (-e["count"], e["label"].lower()))

    return classes


def render_nav(depth: int = 0) -> str:
    root = "../" * depth
    return f"""
    <nav style=\"background:#333;color:#fff;padding:1rem;text-align:center;\">
      <a href=\"{root}index.html\" style=\"color:#fff;margin:0 1rem;text-decoration:none;\">Home</a>
      <a href=\"{root}themes_explained.html\" style=\"color:#fff;margin:0 1rem;text-decoration:none;\">Themes</a>
      <a href=\"{root}graph/index.html\" style=\"color:#fff;margin:0 1rem;text-decoration:none;\">Interactive App</a>
      <a href=\"{root}entities/index.html\" style=\"color:#fff;margin:0 1rem;text-decoration:none;\">Entity Index</a>
    </nav>
    """


def render_page(title: str, body: str, depth: int = 0) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape_html(title)}</title>
  <style>
    body {{ font-family: sans-serif; max-width: 1000px; margin: 0 auto; color: #333; line-height: 1.5; }}
    a {{ color: #0066cc; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .content {{ padding: 2rem; }}
    .entity-card {{ border: 1px solid #e8e8e8; border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem; background: #fafafa; }}
    .muted {{ color: #666; font-size: 0.9rem; }}
    .chip {{ display: inline-block; background: #eef3ff; border: 1px solid #d8e3ff; border-radius: 999px; padding: 0.1rem 0.5rem; margin-right: 0.3rem; font-size: 0.8rem; }}
    .letter-nav a {{ margin-right: 0.4rem; font-size: 0.9rem; }}
  </style>
</head>
<body>
  {render_nav(depth)}
  <div class=\"content\">{body}</div>
</body>
</html>"""


def write_index_page(docs_dir: Path, grouped: dict[str, list[dict]]) -> None:
    total_entities = sum(len(v) for v in grouped.values())
    total_mentions = sum(sum(e["count"] for e in v) for v in grouped.values())

    rows = []
    for cls in CLASS_ORDER + sorted([c for c in grouped.keys() if c not in CLASS_ORDER]):
        entities = grouped.get(cls, [])
        if not entities:
            continue
        mentions = sum(e["count"] for e in entities)
        class_slug = slugify(cls)
        label = CLASS_LABELS.get(cls, cls.replace("_", " ").title())
        rows.append(
            f"<li><a href=\"{class_slug}.html\">{escape_html(label)}</a> — {len(entities)} entities, {mentions} mentions</li>"
        )

    body = f"""
    <h1>Entity Index (Grouped Static Pages)</h1>
    <p>This is a crawlable static index of extracted entities from Project 2025. Pages are grouped by entity class to keep page count low while remaining browsable.</p>
    <p class=\"muted\">Total entities: {total_entities} · Total mentions: {total_mentions}</p>
    <ul>{''.join(rows)}</ul>
    <p><a href=\"../graph/index.html#/entities\">Open interactive entity browser in the Vite app</a></p>
    """

    (docs_dir / "index.html").write_text(render_page("Entity Index", body, depth=1), encoding="utf-8")


def write_class_pages(docs_dir: Path, grouped: dict[str, list[dict]], max_entities_per_class: int) -> None:
    class_names = CLASS_ORDER + sorted([c for c in grouped.keys() if c not in CLASS_ORDER])

    for cls in class_names:
        entities = grouped.get(cls, [])
        if not entities:
            continue

        if max_entities_per_class > 0:
            entities = entities[:max_entities_per_class]

        letter_map: dict[str, list[dict]] = defaultdict(list)
        for entity in entities:
            first = entity["label"][0].upper() if entity["label"] else "#"
            key = first if "A" <= first <= "Z" else "other"
            letter_map[key].append(entity)

        letters = sorted(letter_map.keys(), key=lambda x: (x == "other", x))
        letter_nav = " ".join(
            [f"<a href=\"#{l}\">{'#' if l == 'other' else l}</a>" for l in letters]
        )

        cards = []
        for letter in letters:
            heading = "#" if letter == "other" else letter
            cards.append(f"<h2 id=\"{letter}\">{heading}</h2>")
            for entity in letter_map[letter]:
                label = escape_html(entity["label"])
                mentions = "".join([f"<span class=\"chip\">{escape_html(m)}</span>" for m in entity["mention_samples"]])
                snippet_html = ""
                if entity["snippets"]:
                    snippet_record = entity["snippets"][0]
                    snippet_text = snippet_record.get("text", "") if isinstance(snippet_record, dict) else str(snippet_record)
                    snippet_highlighted = highlight_terms_html(
                        snippet_text,
                        entity.get("mention_samples", []),
                    )
                    page_label = ""
                    source_link = ""
                    if isinstance(snippet_record, dict):
                        page = snippet_record.get("estimated_page")
                        src = snippet_record.get("source_url")
                        if page:
                            page_label = f" (est. p.{page})"
                        if src:
                            if not src.startswith("http") and not src.startswith("../"):
                                src = "../" + src
                            source_link = f" · <a href=\"{escape_html(src)}\" target=\"_blank\" rel=\"noreferrer\">Source{page_label}</a>"
                    snippet_html = f"<p class=\"muted\">Example: {snippet_highlighted}{source_link}</p>"
                entity_href = quote(entity["id"], safe="")

                cards.append(
                    f"""
                    <div class=\"entity-card\">
                      <div><strong>{label}</strong> <span class=\"muted\">({entity['count']} mentions)</span></div>
                      <div class=\"muted\">ID: {escape_html(entity['id'])} · normalized mentions: {entity['normalized_count']} ({entity['normalized_rate_percent']}%)</div>
                      <div style=\"margin-top:0.4rem;\">{mentions}</div>
                      {snippet_html}
                                            <p class=\"muted\"><a href=\"../graph/index.html#/entity/{entity_href}\">Open in interactive app</a></p>
                    </div>
                    """
                )

        class_label = CLASS_LABELS.get(cls, cls.replace("_", " ").title())
        body = f"""
        <p><a href=\"index.html\">← Back to Entity Index</a></p>
        <h1>{escape_html(class_label)}</h1>
        <p class=\"muted\">Grouped by first letter. This keeps static pages limited while preserving discoverability.</p>
        <div class=\"letter-nav\">{letter_nav}</div>
        {''.join(cards)}
        """

        filename = f"{slugify(cls)}.html"
        (docs_dir / filename).write_text(render_page(f"Entities: {class_label}", body, depth=1), encoding="utf-8")


def write_web_data(path: Path, grouped: dict[str, list[dict]]) -> None:
    payload = {
        "entity_classes": [],
        "classes": {},
        "totals": {
            "entities": sum(len(v) for v in grouped.values()),
            "mentions": sum(sum(e["count"] for e in v) for v in grouped.values()),
        },
    }

    class_names = CLASS_ORDER + sorted([c for c in grouped.keys() if c not in CLASS_ORDER])
    for cls in class_names:
        entities = grouped.get(cls, [])
        if not entities:
            continue

        label = CLASS_LABELS.get(cls, cls.replace("_", " ").title())
        payload["entity_classes"].append(
            {
                "id": cls,
                "label": label,
                "entity_count": len(entities),
                "mention_count": sum(e["count"] for e in entities),
            }
        )
        payload["classes"][cls] = entities

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    fallback_path = Path(args.fallback_input)
    raw_text_path = Path(args.text)
    docs_dir = Path(args.docs_dir)
    web_data_path = Path(args.web_data)
    docs_graph_data_path = Path(args.docs_graph_data)

    extractions = load_extractions(input_path, fallback_path)
    raw_text = load_text(raw_text_path)
    cleaned_text = clean_source_for_offsets(raw_text)
    page_starts, page_numbers = build_page_index(raw_text)
    grouped = build_entity_records(
        extractions,
        cleaned_text,
        page_starts,
        page_numbers,
        source_doc_url=args.source_doc_url,
        source_pages_per_html=args.source_pages_per_html,
        max_snippets=args.max_snippets,
        snippet_context_chars=args.snippet_context_chars,
    )

    docs_dir.mkdir(parents=True, exist_ok=True)
    write_index_page(docs_dir, grouped)
    write_class_pages(docs_dir, grouped, max_entities_per_class=args.max_entities_per_class)
    write_web_data(web_data_path, grouped)
    write_web_data(docs_graph_data_path, grouped)

    print(f"Generated static entity pages in: {docs_dir}")
    print(f"Generated Vite entity data: {web_data_path}")
    print(f"Generated docs/graph entity data: {docs_graph_data_path}")
    print(f"Class pages: {len([p for p in docs_dir.glob('*.html') if p.name != 'index.html'])}")


if __name__ == "__main__":
    main()
