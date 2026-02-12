import json
import os

# Substrings to identify quotes to remove
REMOVE_SUBSTRINGS = [
    "The U.S. depends on reliable and cheap energy resources",
    "Mexico\u2014which is arguably functioning as a failed state",
    "part of the broader existential threat posed by the Chinese Communist Party",
    "Environmentalists, upset that too much of the land they coveted",
    "complete a thorough review of any sanctions or findings of misconduct",
    "cannot depend on the rapid development and deployment of untested, academically developed financial actions",
]

INPUT_FILE = "data/analysis_results.json"
OUTPUT_FILE = "data/analysis_results.json"

def curate_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    initial_count = sum(len(chunk.get('concepts', [])) for chunk in data)
    print(f"Initial concept count: {initial_count}")

    removed_count = 0
    for chunk in data:
        if 'concepts' in chunk:
            original_concepts = chunk['concepts']
            new_concepts = []
            for concept in original_concepts:
                quote = concept.get('quote', '')
                
                # Check for matches
                matched = False
                for substr in REMOVE_SUBSTRINGS:
                    if substr in quote:
                        print(f"Removing: {quote[:50]}... (matched '{substr[:20]}...')")
                        matched = True
                        break
                
                if not matched:
                    new_concepts.append(concept)
                else:
                    removed_count += 1
            
            chunk['concepts'] = new_concepts

    print(f"Removed {removed_count} items.")
    final_count = sum(len(chunk.get('concepts', [])) for chunk in data)
    print(f"Final concept count: {final_count}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Saved curated data to {OUTPUT_FILE}")

if __name__ == "__main__":
    curate_data()
