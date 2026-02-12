import os
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

INPUT_FILE = "data/project_2025.txt"
CHUNK_SIZE = 4000
CHUNK_OVERLAP = 200
MODEL_NAME = "gpt-4o"

# Approximate Pricing (OpenAI Direct)
# Input: $5.00 / 1M tokens
# Output: $15.00 / 1M tokens
PRICE_INPUT_PER_1M = 5.00
PRICE_OUTPUT_PER_1M = 15.00

# Estimated output tokens per chunk (based on pilot run of ~3-4 concepts/chunk)
# A concept JSON is roughly ~150-200 tokens? 
# Let's be conservative: 500 output tokens per chunk.
EST_OUTPUT_TOKENS_PER_CHUNK = 500 

def estimate_cost():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    # Split into chunks (same logic as main.py)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n--- PAGE BREAK ---\n\n", "\n\n", "\n", " ", ""]
    )
    docs = splitter.create_documents([text])
    num_chunks = len(docs)
    
    # Token counting
    encoding = tiktoken.encoding_for_model(MODEL_NAME)
    
    total_input_tokens = 0
    # Add system prompt overhead (approximate)
    SYSTEM_PROMPT_TOKENS = 500 
    
    print("Counting tokens...")
    for doc in docs:
        tokens = len(encoding.encode(doc.page_content))
        total_input_tokens += tokens + SYSTEM_PROMPT_TOKENS

    total_output_tokens = num_chunks * EST_OUTPUT_TOKENS_PER_CHUNK
    
    cost_input_gpt4o = (total_input_tokens / 1_000_000) * PRICE_INPUT_PER_1M
    cost_output_gpt4o = (total_output_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M
    total_cost_gpt4o = cost_input_gpt4o + cost_output_gpt4o

    # Gemini 1.5 Flash Pricing (Approx)
    # Input: $0.075 / 1M
    # Output: $0.30 / 1M
    PRICE_INPUT_FLASH = 0.075
    PRICE_OUTPUT_FLASH = 0.30
    
    cost_input_flash = (total_input_tokens / 1_000_000) * PRICE_INPUT_FLASH
    cost_output_flash = (total_output_tokens / 1_000_000) * PRICE_OUTPUT_FLASH
    total_cost_flash = cost_input_flash + cost_output_flash

    print("\n--- Cost Estimate Comparison ---")
    print(f"Total Chunks: {num_chunks}")
    print(f"Total Input Tokens (est): {total_input_tokens:,}")
    print(f"Total Output Tokens (est): {total_output_tokens:,}")
    print("\nGPT-4o:")
    print(f"  Cost: ${total_cost_gpt4o:.2f}")
    print(f"  Poe Points (est 400/msg): {num_chunks * 400:,}")
    
    print("\nGemini 1.5 Flash:")
    print(f"  Cost: ${total_cost_flash:.2f}")
    print(f"  Poe Points (est 20/msg): {num_chunks * 20:,}")
    print("---------------------------------")

if __name__ == "__main__":
    estimate_cost()
