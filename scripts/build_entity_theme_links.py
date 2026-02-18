import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_ANALYSIS = "data/analysis_results.json"
DEFAULT_ENTITIES = "web/public/entities_data.json"
DEFAULT_OUTPUT = "web/public/entity_theme_data.json"
DEFAULT_SOURCE_DOC_URL = "https://www.project2025.observer/en"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build entity-theme co-mention links from analysis quotes."
    )
    parser.add_argument("--analysis", default=DEFAULT_ANALYSIS, help="Analysis JSON path")
    parser.add_argument("--entities", default=DEFAULT_ENTITIES, help="Entity data JSON path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path")
    parser.add_argument(
        "--score-mode",
        choices=["raw", "lift", "pmi"],
        default="raw",
        help="Edge ranking/visualization score",
    )
    parser.add_argument(
        "--source-doc-url",
        default=DEFAULT_SOURCE_DOC_URL,
        help="Canonical source document URL to include with evidence",
    )
    parser.add_argument(
        "--max-entities",
        type=int,
        default=300,
        help="Max entities (by mention count) considered for matching",
    )
    parser.add_argument(
        "--max-links",
        type=int,
        default=1200,
        help="Max links to keep in output",
    )
    parser.add_argument(
        "--max-evidence",
        type=int,
        default=2,
        help="Max evidence quotes per entity-theme edge",
    )
    return parser.parse_args()


def canonical_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def normalize_phrase(text: str) -> str:
    return canonical_space(text).lower()


def phrase_in_text(text_lower: str, phrase: str) -> bool:
    phrase = normalize_phrase(phrase)
    if not phrase:
        return False

    # Skip tiny/ambiguous aliases.
    alnum = re.sub(r"[^a-z0-9]", "", phrase)
    if len(alnum) < 4:
        return False

    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text_lower) is not None


def load_entities(path: Path, max_entities: int) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    all_entities = []
    classes = payload.get("classes", {})

    for class_id, entities in classes.items():
        for entity in entities:
            aliases = []
            label = entity.get("label", "")
            if label:
                aliases.append(label)
            aliases.extend(entity.get("mention_samples", []))

            dedup_aliases = []
            seen = set()
            for alias in aliases:
                key = normalize_phrase(alias)
                if key and key not in seen:
                    seen.add(key)
                    dedup_aliases.append(alias)

            all_entities.append(
                {
                    "id": entity["id"],
                    "label": entity.get("label", entity["id"]),
                    "entity_class": class_id,
                    "count": entity.get("count", 0),
                    "aliases": dedup_aliases,
                }
            )

    all_entities.sort(key=lambda e: (-e["count"], e["label"].lower()))
    if max_entities > 0:
        all_entities = all_entities[:max_entities]
    return all_entities


def main() -> None:
    args = parse_args()

    analysis_path = Path(args.analysis)
    entities_path = Path(args.entities)
    output_path = Path(args.output)

    if not analysis_path.exists():
        raise FileNotFoundError(f"Analysis file not found: {analysis_path}")
    if not entities_path.exists():
        raise FileNotFoundError(f"Entity file not found: {entities_path}")

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    entities = load_entities(entities_path, args.max_entities)

    edge_weights: dict[tuple[str, str], dict] = {}
    theme_counts = Counter()
    entity_match_counts = Counter()
    total_concepts = 0

    for chunk in analysis:
        for concept in chunk.get("concepts", []):
            theme = concept.get("trait")
            quote = canonical_space(concept.get("quote", ""))
            explanation = canonical_space(concept.get("explanation", ""))
            confidence = float(concept.get("confidence", 0.5) or 0.5)
            chunk_id = chunk.get("chunk_id")

            if not theme or not quote:
                continue

            total_concepts += 1
            theme_counts[theme] += 1
            body_lower = normalize_phrase(f"{quote} {explanation}")

            matched_entity_ids = []
            for entity in entities:
                if any(phrase_in_text(body_lower, alias) for alias in entity["aliases"]):
                    matched_entity_ids.append(entity["id"])

            for entity_id in matched_entity_ids:
                entity_match_counts[entity_id] += 1
                key = (entity_id, theme)
                rec = edge_weights.get(key)
                if rec is None:
                    rec = {
                        "entity_id": entity_id,
                        "theme": theme,
                        "raw_weight": 0.0,
                        "count": 0,
                        "evidence": [],
                    }
                    edge_weights[key] = rec

                rec["raw_weight"] += confidence
                rec["count"] += 1
                if quote and len(rec["evidence"]) < args.max_evidence:
                    candidate = {
                        "quote": quote,
                        "chunk_id": chunk_id,
                        "confidence": round(confidence, 3),
                        "source_url": args.source_doc_url,
                    }
                    if candidate not in rec["evidence"]:
                        rec["evidence"].append(candidate)

    epsilon = 1e-12
    for rec in edge_weights.values():
        entity_count = entity_match_counts[rec["entity_id"]]
        theme_count = theme_counts[rec["theme"]]
        joint_count = rec["count"]

        p_entity = entity_count / max(total_concepts, 1)
        p_theme = theme_count / max(total_concepts, 1)
        p_joint = joint_count / max(total_concepts, 1)

        lift = p_joint / max(p_entity * p_theme, epsilon)
        pmi = math.log2((p_joint + epsilon) / max(p_entity * p_theme, epsilon))

        rec["lift"] = round(lift, 6)
        rec["pmi"] = round(pmi, 6)
        rec["weight"] = round(rec["raw_weight"], 6)

        if args.score_mode == "lift":
            rec["score"] = rec["lift"]
        elif args.score_mode == "pmi":
            rec["score"] = rec["pmi"]
        else:
            rec["score"] = rec["weight"]

    entity_lookup = {entity["id"]: entity for entity in entities}

    links = list(edge_weights.values())
    links.sort(key=lambda l: (-l["score"], -l["weight"], -l["count"], l["theme"], l["entity_id"]))
    if args.max_links > 0:
        links = links[: args.max_links]

    used_entity_ids = sorted({link["entity_id"] for link in links})
    used_themes = sorted({link["theme"] for link in links})

    graph_nodes = []
    for theme in used_themes:
        graph_nodes.append(
            {
                "id": theme,
                "group": "theme",
                "label": theme,
                "val": max(8, theme_counts.get(theme, 0)),
            }
        )

    for entity_id in used_entity_ids:
        entity = entity_lookup[entity_id]
        graph_nodes.append(
            {
                "id": entity_id,
                "group": "entity",
                "label": entity["label"],
                "entity_class": entity["entity_class"],
                "count": entity["count"],
                "val": max(3, min(20, entity["count"] // 3 + 2)),
            }
        )

    graph_links = [
        {
            "source": link["entity_id"],
            "target": link["theme"],
            "value": round(link["score"], 3),
            "score_mode": args.score_mode,
            "raw_weight": round(link["weight"], 3),
            "lift": round(link["lift"], 3),
            "pmi": round(link["pmi"], 3),
            "count": link["count"],
        }
        for link in links
    ]

    top_edges = []
    for link in links[:200]:
        entity = entity_lookup[link["entity_id"]]
        top_edges.append(
            {
                "entity_id": link["entity_id"],
                "entity_label": entity["label"],
                "entity_class": entity["entity_class"],
                "theme": link["theme"],
                "score_mode": args.score_mode,
                "weight": round(link["score"], 3),
                "raw_weight": round(link["weight"], 3),
                "lift": round(link["lift"], 3),
                "pmi": round(link["pmi"], 3),
                "count": link["count"],
                "evidence": link["evidence"],
            }
        )

    matrix = defaultdict(dict)
    for link in links:
        matrix[link["entity_id"]][link["theme"]] = round(link["score"], 3)

    output = {
        "meta": {
            "analysis_file": str(analysis_path),
            "entities_file": str(entities_path),
            "matching": "entity aliases matched in quote+explanation text",
            "score_mode": args.score_mode,
            "total_concepts_considered": total_concepts,
            "entity_pool_size": len(entities),
            "link_count": len(links),
            "theme_count": len(used_themes),
        },
        "themes": [{"id": t, "count": theme_counts.get(t, 0)} for t in used_themes],
        "entities": [entity_lookup[eid] for eid in used_entity_ids],
        "links": links,
        "top_edges": top_edges,
        "matrix": matrix,
        "graph": {"nodes": graph_nodes, "links": graph_links},
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Wrote {output_path}")
    print(f"Entities considered: {len(entities)}")
    print(f"Links kept: {len(links)}")


if __name__ == "__main__":
    main()
