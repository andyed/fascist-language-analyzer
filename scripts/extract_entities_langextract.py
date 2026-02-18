import argparse
import os
import re
import textwrap
from pathlib import Path

import langextract as lx
from dotenv import load_dotenv
from langextract.providers.openai import OpenAILanguageModel

load_dotenv()

DEFAULT_INPUT = "data/project_2025.txt"
DEFAULT_JSONL = "data/entities_langextract.jsonl"
DEFAULT_HTML = "data/entities_langextract.html"

PROMPT = textwrap.dedent(
    """\
    Extract key entities and policy references in order of appearance.

    Allowed extraction classes:
    - person: named individual people
    - organization: non-government organizations, think tanks, media orgs, companies
    - government_agency: federal departments, agencies, offices, commissions, or branches
    - policy_program: named policy initiatives, policy frameworks, or recurring named plans
    - legal_reference: named laws, acts, executive orders, constitutional references, or court cases
    - location: named geographic places (city/state/country)

    Rules:
    - Use exact text spans from the source (no paraphrases).
    - Keep entities in order of first appearance.
    - Avoid overlap; prefer the most specific span.
    - Add short attributes to improve graphing utility.
    - If uncertain, skip the extraction.
    """
)

EXAMPLES = [
    lx.data.ExampleData(
        text=(
            "The Heritage Foundation published Project 2025 in Washington, DC. "
            "Kevin D. Roberts wrote the foreword."
        ),
        extractions=[
            lx.data.Extraction(
                extraction_class="organization",
                extraction_text="The Heritage Foundation",
                attributes={"role": "publisher"},
            ),
            lx.data.Extraction(
                extraction_class="policy_program",
                extraction_text="Project 2025",
                attributes={"type": "transition plan"},
            ),
            lx.data.Extraction(
                extraction_class="location",
                extraction_text="Washington, DC",
                attributes={"kind": "city"},
            ),
            lx.data.Extraction(
                extraction_class="person",
                extraction_text="Kevin D. Roberts",
                attributes={"role": "author"},
            ),
        ],
    ),
    lx.data.ExampleData(
        text=(
            "The Department of Homeland Security implemented policy under the "
            "Immigration and Nationality Act."
        ),
        extractions=[
            lx.data.Extraction(
                extraction_class="government_agency",
                extraction_text="Department of Homeland Security",
                attributes={"level": "federal"},
            ),
            lx.data.Extraction(
                extraction_class="legal_reference",
                extraction_text="Immigration and Nationality Act",
                attributes={"kind": "federal law"},
            ),
        ],
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract key entities from Project 2025 using google/langextract."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input .txt file path")
    parser.add_argument("--jsonl-output", default=DEFAULT_JSONL, help="Output JSONL path")
    parser.add_argument("--html-output", default=DEFAULT_HTML, help="Output HTML visualization path")
    parser.add_argument(
        "--model-id",
        default="gemini-2.5-flash",
        help="Model id to use (e.g. gemini-2.5-flash, gpt-4o)",
    )
    parser.add_argument(
        "--extraction-passes",
        type=int,
        default=2,
        help="Number of extraction passes for improved recall",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=20,
        help="Parallel workers for long-document extraction",
    )
    parser.add_argument(
        "--batch-length",
        type=int,
        default=20,
        help="Chunks processed per batch (set >= max-workers for full parallelism)",
    )
    parser.add_argument(
        "--max-char-buffer",
        type=int,
        default=1200,
        help="Chunk-local context window (smaller can improve precision)",
    )
    parser.add_argument(
        "--provider-mode",
        choices=["auto", "native", "poe"],
        default="auto",
        help="Model routing mode: native api key, Poe OpenAI-compatible endpoint, or auto",
    )
    return parser.parse_args()


def get_api_key(model_id: str) -> str | None:
    if model_id.startswith("gpt-"):
        return os.getenv("OPENAI_API_KEY")
    return os.getenv("LANGEXTRACT_API_KEY")


def build_extract_kwargs(args: argparse.Namespace, text: str) -> tuple[dict, str]:
    base_kwargs = {
        "text_or_documents": text,
        "prompt_description": PROMPT,
        "examples": EXAMPLES,
        "model_id": args.model_id,
        "extraction_passes": args.extraction_passes,
        "max_workers": args.max_workers,
        "batch_length": args.batch_length,
        "max_char_buffer": args.max_char_buffer,
        "resolver_params": {"suppress_parse_errors": True},
    }

    api_key = get_api_key(args.model_id)
    poe_key = os.getenv("POE_API_KEY")
    poe_base = os.getenv("POE_API_BASE")

    use_poe = args.provider_mode == "poe" or (
        args.provider_mode == "auto" and not api_key and poe_key and poe_base
    )

    if use_poe:
        model = OpenAILanguageModel(
            model_id=args.model_id,
            api_key=poe_key,
            base_url=poe_base,
            max_workers=args.max_workers,
        )
        base_kwargs.update(
            {
                "model": model,
                "fence_output": True,
                "use_schema_constraints": False,
            }
        )
        return base_kwargs, "poe-openai-compatible"

    if api_key:
        base_kwargs["api_key"] = api_key

    if args.model_id.startswith("gpt-"):
        base_kwargs["fence_output"] = True
        base_kwargs["use_schema_constraints"] = False

    return base_kwargs, "native"


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    jsonl_output = Path(args.jsonl_output)
    html_output = Path(args.html_output)
    jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    html_output.parent.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding="utf-8")
    text = re.sub(r"\n\s*--- PAGE BREAK ---\s*\n", "\n", text)
    text = re.sub(r"\bPAGE\s+BREAK\b", "", text)
    extract_kwargs, mode_label = build_extract_kwargs(args, text)

    print(f"Running extraction on: {input_path}")
    print(f"Model: {args.model_id}")
    print(f"Provider mode: {mode_label}")

    result = lx.extract(**extract_kwargs)

    lx.io.save_annotated_documents(
        [result], output_name=jsonl_output.name, output_dir=str(jsonl_output.parent)
    )

    html_content = lx.visualize(str(jsonl_output))
    with html_output.open("w", encoding="utf-8") as handle:
        if hasattr(html_content, "data"):
            handle.write(html_content.data)
        else:
            handle.write(html_content)

    print(f"Saved JSONL: {jsonl_output}")
    print(f"Saved HTML visualization: {html_output}")


if __name__ == "__main__":
    main()
