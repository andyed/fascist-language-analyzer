import argparse
import json
import os
import re
from urllib.parse import quote

INPUT_FILE = "data/analysis_results.json"
SOURCE_TEXT_FILE = "data/project_2025.txt"
SOURCE_DOC_URL = "https://www.project2025.observer/en"
OUTPUT_DIR = "docs"
THEMES_DIR = os.path.join(OUTPUT_DIR, "themes")
CHUNKS_DIR = os.path.join(OUTPUT_DIR, "chunks")
SOURCE_DIR = os.path.join(OUTPUT_DIR, "source")
WEB_PUBLIC_SOURCE_DIR = os.path.join("web", "public", "source")
DEFAULT_MAX_ITEMS_PER_THEME = 50
DEFAULT_SOURCE_PAGES_PER_HTML = 25

TRAIT_COLORS = {
    "Cult of Tradition": "#ffcccc",
    "Rejection of Modernism": "#ffe5cc",
    "Action for Action's Sake": "#ffffcc",
    "Disagreement is Treason": "#e5ffcc",
    "Fear of Difference": "#ccffcc",
    "Appeal to Social Frustration": "#ccffe5",
    "Obsession with a Plot": "#ccffff",
    "Enemy is Strong and Weak": "#cce5ff",
    "Pacifism is Trafficking with the Enemy": "#ccccff",
    "Contempt for the Weak": "#e5ccff",
    "Everybody is Educated to Become a Hero": "#ffccff",
    "Machismo and Weaponry": "#ffcce5",
    "Selective Populism": "#e0e0e0",
    "Ur-Fascism Speaks Newspeak": "#ff9999"
}

def load_data():
    if not os.path.exists(INPUT_FILE):
        return []
    with open(INPUT_FILE, "r") as f:
        return json.load(f)


def load_source_text(path=SOURCE_TEXT_FILE):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def slugify(text):
    return text.lower().replace(" ", "-").replace("'", "")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate static theme pages for docs/")
    parser.add_argument(
        "--max-items-per-theme",
        type=int,
        default=DEFAULT_MAX_ITEMS_PER_THEME,
        help="Max quote cards per theme page (0 means no cap)",
    )
    parser.add_argument(
        "--source-doc-url",
        default=SOURCE_DOC_URL,
        help="Canonical source document URL used for source links",
    )
    parser.add_argument(
        "--source-pages-per-html",
        type=int,
        default=DEFAULT_SOURCE_PAGES_PER_HTML,
        help="How many Project 2025 pages to pack into each local HTML source page",
    )
    return parser.parse_args()


def clean_source_for_offsets(raw_text):
    text = re.sub(r"\n\s*--- PAGE BREAK ---\s*\n", "\n", raw_text)
    text = re.sub(r"\bPAGE\s+BREAK\b", "", text)
    return text


def build_page_index(raw_text):
    marker = re.compile(r"\n\s*--- PAGE BREAK ---\s*\n")
    pages = re.split(marker, raw_text)

    starts = []
    cursor = 0
    total_pages = len(pages)
    for idx, page_text in enumerate(pages, start=1):
        cleaned_page = re.sub(r"\bPAGE\s+BREAK\b", "", page_text)
        starts.append((cursor, idx))
        cursor += len(cleaned_page)
        if idx < total_pages:
            cursor += 1

    return starts


def estimate_page_for_offset(offset, page_starts):
    if offset is None or not page_starts:
        return None

    low = 0
    high = len(page_starts) - 1
    while low <= high:
        mid = (low + high) // 2
        if page_starts[mid][0] <= offset:
            low = mid + 1
        else:
            high = mid - 1

    if high < 0:
        return page_starts[0][1]
    return page_starts[high][1]


def normalize_search_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def build_probe_words(text, max_words=10):
    normalized = normalize_search_text(text)
    if not normalized:
        return ""
    words = [w for w in normalized.split(" ") if w]
    return " ".join(words[:max_words])


def escape_html(text):
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_text_fragment(text):
    normalized = normalize_search_text(text)
    if not normalized:
        return ""
    words = normalized.split(" ")
    probe = " ".join([w for w in words if w][:8])
    return "#:~:text=" + quote(probe, safe="")


def source_html_filename_for_page(page, pages_per_html):
    if not page or not pages_per_html:
        return "p2025-1.html"
    group = (max(1, int(page)) - 1) // max(1, int(pages_per_html)) + 1
    return f"p2025-{group}.html"


def build_local_source_url(page, quote_text, pages_per_html, depth):
    root = "../" * depth
    filename = source_html_filename_for_page(page, pages_per_html)
    fragment = build_text_fragment(quote_text)
    return f"{root}source/{filename}{fragment}"


def estimate_chunk_pages(data, cleaned_source, page_starts):
    chunk_to_page = {}
    cursor = 0

    for chunk in data:
        chunk_id = chunk.get("chunk_id")
        candidates = [chunk.get("source_text", "")]
        for concept in chunk.get("concepts", [])[:3]:
            candidates.append(concept.get("quote", ""))

        found_offset = None
        for candidate in candidates:
            probe = build_probe_words(candidate, max_words=10)
            if len(probe) < 24:
                continue

            # Allow whitespace differences between the quote and the source.
            pattern = r"\\s+".join([re.escape(w) for w in probe.split(" ") if w])
            if not pattern:
                continue
            rx = re.compile(pattern, re.IGNORECASE)

            # Prefer searching forward from the last successful match to keep pages aligned.
            window = cleaned_source[cursor:]
            m = rx.search(window)
            if m is None:
                m = rx.search(cleaned_source)
                if m is None:
                    continue
                found = m.start()
            else:
                found = cursor + m.start()

            found_offset = found
            cursor = found + max(1, len(probe))
            break

        chunk_to_page[chunk_id] = estimate_page_for_offset(found_offset, page_starts)

    return chunk_to_page


def estimate_chunk_pages_by_pages(data, cleaned_pages):
    """Estimate page by searching within per-page text.

    This is more robust than using global character offsets because the raw text
    contains line wraps and unicode punctuation that can defeat simple substring
    matching.
    """

    if not cleaned_pages:
        return {}

    normalized_pages = [normalize_search_text(p) for p in cleaned_pages]
    chunk_to_page = {}
    cursor_page_idx = 0

    for chunk in data:
        chunk_id = chunk.get("chunk_id")
        candidates = [chunk.get("source_text", "")]
        for concept in chunk.get("concepts", [])[:3]:
            candidates.append(concept.get("quote", ""))

        found_page = None
        for candidate in candidates:
            probe = build_probe_words(candidate, max_words=12)
            if len(probe) < 24:
                continue

            # Search forward from the last hit to keep alignment.
            for idx in range(cursor_page_idx, len(normalized_pages)):
                if probe.lower() in normalized_pages[idx].lower():
                    found_page = idx + 1
                    cursor_page_idx = idx
                    break
            if found_page is not None:
                break

            # Fallback: global scan.
            for idx, page_text in enumerate(normalized_pages):
                if probe.lower() in page_text.lower():
                    found_page = idx + 1
                    cursor_page_idx = idx
                    break
            if found_page is not None:
                break

        chunk_to_page[chunk_id] = found_page

    return chunk_to_page

def generate_header(title, depth=0):
    root = "../" * depth
    nav = f"""
    <nav style="background: #333; color: #fff; padding: 1rem; text-align: center;">
        <a href="{root}index.html" style="color: #fff; margin: 0 1rem; text-decoration: none;">Home</a>
        <a href="{root}themes_explained.html" style="color: #fff; margin: 0 1rem; text-decoration: none;">Themes & Sources</a>
        <a href="{root}graph/index.html" style="color: #fff; margin: 0 1rem; text-decoration: none;">Interactive Graph</a>
        <a href="{root}entities/index.html" style="color: #fff; margin: 0 1rem; text-decoration: none;">Entity Index</a>
        <a href="{root}ode.html" style="color: #fff; margin: 0 1rem; text-decoration: none;">The Ode</a>
    </nav>
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ font-family: sans-serif; max-width: 900px; margin: 0 auto; line-height: 1.6; color: #333; }}
            a {{ color: #0066cc; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .quote-card {{ background: #f9f9f9; border-left: 4px solid #ccc; padding: 1rem; margin-bottom: 1rem; }}
            .trait-tag {{ font-weight: bold; font-size: 0.9em; }}
            .theme-section {{ margin-bottom: 2rem; border-bottom: 1px solid #eee; padding-bottom: 1rem; }}
        </style>
    </head>
    <body>
        {nav}
        <div style="padding: 2rem;">
            <h1>{title}</h1>
    """

def generate_footer():
    return """
        </div>
        <footer style="text-align: center; padding: 2rem; border-top: 1px solid #eee; font-size: 0.8em; color: #666;">
            Generated by LangChain + Gemini-3-Flash. <br>
            <a href="https://github.com/langchain-ai/langchain">Powered by LangChain</a>
        </footer>
    </body>
    </html>
    """

def generate_about_themes():
    html = generate_header("Themes & Sources: Umberto Eco's Ur-Fascism")
    
    definitions = [
        ("1. Cult of Tradition", "Truth is already known; we must only interpret the obscure messages of the past."),
        ("2. Rejection of Modernism", "The Enlightenment, the Age of Reason is seen as the beginning of modern depravity."),
        ("3. Action for Action's Sake", "Thinking is a form of emasculation. Culture is suspect insofar as it is identified with critical attitudes."),
        ("4. Disagreement is Treason", "The critical spirit makes distinctions, and to distinguish is a sign of modernism."),
        ("5. Fear of Difference", "The first appeal of a fascist or prematurely fascist movement is an appeal against the intruders."),
        ("6. Appeal to Social Frustration", "Appeal to a frustrated middle class, suffering from an economic crisis or feelings of political humiliation."),
        ("7. Obsession with a Plot", "The followers must feel besieged. The easiest way to solve the plot is the appeal to xenophobia."),
        ("8. Enemy is Strong and Weak", "By a continuous shifting of rhetorical focus, the enemies are at the same time too strong and too weak."),
        ("9. Pacifism is Trafficking with the Enemy", "Life is permanent warfare."),
        ("10. Contempt for the Weak", "Elitism is a typical aspect of any reactionary ideology."),
        ("11. Everybody is Educated to Become a Hero", "In Ur-Fascism, heroism is the norm."),
        ("12. Machismo and Weaponry", "This is the origin of 'machismo' (which implies both disdain for women and intolerance and condemnation of nonstandard sexual habits)."),
        ("13. Selective Populism", "The People is conceived as a quality, a monolithic entity expressing the Common Will."),
        ("14. Ur-Fascism Speaks Newspeak", "All the Nazi or Fascist schoolbooks made use of an impoverished vocabulary, and an elementary syntax.")
    ]
    
    html += """
    <div style="max-width: 800px; margin: 0 auto;">
        <p>This analysis is based on <strong>Umberto Eco's</strong> essay <em>"Ur-Fascism"</em> (1995), originally published in the New York Review of Books. Eco identifies 14 "typical" features of fascism that may not be organized into a coherent system but form a "fuzzy" family resemblance.</p>
        
        <p>The analyzer identifies text segments that align with these definitions:</p>
    """
    
    for title, desc in definitions:
        trait_key = title.split(". ")[1]
        color = TRAIT_COLORS.get(trait_key, "#ccc")
        slug = slugify(trait_key)
        
        html += f"""
        <div class="theme-section" style="border-left: 5px solid {color}; padding-left: 1rem;">
            <h3><a href="themes/{slug}.html" style="color: inherit;">{title}</a></h3>
            <p>{desc}</p>
        </div>
        """
        
    html += """
        <p><em>Source: Eco, Umberto. "Ur-Fascism." The New York Review of Books, June 22, 1995.</em></p>
    </div>
    """
    html += generate_footer()
    
    with open(os.path.join(OUTPUT_DIR, "themes_explained.html"), "w") as f:
        f.write(html)


def generate_chunk_pages(data, chunk_to_page, pages_per_html):
    os.makedirs(CHUNKS_DIR, exist_ok=True)

    for chunk in data:
        chunk_id = chunk.get("chunk_id")
        concepts = chunk.get("concepts", [])
        unique_traits = list(dict.fromkeys([c.get("trait") for c in concepts if c.get("trait")]))
        est_page = chunk_to_page.get(chunk_id)

        html = generate_header(f"Chunk {chunk_id}", depth=1)
        local_source_url = build_local_source_url(
            est_page,
            chunk.get("source_text") or "",
            pages_per_html=pages_per_html,
            depth=1,
        )
        if est_page:
            html += f"<p><strong>Estimated source page:</strong> {est_page} · <a href=\"{local_source_url}\" target=\"_blank\" rel=\"noreferrer\">Open source</a></p>"
        else:
            html += f"<p><a href=\"{local_source_url}\" target=\"_blank\" rel=\"noreferrer\">Open source document</a></p>"

        if unique_traits:
            trait_links = " · ".join(
                [f"<a href=\"../themes/{slugify(t)}.html\">{t}</a>" for t in unique_traits]
            )
            html += f"<p><strong>Linked themes:</strong> {trait_links}</p>"

        source_text = chunk.get("source_text")
        if source_text:
            html += f"<div class=\"quote-card\"><blockquote>\"{source_text[:1200]}\"</blockquote></div>"

        for concept in concepts:
            trait = concept.get("trait", "Unknown")
            color = TRAIT_COLORS.get(trait, "#ccc")
            quote = concept.get("quote", "")
            explanation = concept.get("explanation", "")
            conf = concept.get("confidence", "")
            html += f"""
            <div class=\"quote-card\" style=\"border-left-color: {color}\">
                <p><strong>Theme:</strong> <a href=\"../themes/{slugify(trait)}.html\">{trait}</a></p>
                <blockquote>\"{quote}\"</blockquote>
                <p>{explanation}</p>
                <small>Confidence: {conf}</small>
            </div>
            """

        html += generate_footer()
        with open(os.path.join(CHUNKS_DIR, f"chunk-{chunk_id}.html"), "w") as f:
            f.write(html)


def generate_theme_pages(data, max_items_per_theme, chunk_to_page, pages_per_html):
    os.makedirs(THEMES_DIR, exist_ok=True)
    
    # Group by trait
    traits = {t: [] for t in TRAIT_COLORS.keys()}
    
    for chunk in data:
        for concept in chunk.get("concepts", []):
            t = concept["trait"]
            if t in traits:
                payload = concept.copy()
                payload["chunk_id"] = chunk["chunk_id"]
                payload["estimated_page"] = chunk_to_page.get(chunk["chunk_id"])
                traits[t].append(payload)

    # Generate index of themes
    themes_index = "<ul>"
    
    for trait, items in traits.items():
        slug = slugify(trait)
        filename = f"{slug}.html"
        filepath = os.path.join(THEMES_DIR, filename)
        
        themes_index += f'<li><a href="themes/{filename}">{trait}</a> ({len(items)})</li>'
        
        # content
        display_items = items if max_items_per_theme <= 0 else items[:max_items_per_theme]

        html = generate_header(f"Trait: {trait}", depth=1)
        html += f"<p>Found {len(items)} instances of this trait.</p>"
        if max_items_per_theme > 0 and len(items) > len(display_items):
            html += f"<p>Showing top {len(display_items)} instances on this static page.</p>"
        
        for item in display_items:
            color = TRAIT_COLORS.get(trait, "#ccc")
            local_source_url = build_local_source_url(
                item.get("estimated_page"),
                item.get("quote", ""),
                pages_per_html=pages_per_html,
                depth=1,
            )
            html += f"""
            <div class="quote-card" style="border-left-color: {color}">
                <blockquote>"{item['quote']}"</blockquote>
                <p>{item['explanation']}</p>
                <small>
                    Confidence: {item['confidence']} |
                    <a href="../chunks/chunk-{item['chunk_id']}.html">Chunk {item['chunk_id']}</a>
                    {f" | <a href='{local_source_url}' target='_blank' rel='noreferrer'>Source (est. p.{item['estimated_page']})</a>" if item.get('estimated_page') else ""}
                </small>
            </div>
            """
            
        html += generate_footer()
        
        with open(filepath, "w") as f:
            f.write(html)
            
    themes_index += "</ul>"
    return themes_index

def generate_landing(themes_list, data):
    html = generate_header("Project 2025 Analysis")
    
    html += """
    <h2>Overview</h2>
    <p>This project uses <strong>LangChain</strong> and <strong>Gemini-3-Flash</strong> to analyze the text of Project 2025, mapping it against Umberto Eco's 14 properties of Ur-Fascism.</p>
    
    <div style="text-align: center; margin-bottom: 2rem;">
        <a href="themes_explained.html" style="display: inline-block; padding: 0.5rem 1rem; background: #eee; color: #333; border-radius: 4px; border: 1px solid #ccc; margin-right: 1rem;">Read about the 14 Themes (Eco)</a>
        <a href="https://www.project2025.observer/en" style="display: inline-block; padding: 0.5rem 1rem; background: #eee; color: #333; border-radius: 4px; border: 1px solid #ccc;">Read the Original Text (External)</a>
    </div>
    
    <div style="display: flex; gap: 2rem; margin: 2rem 0;">
        <div style="flex: 1; padding: 1.5rem; background: #eef; border-radius: 8px;">
            <h3>🔍 Explore by Theme</h3>
            """ + themes_list + """
        </div>
        <div style="flex: 1; padding: 1.5rem; border: 1px solid #ddd; border-radius: 8px;">
            <h3>🕸️ Interactive Graph</h3>
            <p>Visualize the connections between text segments and fascist traits.</p>
            <a href="graph/index.html" style="display: inline-block; padding: 0.8rem 1.5rem; background: #0066cc; color: #fff; border-radius: 4px; text-decoration: none; font-weight: bold;">Launch Graph View</a>
        </div>
        <div style="flex: 1; padding: 1.5rem; border: 1px solid #ddd; border-radius: 8px;">
            <h3>🏷️ Entity Index</h3>
            <p>Browse extracted people, agencies, organizations, policies, legal references, and locations.</p>
            <a href="entities/index.html" style="display: inline-block; padding: 0.8rem 1.5rem; background: #0066cc; color: #fff; border-radius: 4px; text-decoration: none; font-weight: bold;">Browse Entities</a>
        </div>
    </div>
    """
    
    html += generate_footer()
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
        f.write(html)

def main():
    args = parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Loading data...")
    data = load_data()
    if not data:
        print("No data found!")
        return

    source_text = load_source_text(SOURCE_TEXT_FILE)
    cleaned_source = clean_source_for_offsets(source_text) if source_text else ""
    marker = re.compile(r"\n\s*--- PAGE BREAK ---\s*\n")
    pages = re.split(marker, source_text) if source_text else []
    cleaned_pages = [re.sub(r"\bPAGE\s+BREAK\b", "", p) for p in pages] if source_text else []

    page_starts = build_page_index(source_text) if source_text else []
    chunk_to_page = estimate_chunk_pages_by_pages(data, cleaned_pages) if source_text else {}

    if chunk_to_page:
        chunk_pages_payload = {str(k): v for k, v in chunk_to_page.items() if k is not None}
        for out_path in (
            os.path.join(OUTPUT_DIR, "chunk_pages.json"),
            os.path.join(OUTPUT_DIR, "graph", "chunk_pages.json"),
            os.path.join("web", "public", "chunk_pages.json"),
        ):
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(chunk_pages_payload, f, indent=2)

    if source_text:
        os.makedirs(SOURCE_DIR, exist_ok=True)
        os.makedirs(WEB_PUBLIC_SOURCE_DIR, exist_ok=True)
        per_file = max(1, int(args.source_pages_per_html))
        total_groups = (len(cleaned_pages) + per_file - 1) // per_file
        for group_idx in range(total_groups):
            start = group_idx * per_file
            end = min(len(cleaned_pages), (group_idx + 1) * per_file)
            group_pages = cleaned_pages[start:end]
            page_start_num = start + 1
            page_end_num = end
            body = "\n\n".join([normalize_search_text(p) for p in group_pages if p is not None])
            html = generate_header(f"Project 2025 — Pages {page_start_num}–{page_end_num}", depth=1)
            html += f"<p><strong>Pages {page_start_num}–{page_end_num}</strong></p>"
            html += f"<pre style=\"white-space: pre-wrap;\">{escape_html(body)}</pre>"
            html += generate_footer()
            out_name = f"p2025-{group_idx + 1}.html"
            for output_dir in (SOURCE_DIR, WEB_PUBLIC_SOURCE_DIR):
                with open(os.path.join(output_dir, out_name), "w", encoding="utf-8") as f:
                    f.write(html)

    print("Generating Chunk Pages...")
    generate_chunk_pages(data, chunk_to_page, args.source_pages_per_html)

    print("Generating Theme Pages...")
    themes_list = generate_theme_pages(data, args.max_items_per_theme, chunk_to_page, args.source_pages_per_html)
    
    print("Generating Themes Explanation...")
    generate_about_themes()

    
    print("Generating Landing Page...")
    generate_landing(themes_list, data)
    
    print(f"Site generated in {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
