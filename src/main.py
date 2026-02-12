import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.analysis import get_analyzer_chain
from src.schema import AnalysisResult

# Configuration
INPUT_FILE = "data/project_2025.txt"
OUTPUT_FILE = "data/analysis_results.json"
CHUNK_SIZE = 4000  # Characters (safe for GPT-4o context + system prompt)
CHUNK_OVERLAP = 200

def load_data():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"{INPUT_FILE} not found. Run ingestion.py first.")
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()
    return text

import asyncio
import time

async def process_chunk(sem, chain, doc, i, total):
    async with sem:
        try:
            # print(f"  Starting chunk {i+1}/{total}...") 
            result = await chain.ainvoke({"text": doc.page_content})
            
            # Convert Pydantic model to dict
            result_dict = result.dict()
            result_dict["chunk_id"] = i
            result_dict["source_text"] = doc.page_content[:100] + "..."
            
            if i % 10 == 0:
                print(f"Completed chunk {i+1}/{total}")
            
            return result_dict
            
        except Exception as e:
            print(f"  Error processing chunk {i}: {e}")
            return None

async def run_analysis_async():
    print("Loading data...")
    full_text = load_data()
    
    print("Splitting text...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n--- PAGE BREAK ---\n\n", "\n\n", "\n", " ", ""]
    )
    docs = splitter.create_documents([full_text])
    print(f"Created {len(docs)} chunks.")

    print("Initializing chain...")
    try:
        chain = get_analyzer_chain()
    except ValueError as e:
        print(f"Error: {e}")
        return

    print(f"Starting full parallel analysis of {len(docs)} chunks...")
    start_time = time.time()
    
    # Validation: Run one chunk first to ensure it works before spawning 1000
    print("Validating with single chunk...")
    await process_chunk(asyncio.Semaphore(1), chain, docs[0], 0, len(docs))
    print("Validation successful. Launching batch...")

    sem = asyncio.Semaphore(20) # Limit concurrency to avoid rate limits
    # Full Run
    print(f"Starting FULL analysis of {len(docs)} chunks...")
    
    tasks = []
    for i, doc in enumerate(docs):
        task = asyncio.create_task(process_chunk(sem, chain, doc, i, len(docs)))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # Filter out None results
    valid_results = [r for r in results if r is not None]
    
    # Sort by chunk_id to maintain order
    valid_results.sort(key=lambda x: x["chunk_id"])

    print(f"Saving {len(valid_results)} results to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(valid_results, f, indent=2)
        
    elapsed = time.time() - start_time
    print(f"Analysis complete in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(run_analysis_async())
