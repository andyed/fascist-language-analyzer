import os
from src.analysis import get_analyzer_chain
from langchain_core.output_parsers import PydanticOutputParser
from src.schema import AnalysisResult

# Sample text with clear authoritarian undertones (fictional for testing)
SAMPLE_TEXT = """
Our great nation is under siege by foreign influences and internal traitors who hate our traditional values. 
We must act now, without hesitation, to purge these elements. The intellectual elites and their critical theories 
only serve to weaken our resolve. Only through strength and unity can we return to our glorious past. 
Pacifism is a sickness that invites our enemies to destroy us.
"""

def test_analysis():
    print("Initializing chain...")
    try:
        chain = get_analyzer_chain()
    except ValueError as e:
        print(f"Error: {e}")
        return

    parser = PydanticOutputParser(pydantic_object=AnalysisResult)
    format_instructions = parser.get_format_instructions()

    print("Running analysis on sample text...")
    try:
        result = chain.invoke({
            "text": SAMPLE_TEXT,
            "format_instructions": format_instructions
        })
        
        print("\nanalysis Result:")
        print(f"Summary: {result.summary}\n")
        for concept in result.concepts:
            print(f"- Trait: {concept.trait}")
            print(f"  Quote: \"{concept.quote}\"")
            print(f"  Confidence: {concept.confidence}")
            print(f"  Explanation: {concept.explanation}\n")
            
    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    test_analysis()
