import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_GOLD = "data/gold/entities_gold_v0.jsonl"
DEFAULT_PRED = "data/gold/entities_pred_v0.jsonl"
DEFAULT_REPORT = "data/gold/entities_eval_report_v0.json"
SUFFIX_TOKENS = {"phd", "md", "jr", "sr"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate entity extraction predictions against a JSONL gold set."
    )
    parser.add_argument("--gold", default=DEFAULT_GOLD, help="Gold JSONL path")
    parser.add_argument("--pred", default=DEFAULT_PRED, help="Prediction JSONL path")
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Output report JSON path")
    parser.add_argument(
        "--mode",
        choices=["strict", "lenient"],
        default="strict",
        help="Matching mode: strict exact match or lenient boundary/acronym-aware match",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extraction_key(extraction: dict[str, Any]) -> tuple[str, str]:
    extraction_class = str(extraction.get("extraction_class", "")).strip().lower()
    extraction_text = normalize_text(str(extraction.get("extraction_text", "")))
    return extraction_class, extraction_text


def _remove_person_suffixes(text: str) -> str:
    tokens = text.split()
    while tokens and tokens[-1] in SUFFIX_TOKENS:
        tokens.pop()
    return " ".join(tokens)


def _remove_trailing_acronym(text: str) -> str:
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


def text_variants(entity_class: str, text: str, mode: str) -> set[str]:
    variants = {text}
    if mode == "strict":
        return variants

    if text.startswith("the "):
        variants.add(text[4:])

    if text.startswith("u s "):
        variants.add(text[4:])

    stripped_acronym = _remove_trailing_acronym(text)
    variants.add(stripped_acronym)

    if entity_class == "person":
        variants.update({_remove_person_suffixes(x) for x in list(variants)})

    return {v.strip() for v in variants if v.strip()}


def are_equivalent(entity_class: str, gold_text: str, pred_text: str, mode: str) -> bool:
    if mode == "strict":
        return gold_text == pred_text

    gold_variants = text_variants(entity_class, gold_text, mode)
    pred_variants = text_variants(entity_class, pred_text, mode)

    if gold_variants & pred_variants:
        return True

    containment_classes = {"policy_program", "government_agency", "legal_reference", "location"}
    if entity_class in containment_classes:
        for gold_value in gold_variants:
            for pred_value in pred_variants:
                if len(gold_value) >= 8 and len(pred_value) >= 8 and (
                    gold_value in pred_value or pred_value in gold_value
                ):
                    return True
    return False


def score_record(
    gold_extractions: list[dict[str, Any]],
    pred_extractions: list[dict[str, Any]],
    mode: str,
) -> dict[str, Any]:
    gold_items = [
        {"entity_class": extraction_key(item)[0], "text": extraction_key(item)[1]}
        for item in gold_extractions
    ]
    pred_items = [
        {"entity_class": extraction_key(item)[0], "text": extraction_key(item)[1]}
        for item in pred_extractions
    ]

    matched_gold: set[int] = set()
    matched_pred: set[int] = set()

    for gold_index, gold_item in enumerate(gold_items):
        for pred_index, pred_item in enumerate(pred_items):
            if pred_index in matched_pred:
                continue
            if gold_item["entity_class"] != pred_item["entity_class"]:
                continue
            if gold_item["text"] == pred_item["text"]:
                matched_gold.add(gold_index)
                matched_pred.add(pred_index)
                break

    if mode == "lenient":
        for gold_index, gold_item in enumerate(gold_items):
            if gold_index in matched_gold:
                continue
            for pred_index, pred_item in enumerate(pred_items):
                if pred_index in matched_pred:
                    continue
                if gold_item["entity_class"] != pred_item["entity_class"]:
                    continue
                if are_equivalent(gold_item["entity_class"], gold_item["text"], pred_item["text"], mode):
                    matched_gold.add(gold_index)
                    matched_pred.add(pred_index)
                    break

    unmatched_gold = [item for idx, item in enumerate(gold_items) if idx not in matched_gold]
    unmatched_pred = [item for idx, item in enumerate(pred_items) if idx not in matched_pred]

    return {
        "tp": len(matched_gold),
        "fp": len(unmatched_pred),
        "fn": len(unmatched_gold),
        "matched": [gold_items[idx] for idx in sorted(matched_gold)],
        "unmatched_gold": unmatched_gold,
        "unmatched_pred": unmatched_pred,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_num, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} line {line_num}: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected object in {path} line {line_num}, got {type(parsed)}")
            records.append(parsed)
    return records


def collect_extractions(record: dict[str, Any]) -> list[dict[str, Any]]:
    value = record.get("extractions")
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    return []


def make_record_id(record: dict[str, Any], index: int) -> str:
    value = record.get("id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"idx-{index:04d}"


def precision(tp: int, fp: int) -> float:
    return tp / (tp + fp) if (tp + fp) else 0.0


def recall(tp: int, fn: int) -> float:
    return tp / (tp + fn) if (tp + fn) else 0.0


def f1(p: float, r: float) -> float:
    return (2 * p * r / (p + r)) if (p + r) else 0.0


def main() -> None:
    args = parse_args()
    gold_path = Path(args.gold)
    pred_path = Path(args.pred)
    report_path = Path(args.report)

    if not gold_path.exists():
        raise FileNotFoundError(f"Gold file not found: {gold_path}")
    if not pred_path.exists():
        raise FileNotFoundError(f"Pred file not found: {pred_path}")

    gold_records = read_jsonl(gold_path)
    pred_records = read_jsonl(pred_path)

    pred_by_id: dict[str, dict[str, Any]] = {}
    for i, record in enumerate(pred_records):
        pred_by_id[make_record_id(record, i)] = record

    total_tp = 0
    total_fp = 0
    total_fn = 0

    per_class_counts: dict[str, Counter] = defaultdict(Counter)
    record_reports: list[dict[str, Any]] = []

    for i, gold_record in enumerate(gold_records):
        record_id = make_record_id(gold_record, i)
        pred_record = pred_by_id.get(record_id, {"id": record_id, "extractions": []})

        scored = score_record(
            collect_extractions(gold_record), collect_extractions(pred_record), args.mode
        )

        tp = int(scored["tp"])
        fp = int(scored["fp"])
        fn = int(scored["fn"])

        total_tp += tp
        total_fp += fp
        total_fn += fn

        for item in scored["matched"]:
            per_class_counts[item["entity_class"]]["tp"] += 1
        for item in scored["unmatched_pred"]:
            per_class_counts[item["entity_class"]]["fp"] += 1
        for item in scored["unmatched_gold"]:
            per_class_counts[item["entity_class"]]["fn"] += 1

        misses_counter = Counter((item["entity_class"], item["text"]) for item in scored["unmatched_gold"])
        fps_counter = Counter((item["entity_class"], item["text"]) for item in scored["unmatched_pred"])

        misses = [
            {"extraction_class": key[0], "extraction_text_normalized": key[1], "count": count}
            for key, count in misses_counter.items()
        ]
        false_positives = [
            {"extraction_class": key[0], "extraction_text_normalized": key[1], "count": count}
            for key, count in fps_counter.items()
        ]

        record_reports.append(
            {
                "id": record_id,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "misses": misses,
                "false_positives": false_positives,
            }
        )

    p = precision(total_tp, total_fp)
    r = recall(total_tp, total_fn)
    micro_f1 = f1(p, r)

    per_class_metrics: dict[str, dict[str, float | int]] = {}
    for entity_class, counts in per_class_counts.items():
        class_tp = int(counts.get("tp", 0))
        class_fp = int(counts.get("fp", 0))
        class_fn = int(counts.get("fn", 0))
        class_p = precision(class_tp, class_fp)
        class_r = recall(class_tp, class_fn)
        per_class_metrics[entity_class] = {
            "tp": class_tp,
            "fp": class_fp,
            "fn": class_fn,
            "precision": round(class_p, 4),
            "recall": round(class_r, 4),
            "f1": round(f1(class_p, class_r), 4),
        }

    report = {
        "gold_file": str(gold_path),
        "pred_file": str(pred_path),
        "mode": args.mode,
        "records_gold": len(gold_records),
        "records_pred": len(pred_records),
        "micro": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(micro_f1, 4),
        },
        "per_class": per_class_metrics,
        "records": record_reports,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print(f"Report written: {report_path}")
    print(f"Mode: {args.mode}")
    print(
        "Micro P/R/F1: "
        f"{report['micro']['precision']:.4f}/"
        f"{report['micro']['recall']:.4f}/"
        f"{report['micro']['f1']:.4f}"
    )
    print(f"TP/FP/FN: {total_tp}/{total_fp}/{total_fn}")


if __name__ == "__main__":
    main()
