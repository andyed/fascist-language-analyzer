from bs4 import BeautifulSoup
import os

FILE_GPT = "data/visualization_gpt4o.html"
FILE_GEMINI = "data/visualization_gemini.html"

def parse_html(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return None
        
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        
    chunks = soup.find_all("div", class_="chunk")
    data = {}
    
    total_concepts = 0
    all_confidences = []
    traits_found = {}
    
    for chunk in chunks:
        chunk_title = chunk.find("h3").text
        chunk_id = int(chunk_title.split(" ")[1])
        
        concepts = chunk.find_all("div", class_="quote-card")
        chunk_data = []
        
        for c in concepts:
            trait_tag = c.find("span", class_="trait-tag")
            trait_name = trait_tag.contents[0].strip()
            confidence_str = c.find("span", class_="confidence").text
            # Format: (Conf: 0.9)
            confidence = float(confidence_str.split(":")[1].strip().replace(")", ""))
            
            chunk_data.append({
                "trait": trait_name,
                "confidence": confidence
            })
            
            total_concepts += 1
            all_confidences.append(confidence)
            traits_found[trait_name] = traits_found.get(trait_name, 0) + 1
            
        data[chunk_id] = chunk_data
        
    avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0
    
    return {
        "total_concepts": total_concepts,
        "avg_confidence": avg_conf,
        "traits_distribution": traits_found,
        "chunks": data
    }

def compare():
    print("Parsing GPT-4o Results...")
    res_gpt = parse_html(FILE_GPT)
    
    print("Parsing Gemini Results...")
    res_gemini = parse_html(FILE_GEMINI)
    
    if not res_gpt or not res_gemini:
        return

    print("\n=== High Level Comparison (10 Pilot Chunks) ===")
    print(f"{'Metric':<25} | {'GPT-4o':<15} | {'Gemini-3-Flash':<15}")
    print("-" * 65)
    print(f"{'Total Concepts Found':<25} | {res_gpt['total_concepts']:<15} | {res_gemini['total_concepts']:<15}")
    print(f"{'Avg Confidence':<25} | {res_gpt['avg_confidence']:.2f}{'':<11} | {res_gemini['avg_confidence']:.2f}")
    
    print("\n=== Top Traits Identified ===")
    top_gpt = sorted(res_gpt['traits_distribution'].items(), key=lambda x: x[1], reverse=True)[:3]
    top_gemini = sorted(res_gemini['traits_distribution'].items(), key=lambda x: x[1], reverse=True)[:3]
    
    print("GPT-4o Top 3:")
    for t, c in top_gpt:
        print(f"  - {t}: {c}")
        
    print("\nGemini Top 3:")
    for t, c in top_gemini:
        print(f"  - {t}: {c}")

    print("\n=== Chunk-by-Chunk Count ===")
    print(f"{'Chunk':<6} | {'GPT-4o':<10} | {'Gemini':<10}")
    for i in sorted(res_gpt['chunks'].keys()):
        count_gpt = len(res_gpt['chunks'].get(i, []))
        count_gemini = len(res_gemini['chunks'].get(i, []))
        print(f"{i:<6} | {count_gpt:<10} | {count_gemini:<10}")

if __name__ == "__main__":
    compare()
