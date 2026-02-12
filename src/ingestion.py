import os
from langchain_community.document_loaders import PyPDFLoader

# Configuration
PDF_PATH = "2025_MandateForLeadership_FULL.pdf"
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "project_2025.txt")

def ingest_pdf():
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}")
        return

    print(f"Loading {PDF_PATH}...")
    loader = PyPDFLoader(PDF_PATH)
    pages = loader.load()
    
    print(f"Loaded {len(pages)} pages.")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"Writing text to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for page in pages:
            f.write(page.page_content)
            f.write("\n\n--- PAGE BREAK ---\n\n")
            
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_pdf()
