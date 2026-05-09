"""
Build the GitHub social / OG card from the canonical trait-count data.

Reads:  data/analysis_results.json
Writes: assets/github-social-1200x630.svg
        assets/github-social-1200x630.png   (via rsvg-convert)

Editorial register, not propaganda register:
- Cream-on-near-black palette (muriel OLED tokens).
- Bars sorted by count, count labels rendered as text (every number labeled).
- Single muted accent for bars; cream for all text (8:1+ contrast).
- Provenance footer: corpus + n + method + source.

Run:  python3 assets/build_og_card.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "analysis_results.json"
SVG_OUT = REPO / "assets" / "github-social-1200x630.svg"
PNG_OUT = REPO / "assets" / "github-social-1200x630.png"

W, H = 1200, 630

CREAM = "#E6E4D2"
CREAM_DIM = "#A8A698"
CREAM_FOOT = "#CECCBC"
NEAR_BLACK = "#0A0A0F"
BAR = "#B26A57"
RULE = "#23232C"

PROJECT_2025_PAGES = 920


def normalize(label: str) -> str:
    s = re.sub(r"^\s*\d+\.\s*", "", label)
    s = re.sub(r"\s*\(\d+\)\s*$", "", s)
    return s.strip()


def load_counts() -> tuple[list[tuple[str, int]], int]:
    records = json.loads(DATA.read_text())
    counter: Counter[str] = Counter()
    for rec in records:
        for c in rec.get("concepts", []) or []:
            label = c.get("trait") or c.get("label") or c.get("name") or c.get("type")
            if label:
                counter[normalize(label)] += 1
    pairs = sorted(counter.items(), key=lambda kv: -kv[1])
    return pairs, len(records)


def build_svg(pairs: list[tuple[str, int]], n_chunks: int) -> str:
    top = pairs[:8]
    max_n = max(n for _, n in top)

    pad_x = 64
    title_y = 116
    subtitle_y = 158
    dropcap_x = pad_x
    dropcap_y = subtitle_y
    dropcap_size = 120
    text_indent = pad_x + 78

    bar_top = 210
    bar_h = 28
    bar_gap = 14
    label_w = 280
    bar_x = pad_x + label_w + 16
    bar_max_w = W - bar_x - 120 - pad_x

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, '
        f'Helvetica Neue, Helvetica, Arial, sans-serif">'
    )
    parts.append(f'<rect width="{W}" height="{H}" fill="{NEAR_BLACK}"/>')

    parts.append(
        f'<text x="{dropcap_x}" y="{dropcap_y}" fill="{CREAM}" '
        f'font-family="Charter, &quot;Iowan Old Style&quot;, Georgia, '
        f'Cambria, serif" font-size="{dropcap_size}" font-weight="700" '
        f'letter-spacing="-2">F</text>'
    )
    parts.append(
        f'<text x="{text_indent}" y="{title_y}" fill="{CREAM}" font-size="56" '
        f'font-weight="700" letter-spacing="-1.2">'
        f'ascist Language Analyzer</text>'
    )
    parts.append(
        f'<text x="{text_indent}" y="{subtitle_y}" fill="{CREAM_DIM}" '
        f'font-size="22" font-weight="400" letter-spacing="0.2">'
        f"Eco&#8217;s Ur-Fascism traits, counted across Project 2025</text>"
    )

    parts.append(
        f'<line x1="{pad_x}" y1="180" x2="{W - pad_x}" y2="180" '
        f'stroke="{RULE}" stroke-width="1"/>'
    )

    for i, (trait, n) in enumerate(top):
        y = bar_top + i * (bar_h + bar_gap)
        bw = max(2, int(round(bar_max_w * n / max_n)))
        text_y = y + bar_h - 9

        parts.append(
            f'<text x="{pad_x + label_w}" y="{text_y}" fill="{CREAM}" '
            f'font-size="17" font-weight="500" text-anchor="end">'
            f'{escape(trait)}</text>'
        )
        parts.append(
            f'<rect x="{bar_x}" y="{y}" width="{bw}" height="{bar_h}" '
            f'fill="{BAR}" rx="2"/>'
        )
        parts.append(
            f'<text x="{bar_x + bw + 10}" y="{text_y}" fill="{CREAM}" '
            f'font-size="17" font-weight="600" '
            f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
            f'{n}</text>'
        )

    foot_y = H - 40
    parts.append(
        f'<line x1="{pad_x}" y1="{foot_y - 22}" x2="{W - pad_x}" y2="{foot_y - 22}" '
        f'stroke="{RULE}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{pad_x}" y="{foot_y}" fill="{CREAM_FOOT}" font-size="16" '
        f'font-weight="500" letter-spacing="0.2">'
        f"Project 2025 &#183; "
        f"{PROJECT_2025_PAGES} pages &#183; "
        f"{n_chunks} analyzed chunks &#183; "
        f"LangChain &#183; "
        f"Eco, &#8220;Ur-Fascism,&#8221; 1995"
        f"</text>"
    )
    parts.append(
        f'<text x="{W - pad_x}" y="{foot_y}" fill="{CREAM_FOOT}" font-size="16" '
        f'font-weight="500" text-anchor="end">'
        f'github.com/andyed/fascist-language-analyzer</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    pairs, n_chunks = load_counts()
    svg = build_svg(pairs, n_chunks)
    SVG_OUT.write_text(svg)
    print(f"wrote {SVG_OUT.relative_to(REPO)} ({len(svg)} bytes)")

    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        print("rsvg-convert not found; PNG step skipped")
        return
    subprocess.run(
        [rsvg, "-w", str(W), "-h", str(H), "-o", str(PNG_OUT), str(SVG_OUT)],
        check=True,
    )
    print(f"wrote {PNG_OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
