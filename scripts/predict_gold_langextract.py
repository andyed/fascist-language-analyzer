import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import langextract as lx
from dotenv import load_dotenv
from langextract.providers.openai import OpenAILanguageModel

sys.path.append(str(Path(__file__).resolve().parent))
from extract_entities_langextract import EXAMPLES, PROMPT

DEFAULT_GOLD = "data/gold/entities_gold_v0.jsonl"
DEFAULT_PRED = "data/gold/entities_pred_v0.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run LangExtract on gold snippets and write prediction JSONL."
    )
    parser.add_argument("--gold", default=DEFAULT_GOLD, help="Input gold JSONL")
    parser.add_argument("--pred", default=DEFAULT_PRED, help="Output prediction JSONL")
    parser.add_argument(
        "--model-id",
        default="Gemini-3-Flash",
        help="Poe model id exposed via OpenAI-compatible endpoint",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Parallel workers within each extraction call",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def extraction_to_dict(extraction: Any) -> dict[str, Any]:
    extraction_class = getattr(extraction, "extraction_class", None)
    extraction_text = getattr(extraction, "extraction_text", None)
    attributes = getattr(extraction, "attributes", None)
    result = {
        "extraction_class": str(extraction_class) if extraction_class is not None else "",
        "extraction_text": str(extraction_text) if extraction_text is not None else "",
    }
    if isinstance(attributes, dict) and attributes:
        result["attributes"] = attributes
    return result


def annotated_doc_to_extractions(doc: Any) -> list[dict[str, Any]]:
    extractions = getattr(doc, "extractions", None)
    if isinstance(extractions, list):
        return [extraction_to_dict(item) for item in extractions]
    return []


def main() -> None:
    args = parse_args()

    load_dotenv(dotenv_path=Path(".env"), override=False)
    poe_key = os.getenv("POE_API_KEY")
    poe_base = os.getenv("POE_API_BASE")

    if not poe_key or not poe_base:
        raise ValueError("POE_API_KEY and POE_API_BASE must be set in .env or environment")

    gold_path = Path(args.gold)
    pred_path = Path(args.pred)

    if not gold_path.exists():
        raise FileNotFoundError(f"Gold file not found: {gold_path}")

    pred_path.parent.mkdir(parents=True, exist_ok=True)
    gold_records = load_jsonl(gold_path)

    model = OpenAILanguageModel(
        model_id=args.model_id,
        api_key=poe_key,
        base_url=poe_base,
        max_workers=args.max_workers,
    )

    written = 0
    with pred_path.open("w", encoding="utf-8") as out:
        for i, record in enumerate(gold_records, start=1):
            snippet_id = record.get("id", f"idx-{i:04d}")
            text = str(record.get("text", ""))

            result = lx.extract(
                text_or_documents=text,
                prompt_description=PROMPT,
                examples=EXAMPLES,
                model=model,
                fence_output=True,
                use_schema_constraints=False,
                show_progress=False,
                extraction_passes=1,
                max_char_buffer=1200,
                max_workers=args.max_workers,
            )

            predicted = {
                "id": snippet_id,
                "text": text,
                "extractions": annotated_doc_to_extractions(result),
            }
            out.write(json.dumps(predicted, ensure_ascii=False) + "\n")
            written += 1
            if written % 5 == 0:
                print(f"Processed {written}/{len(gold_records)} snippets")

    print(f"Wrote predictions: {pred_path}")


if __name__ == "__main__":
    main()
