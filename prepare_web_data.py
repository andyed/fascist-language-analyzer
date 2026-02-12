import json
import os

INPUT_FILE = "data/analysis_results.json"
OUTPUT_FILE = "web/public/graph_data.json"

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

def transform_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    nodes = []
    links = []
    
    # Track existing nodes to avoid duplicates
    existing_nodes = set()


    # Create Trait Nodes first (they are the hubs)
    for trait, color in TRAIT_COLORS.items():
        nodes.append({
            "id": trait,
            "group": "trait",
            "color": color,
            "val": 20 # Size
        })
        existing_nodes.add(trait)

    # Helper function to normalize trait names
    def normalize_trait(t):
        # Remove leading numbers and dots (e.g., "1. Cult..." -> "Cult...")
        if t[0].isdigit():
            parts = t.split(' ', 1)
            if len(parts) > 1:
                return parts[1].strip()
        return t

    for chunk in data:
        chunk_id = f"Chunk {chunk['chunk_id']}"
        
        # Add Chunk Node
        if chunk_id not in existing_nodes:
            nodes.append({
                "id": chunk_id,
                "group": "chunk",
                "color": "#666",
                "val": 5,
                "desc": chunk.get("summary", "No summary")
            })
            existing_nodes.add(chunk_id)
            
        # Add Links (and normalize traits in the process)
        for concept in chunk.get("concepts", []):
            raw_trait = concept["trait"]
            trait = normalize_trait(raw_trait)
            
            # Update the concept in the original data to use the normalized name
            concept["trait"] = trait
            
            if trait not in existing_nodes:
                # Should have been added, but just in case of typo/mismatch
                # strict matching against TRAIT_COLORS keys might fail if the key itself has a number
                # distinct from the data. Assuming TRAIT_COLORS keys are canonical.
                # If trait is not in TRAIT_COLORS, check if we can map it.
                canonical_trait = next((k for k in TRAIT_COLORS if normalize_trait(k) == trait), trait)
                
                if canonical_trait not in existing_nodes:
                     nodes.append({
                        "id": canonical_trait,
                        "group": "trait",
                        "color": TRAIT_COLORS.get(canonical_trait, "#ccc"),
                        "val": 20
                    })
                     existing_nodes.add(canonical_trait)
                trait = canonical_trait

            links.append({
                "source": chunk_id,
                "target": trait,
                "value": concept["confidence"]
            })

    # --- NEW: Add Structural Links (Trait <-> Trait) ---
    # These edges pull related traits together in the layout
    
    # Calculate co-occurrences
    pair_counts = {}
    for chunk in data:
        traits = sorted(list(set(normalize_trait(c["trait"]) for c in chunk.get("concepts", []))))
        for i in range(len(traits)):
            for j in range(i + 1, len(traits)):
                t1, t2 = traits[i], traits[j]
                key = (t1, t2)
                pair_counts[key] = pair_counts.get(key, 0) + 1

    # Add edges for strong connections
    for (t1, t2), count in pair_counts.items():
        if count >= 3: # Threshold to avoid noise
            links.append({
                "source": t1,
                "target": t2,
                "value": count * 2, # Stronger pull for structural links
                "type": "structural", # Mark them so frontend can treat differently
                "color": "rgba(0,0,0,0.1)" # Faint line
            })

    output = {
        "nodes": nodes,
        "links": links
    }

    # Ensure output directory exists (web/public)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        
    # Also copy the full analysis results for the text view
    FULL_DATA_OUTPUT = "web/public/data.json"
    with open(FULL_DATA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Graph data saved to {OUTPUT_FILE}")
    print(f"Full data saved to {FULL_DATA_OUTPUT}")
    print(f"Nodes: {len(nodes)}, Links: {len(links)}")

if __name__ == "__main__":
    transform_data()
