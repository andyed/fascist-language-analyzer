import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INPUT = "data/entities_langextract.jsonl"
DEFAULT_OUTPUT = "data/entities_langextract.normalized.jsonl"
DEFAULT_REPORT = "data/entities_langextract.normalization_report.json"
DEFAULT_PERSON_GOLD = "data/gold/entities_gold_v0.jsonl"
DEFAULT_EXPANSION_FILE = "data/normalization_aliases_v2.json"
SUFFIX_TOKENS = {"phd", "md", "jr", "sr"}


CANONICAL_ENTITIES = [
    {
        "canonical_id": "agency.dhs",
        "canonical_label": "Department of Homeland Security",
        "entity_class": "government_agency",
        "aliases": [
            "department of homeland security",
            "u.s. department of homeland security",
            "dhs",
        ],
    },
    {
        "canonical_id": "agency.dod",
        "canonical_label": "Department of Defense",
        "entity_class": "government_agency",
        "aliases": ["department of defense", "u.s. department of defense", "dod"],
    },
    {
        "canonical_id": "agency.doj",
        "canonical_label": "Department of Justice",
        "entity_class": "government_agency",
        "aliases": ["department of justice", "u.s. department of justice", "doj"],
    },
    {
        "canonical_id": "agency.state",
        "canonical_label": "Department of State",
        "entity_class": "government_agency",
        "aliases": ["department of state", "u.s. department of state", "state department"],
    },
    {
        "canonical_id": "agency.hhs",
        "canonical_label": "Department of Health and Human Services",
        "entity_class": "government_agency",
        "aliases": [
            "department of health and human services",
            "u.s. department of health and human services",
            "hhs",
        ],
    },
    {
        "canonical_id": "agency.va",
        "canonical_label": "Department of Veterans Affairs",
        "entity_class": "government_agency",
        "aliases": ["department of veterans affairs", "u.s. department of veterans affairs", "va"],
    },
    {
        "canonical_id": "agency.usaid",
        "canonical_label": "U.S. Agency for International Development",
        "entity_class": "government_agency",
        "aliases": [
            "u.s. agency for international development",
            "us agency for international development",
            "usaid",
        ],
    },
    {
        "canonical_id": "agency.usagm",
        "canonical_label": "U.S. Agency for Global Media",
        "entity_class": "government_agency",
        "aliases": [
            "u.s. agency for global media",
            "us agency for global media",
            "agency for global media",
            "usagm",
        ],
    },
    {
        "canonical_id": "agency.omb",
        "canonical_label": "Office of Management and Budget",
        "entity_class": "government_agency",
        "aliases": ["office of management and budget", "omb"],
    },
    {
        "canonical_id": "agency.opm",
        "canonical_label": "Office of Personnel Management",
        "entity_class": "government_agency",
        "aliases": ["office of personnel management", "u.s. office of personnel management", "opm"],
    },
    {
        "canonical_id": "agency.epa",
        "canonical_label": "Environmental Protection Agency",
        "entity_class": "government_agency",
        "aliases": ["environmental protection agency", "epa", "u.s. environmental protection agency"],
    },
    {
        "canonical_id": "agency.fcc",
        "canonical_label": "Federal Communications Commission",
        "entity_class": "government_agency",
        "aliases": ["federal communications commission", "fcc"],
    },
    {
        "canonical_id": "agency.fec",
        "canonical_label": "Federal Election Commission",
        "entity_class": "government_agency",
        "aliases": ["federal election commission", "fec"],
    },
    {
        "canonical_id": "agency.ftc",
        "canonical_label": "Federal Trade Commission",
        "entity_class": "government_agency",
        "aliases": ["federal trade commission", "ftc"],
    },
    {
        "canonical_id": "agency.federal_reserve",
        "canonical_label": "Federal Reserve",
        "entity_class": "government_agency",
        "aliases": ["federal reserve", "federal reserve system", "the federal reserve"],
    },
    {
        "canonical_id": "agency.white_house",
        "canonical_label": "White House",
        "entity_class": "government_agency",
        "aliases": ["white house", "the white house"],
    },
    {
        "canonical_id": "agency.who",
        "canonical_label": "White House Office",
        "entity_class": "government_agency",
        "aliases": ["white house office", "who"],
    },
    {
        "canonical_id": "agency.eop",
        "canonical_label": "Executive Office of the President",
        "entity_class": "government_agency",
        "aliases": ["executive office of the president", "eop"],
    },
    {
        "canonical_id": "agency.nsc",
        "canonical_label": "National Security Council",
        "entity_class": "government_agency",
        "aliases": ["national security council", "nsc"],
    },
    {
        "canonical_id": "agency.nec",
        "canonical_label": "National Economic Council",
        "entity_class": "government_agency",
        "aliases": ["national economic council", "nec"],
    },
    {
        "canonical_id": "agency.dpc",
        "canonical_label": "Domestic Policy Council",
        "entity_class": "government_agency",
        "aliases": ["domestic policy council", "dpc"],
    },
    {
        "canonical_id": "agency.ola",
        "canonical_label": "Office of Legislative Affairs",
        "entity_class": "government_agency",
        "aliases": ["office of legislative affairs", "ola"],
    },
    {
        "canonical_id": "agency.opl",
        "canonical_label": "Office of Public Liaison",
        "entity_class": "government_agency",
        "aliases": ["office of public liaison", "opl"],
    },
    {
        "canonical_id": "agency.iga",
        "canonical_label": "Intergovernmental Affairs",
        "entity_class": "government_agency",
        "aliases": ["intergovernmental affairs", "iga"],
    },
    {
        "canonical_id": "organization.heritage",
        "canonical_label": "The Heritage Foundation",
        "entity_class": "organization",
        "aliases": ["the heritage foundation", "heritage foundation"],
    },
    {
        "canonical_id": "organization.freedomworks",
        "canonical_label": "FreedomWorks",
        "entity_class": "organization",
        "aliases": ["freedomworks"],
    },
    {
        "canonical_id": "organization.afpc",
        "canonical_label": "American Foreign Policy Council",
        "entity_class": "organization",
        "aliases": ["american foreign policy council"],
    },
    {
        "canonical_id": "organization.cfam",
        "canonical_label": "Center for Family and Human Rights",
        "entity_class": "organization",
        "aliases": ["center for family and human rights", "c-fam", "cfam"],
    },
    {
        "canonical_id": "organization.eppc",
        "canonical_label": "Ethics and Public Policy Center",
        "entity_class": "organization",
        "aliases": ["ethics and public policy center", "eppc"],
    },
    {
        "canonical_id": "program.project_2025",
        "canonical_label": "Project 2025",
        "entity_class": "policy_program",
        "aliases": [
            "project 2025",
            "the 2025 presidential transition project",
            "2025 presidential transition project",
            "mandate for leadership 2025",
            "mandate for leadership 2025 the conservative promise",
            "mandate for leadership: the conservative promise",
        ],
    },
    {
        "canonical_id": "law.immigration_nationality_act",
        "canonical_label": "Immigration and Nationality Act",
        "entity_class": "legal_reference",
        "aliases": ["immigration and nationality act"],
    },
    {
        "canonical_id": "law.defense_production_act",
        "canonical_label": "Defense Production Act",
        "entity_class": "legal_reference",
        "aliases": ["defense production act"],
    },
    {
        "canonical_id": "legal.constitution",
        "canonical_label": "U.S. Constitution",
        "entity_class": "legal_reference",
        "aliases": ["constitution", "u.s. constitution", "the constitution"],
    },
    {
        "canonical_id": "location.washington_dc",
        "canonical_label": "Washington, DC",
        "entity_class": "location",
        "aliases": ["washington, dc", "washington dc", "dc"],
    },
    {
        "canonical_id": "location.united_states",
        "canonical_label": "United States",
        "entity_class": "location",
        "aliases": ["united states", "u.s.", "us", "america"],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize LangExtract entities into canonical IDs and labels."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input JSONL path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Normalized output JSONL path")
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Normalization report JSON path")
    parser.add_argument(
        "--expansion-file",
        default=DEFAULT_EXPANSION_FILE,
        help="Optional alias expansion JSON file produced from unresolved mentions",
    )
    parser.add_argument(
        "--disable-expansion-file",
        action="store_true",
        help="Disable loading of expansion aliases",
    )
    parser.add_argument(
        "--person-gold",
        default=DEFAULT_PERSON_GOLD,
        help="Optional gold JSONL used to derive person canonical aliases",
    )
    parser.add_argument(
        "--disable-person-canonical",
        action="store_true",
        help="Disable person canonical map derived from gold file",
    )
    parser.add_argument(
        "--mode",
        choices=["strict", "lenient"],
        default="lenient",
        help="Normalization mode for alias matching",
    )
    return parser.parse_args()


def normalize_key(text: str) -> str:
    text = text.strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_person_suffixes(text: str) -> str:
    tokens = text.split()
    while tokens and tokens[-1] in SUFFIX_TOKENS:
        tokens.pop()
    return " ".join(tokens)


def remove_trailing_acronym(text: str) -> str:
    tokens = text.split()
    if len(tokens) < 3:
        return text

    last = tokens[-1]
    if not (2 <= len(last) <= 6 and last.isalpha()):
        return text

    stop_tokens = {"of", "and", "the", "for", "to", "in", "on", "a", "an"}
    initials = "".join(token[0] for token in tokens[:-1] if token and token not in stop_tokens)
    if initials == last:
        return " ".join(tokens[:-1])
    return text


def normalized_variants(entity_class: str, mention: str, mode: str) -> list[str]:
    base = normalize_key(mention)
    variants = {base}

    if mode == "lenient":
        if base.startswith("the "):
            variants.add(base[4:])
        if base.startswith("u s "):
            variants.add(base[4:])
        variants.add(remove_trailing_acronym(base))

        if entity_class == "person":
            variants |= {remove_person_suffixes(value) for value in list(variants)}

    return [value for value in variants if value]


def build_alias_index() -> tuple[dict[tuple[str, str], dict[str, str]], list[dict[str, str]]]:
    alias_index: dict[tuple[str, str], dict[str, str]] = {}
    collisions: list[dict[str, str]] = []

    for entity in CANONICAL_ENTITIES:
        entity_class = entity["entity_class"]
        payload = {
            "canonical_id": entity["canonical_id"],
            "canonical_label": entity["canonical_label"],
        }

        for alias in entity["aliases"]:
            key = (entity_class, normalize_key(alias))
            existing = alias_index.get(key)
            if existing and existing["canonical_id"] != payload["canonical_id"]:
                collisions.append(
                    {
                        "entity_class": entity_class,
                        "alias": alias,
                        "normalized_alias": key[1],
                        "existing_id": existing["canonical_id"],
                        "new_id": payload["canonical_id"],
                    }
                )
            else:
                alias_index[key] = payload
    return alias_index, collisions


def _person_id_from_label(label: str) -> str:
    return f"person.{normalize_key(label).replace(' ', '_')[:80]}"


def build_person_catalog_from_gold(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    people: dict[str, set[str]] = {}

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            extractions = record.get("extractions")
            if not isinstance(extractions, list):
                continue

            for extraction in extractions:
                if not isinstance(extraction, dict):
                    continue
                if str(extraction.get("extraction_class", "")).strip().lower() != "person":
                    continue
                mention = str(extraction.get("extraction_text", "")).strip()
                if not mention:
                    continue

                canonical_label = remove_person_suffixes(normalize_key(mention)).title()
                aliases = {
                    normalize_key(mention),
                    remove_person_suffixes(normalize_key(mention)),
                }

                if canonical_label not in people:
                    people[canonical_label] = set()
                people[canonical_label] |= {alias for alias in aliases if alias}

    catalog: list[dict[str, Any]] = []
    for canonical_label, aliases in sorted(people.items()):
        catalog.append(
            {
                "canonical_id": _person_id_from_label(canonical_label),
                "canonical_label": canonical_label,
                "entity_class": "person",
                "aliases": sorted(aliases),
            }
        )
    return catalog


def add_entities_to_alias_index(
    alias_index: dict[tuple[str, str], dict[str, str]],
    collisions: list[dict[str, str]],
    entities: list[dict[str, Any]],
    source: str,
) -> None:
    for entity in entities:
        entity_class = entity["entity_class"]
        payload = {
            "canonical_id": entity["canonical_id"],
            "canonical_label": entity["canonical_label"],
        }

        for alias in entity.get("aliases", []):
            key = (entity_class, normalize_key(str(alias)))
            existing = alias_index.get(key)
            if existing and existing["canonical_id"] != payload["canonical_id"]:
                collisions.append(
                    {
                        "entity_class": entity_class,
                        "alias": str(alias),
                        "normalized_alias": key[1],
                        "existing_id": existing["canonical_id"],
                        "new_id": payload["canonical_id"],
                        "source": source,
                    }
                )
            else:
                alias_index[key] = payload


def load_expansion_entities(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return []

    valid_entries: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entity_class = str(entry.get("entity_class", "")).strip().lower()
        canonical_id = str(entry.get("canonical_id", "")).strip()
        canonical_label = str(entry.get("canonical_label", "")).strip()
        aliases = entry.get("aliases", [])
        if not (entity_class and canonical_id and canonical_label and isinstance(aliases, list)):
            continue
        valid_entries.append(
            {
                "entity_class": entity_class,
                "canonical_id": canonical_id,
                "canonical_label": canonical_label,
                "aliases": [str(alias) for alias in aliases if str(alias).strip()],
            }
        )
    return valid_entries


def iter_extractions(node: Any):
    if isinstance(node, dict):
        if "extraction_class" in node and "extraction_text" in node:
            yield node
        for value in node.values():
            yield from iter_extractions(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_extractions(item)


def apply_normalization(
    record: dict[str, Any],
    alias_index: dict[tuple[str, str], dict[str, str]],
    stats: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    extraction_count = 0
    resolved_count = 0

    for extraction in iter_extractions(record):
        extraction_count += 1
        entity_class = str(extraction.get("extraction_class", "")).strip().lower()
        mention = str(extraction.get("extraction_text", "")).strip()
        variants = normalized_variants(entity_class, mention, mode)
        match = None
        matched_variant = None
        for variant in variants:
            candidate = alias_index.get((entity_class, variant))
            if candidate:
                match = candidate
                matched_variant = variant
                break

        if match:
            extraction["canonical_id"] = match["canonical_id"]
            extraction["canonical_label"] = match["canonical_label"]
            extraction["normalization_method"] = (
                "alias_exact" if matched_variant == normalize_key(mention) else "alias_variant"
            )
            extraction["normalized"] = True
            resolved_count += 1
            stats["resolved_by_id"][match["canonical_id"]] += 1
        else:
            extraction["canonical_id"] = f"raw.{entity_class}.{normalize_key(mention).replace(' ', '_')[:80]}"
            extraction["canonical_label"] = mention
            extraction["normalization_method"] = "passthrough"
            extraction["normalized"] = False
            stats["unresolved_mentions"][f"{entity_class}::{mention}"] += 1

    stats["records"] += 1
    stats["extractions"] += extraction_count
    stats["resolved"] += resolved_count
    return record


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_num, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_num}: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected JSON object at line {line_num}, got {type(parsed)}")
            records.append(parsed)
    return records


def save_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    report_path = Path(args.report)

    if not input_path.exists():
        raise FileNotFoundError(f"Input JSONL not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    records = load_jsonl(input_path)
    alias_index, collisions = build_alias_index()

    person_catalog_size = 0
    person_gold_path = Path(args.person_gold)
    if not args.disable_person_canonical:
        person_entities = build_person_catalog_from_gold(person_gold_path)
        person_catalog_size = len(person_entities)
        add_entities_to_alias_index(alias_index, collisions, person_entities, source="person_gold")

    expansion_catalog_size = 0
    expansion_path = Path(args.expansion_file)
    if not args.disable_expansion_file:
        expansion_entities = load_expansion_entities(expansion_path)
        expansion_catalog_size = len(expansion_entities)
        add_entities_to_alias_index(alias_index, collisions, expansion_entities, source="expansion_file")

    stats: dict[str, Any] = {
        "records": 0,
        "extractions": 0,
        "resolved": 0,
        "resolved_by_id": Counter(),
        "unresolved_mentions": Counter(),
    }

    normalized_records = [
        apply_normalization(record, alias_index, stats, args.mode) for record in records
    ]
    save_jsonl(output_path, normalized_records)

    resolved_rate = (stats["resolved"] / stats["extractions"] * 100.0) if stats["extractions"] else 0.0
    report = {
        "input": str(input_path),
        "output": str(output_path),
        "mode": args.mode,
        "records": stats["records"],
        "extractions": stats["extractions"],
        "resolved": stats["resolved"],
        "resolved_rate_percent": round(resolved_rate, 2),
        "alias_catalog_size": len(CANONICAL_ENTITIES),
        "person_catalog_size": person_catalog_size,
        "person_catalog_source": str(person_gold_path) if not args.disable_person_canonical else None,
        "expansion_catalog_size": expansion_catalog_size,
        "expansion_catalog_source": str(expansion_path) if not args.disable_expansion_file else None,
        "alias_index_size": len(alias_index),
        "alias_collisions": collisions,
        "top_resolved_ids": dict(Counter(stats["resolved_by_id"]).most_common(50)),
        "top_unresolved_mentions": dict(Counter(stats["unresolved_mentions"]).most_common(100)),
    }

    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print(f"Normalized records written to: {output_path}")
    print(f"Report written to: {report_path}")
    print(
        "Resolved "
        f"{stats['resolved']}/{stats['extractions']} extractions "
        f"({report['resolved_rate_percent']}%)"
    )


if __name__ == "__main__":
    main()
