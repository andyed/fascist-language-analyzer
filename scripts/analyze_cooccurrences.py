
import json
from collections import Counter
from itertools import combinations

# Load the data
with open('web/public/data.json', 'r') as f:
    data = json.load(f)

# Count co-occurrences
pair_counts = Counter()
trait_counts = Counter()

for chunk in data:
    concepts = chunk.get('concepts', [])
    traits = sorted(list(set(c['trait'] for c in concepts)))
    
    # Update individual trait counts
    for trait in traits:
        trait_counts[trait] += 1
        
    # Update pair counts
    for pair in combinations(traits, 2):
        pair_counts[pair] += 1

# Print Results
print("--- Top 20 Trait Co-occurrences ---")
for pair, count in pair_counts.most_common(20):
    print(f"{count}: {pair[0]} <---> {pair[1]}")

print("\n--- Individual Trait Counts ---")
for trait, count in trait_counts.most_common():
    print(f"{count}: {trait}")
