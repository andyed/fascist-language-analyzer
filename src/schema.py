from typing import List, Optional
from pydantic import BaseModel, Field

class FascistConcept(BaseModel):
    """
    Represents a specific instance of fascist rhetoric identified in the text.
    """
    quote: str = Field(..., description="The exact quote from the text.")
    trait: str = Field(..., description="The specific Ur-Fascism trait identified (e.g., 'Cult of Tradition', 'Disagreement is Treason').")
    explanation: str = Field(..., description="Reasoning for why this quote matches the trait.")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0.")

class AnalysisResult(BaseModel):
    """
    Container for the analysis of a document section.
    """
    concepts: List[FascistConcept] = Field(default_factory=list, description="List of identified fascist concepts.")
    summary: str = Field(..., description="Brief summary of the rhetoric in this section.")
