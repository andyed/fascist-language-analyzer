import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from extract_entities_langextract import EXAMPLES, PROMPT


DEFAULT_INPUT = "data/project_2025.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate LangExtract API calls/tokens/cost for a run configuration."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input text file path")
    parser.add_argument("--max-char-buffer", type=int, default=1200, help="Chunk size in characters")
    parser.add_argument("--extraction-passes", type=int, default=2, help="Sequential extraction passes")
    parser.add_argument(
        "--chars-per-token",
        type=float,
        default=4.0,
        help="Approximate chars per token for rough token estimation",
    )
    parser.add_argument(
        "--output-tokens-low",
        type=int,
        default=60,
        help="Low estimate output tokens per API call",
    )
    parser.add_argument(
        "--output-tokens-mid",
        type=int,
        default=120,
        help="Mid estimate output tokens per API call",
    )
    parser.add_argument(
        "--output-tokens-high",
        type=int,
        default=220,
        help="High estimate output tokens per API call",
    )
    parser.add_argument(
        "--input-price-per-1m",
        type=float,
        default=None,
        help="Optional price in USD per 1M input tokens",
    )
    parser.add_argument(
        "--output-price-per-1m",
        type=float,
        default=None,
        help="Optional price in USD per 1M output tokens",
    )
    parser.add_argument(
        "--input-points-per-1k",
        type=float,
        default=None,
        help="Optional points per 1K input tokens",
    )
    parser.add_argument(
        "--output-points-per-1k",
        type=float,
        default=None,
        help="Optional points per 1K output tokens",
    )
    parser.add_argument(
        "--long-context-threshold-tokens",
        type=int,
        default=200_000,
        help="Per-call token threshold for long-context rate multipliers",
    )
    parser.add_argument(
        "--long-context-input-multiplier",
        type=float,
        default=2.0,
        help="Input multiplier when threshold is exceeded",
    )
    parser.add_argument(
        "--long-context-output-multiplier",
        type=float,
        default=1.5,
        help="Output multiplier when threshold is exceeded",
    )
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = re.sub(r"\n\s*--- PAGE BREAK ---\s*\n", "\n", text)
    text = re.sub(r"\bPAGE\s+BREAK\b", "", text)
    return text


def estimate_cost(input_tokens: float, output_tokens: float, in_price: float, out_price: float) -> float:
    return (input_tokens / 1_000_000.0) * in_price + (output_tokens / 1_000_000.0) * out_price


def estimate_points(input_tokens: float, output_tokens: float, in_points: float, out_points: float) -> float:
    return (input_tokens / 1_000.0) * in_points + (output_tokens / 1_000.0) * out_points


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8")
    text = clean_text(raw_text)

    chars = len(text)
    chunks = math.ceil(chars / args.max_char_buffer)
    calls = chunks * args.extraction_passes

    prompt_chars = len(PROMPT)
    examples_chars = sum(
        len(example.text) + sum(len(extraction.extraction_text) for extraction in example.extractions)
        for example in EXAMPLES
    )

    chunk_tokens = args.max_char_buffer / args.chars_per_token
    overhead_tokens = (prompt_chars + examples_chars) / args.chars_per_token

    input_tokens_per_call = chunk_tokens + overhead_tokens
    long_context_applies = input_tokens_per_call > args.long_context_threshold_tokens
    input_multiplier = args.long_context_input_multiplier if long_context_applies else 1.0
    output_multiplier = args.long_context_output_multiplier if long_context_applies else 1.0

    total_input_tokens = input_tokens_per_call * calls

    output_tokens = {
        "low": calls * args.output_tokens_low,
        "mid": calls * args.output_tokens_mid,
        "high": calls * args.output_tokens_high,
    }

    result: dict[str, object] = {
        "input_file": str(input_path),
        "clean_chars": chars,
        "max_char_buffer": args.max_char_buffer,
        "estimated_chunks": chunks,
        "extraction_passes": args.extraction_passes,
        "estimated_api_calls": calls,
        "token_assumptions": {
            "chars_per_token": args.chars_per_token,
            "prompt_chars": prompt_chars,
            "examples_chars": examples_chars,
            "input_tokens_per_call_est": round(input_tokens_per_call, 2),
            "long_context_applies": long_context_applies,
            "long_context_threshold_tokens": args.long_context_threshold_tokens,
            "input_rate_multiplier": input_multiplier,
            "output_rate_multiplier": output_multiplier,
        },
        "estimated_input_tokens_total": round(total_input_tokens),
        "estimated_input_tokens_billed": round(total_input_tokens * input_multiplier),
        "estimated_output_tokens_total": output_tokens,
        "estimated_output_tokens_billed": {
            key: round(value * output_multiplier) for key, value in output_tokens.items()
        },
    }

    if args.input_price_per_1m is not None and args.output_price_per_1m is not None:
        cost_range = {
            "low": round(
                estimate_cost(
                    total_input_tokens * input_multiplier,
                    output_tokens["low"] * output_multiplier,
                    args.input_price_per_1m,
                    args.output_price_per_1m,
                ),
                4,
            ),
            "mid": round(
                estimate_cost(
                    total_input_tokens * input_multiplier,
                    output_tokens["mid"] * output_multiplier,
                    args.input_price_per_1m,
                    args.output_price_per_1m,
                ),
                4,
            ),
            "high": round(
                estimate_cost(
                    total_input_tokens * input_multiplier,
                    output_tokens["high"] * output_multiplier,
                    args.input_price_per_1m,
                    args.output_price_per_1m,
                ),
                4,
            ),
        }
        result["pricing"] = {
            "input_price_per_1m": args.input_price_per_1m,
            "output_price_per_1m": args.output_price_per_1m,
            "estimated_cost_usd": cost_range,
        }

    if args.input_points_per_1k is not None and args.output_points_per_1k is not None:
        points_range = {
            "low": round(
                estimate_points(
                    total_input_tokens * input_multiplier,
                    output_tokens["low"] * output_multiplier,
                    args.input_points_per_1k,
                    args.output_points_per_1k,
                ),
                2,
            ),
            "mid": round(
                estimate_points(
                    total_input_tokens * input_multiplier,
                    output_tokens["mid"] * output_multiplier,
                    args.input_points_per_1k,
                    args.output_points_per_1k,
                ),
                2,
            ),
            "high": round(
                estimate_points(
                    total_input_tokens * input_multiplier,
                    output_tokens["high"] * output_multiplier,
                    args.input_points_per_1k,
                    args.output_points_per_1k,
                ),
                2,
            ),
        }
        result["points_pricing"] = {
            "input_points_per_1k": args.input_points_per_1k,
            "output_points_per_1k": args.output_points_per_1k,
            "estimated_cost_points": points_range,
        }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
