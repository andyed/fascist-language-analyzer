import json
import collections

INPUT_FILE = "data/analysis_results.json"

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

def generate_histogram():
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found.")
        return

    trait_counts = collections.Counter()
    for chunk in data:
        for concept in chunk.get("concepts", []):
            trait = concept["trait"]
            trait_counts[trait] += 1

    # Sort by count descending
    sorted_traits = trait_counts.most_common()
    max_count = sorted_traits[0][1] if sorted_traits else 1
    max_label_len = max(len(t) for t in TRAIT_COLORS.keys())

    print("\n### Trait Frequency Histogram\n")
    print("```text")
    for trait, count in sorted_traits:
        bar_len = int((count / max_count) * 40)
        bar = "█" * bar_len
        label = trait.ljust(max_label_len)
        print(f"{label} | {bar} ({count})")
    print("```\n")

if __name__ == "__main__":
    generate_histogram()
