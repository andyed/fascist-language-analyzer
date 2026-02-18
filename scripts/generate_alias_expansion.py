import argparse
import json
import re
from pathlib import Path


DEFAULT_REPORT = "data/entities_langextract.normalization_report.json"
DEFAULT_OUTPUT = "data/normalization_aliases_v2.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate alias expansion catalog from normalization unresolved mentions."
    )
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Normalization report JSON path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Alias expansion JSON path")
    parser.add_argument(
        "--top-n", type=int, default=50, help="Number of unresolved mentions to convert"
    )
    return parser.parse_args()


def normalize_key(text: str) -> str:
    text = text.strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def slugify(text: str) -> str:
    return normalize_key(text).replace(" ", "_")[:80]


def prefix_for_entity_class(entity_class: str) -> str:
    mapping = {
        "government_agency": "agency",
        "organization": "organization",
        "policy_program": "program",
        "legal_reference": "law",
        "location": "location",
        "person": "person",
    }
    return mapping.get(entity_class, "raw")


def main() -> None:
    args = parse_args()
    report_path = Path(args.report)
    output_path = Path(args.output)

    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    unresolved = report.get("top_unresolved_mentions", {})
    if not isinstance(unresolved, dict):
        raise ValueError("top_unresolved_mentions missing or invalid in report")

    sorted_items = sorted(unresolved.items(), key=lambda item: item[1], reverse=True)
    selected = sorted_items[: args.top_n]

    entries: list[dict] = []
    for unresolved_key, count in selected:
        if "::" not in unresolved_key:
            continue
        entity_class, mention = unresolved_key.split("::", 1)
        entity_class = entity_class.strip().lower()
        mention = mention.strip()
        if not entity_class or not mention:
            continue

        canonical_id = f"{prefix_for_entity_class(entity_class)}.{slugify(mention)}"
        aliases = sorted({mention, normalize_key(mention)})

        entries.append(
            {
                "canonical_id": canonical_id,
                "canonical_label": mention,
                "entity_class": entity_class,
                "aliases": aliases,
                "source_count": int(count),
            }
        )

    payload = {
        "version": "v2-auto",
        "generated_from": str(report_path),
        "top_n": args.top_n,
        "entries": entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Generated alias expansion file: {output_path}")
    print(f"Entries: {len(entries)}")


if __name__ == "__main__":
    main()
