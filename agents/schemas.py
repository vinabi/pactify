from pydantic import BaseModel, Field
from typing import List

CATEGORIES = [
    "Payment Terms",
    "Confidentiality",
    "Intellectual Property",
    "Indemnity",
    "Liability",
    "Termination",
    "Governing Law",
    "Assignment",
    "Non-compete/Non-solicit",
    "Miscellaneous",
]

class ClassifyOut(BaseModel):
    category: str = Field(description=f"One of: {', '.join(CATEGORIES)}")
    risk: str = Field(description="Low | Medium | High")
    rationale: str

class PolicyOut(BaseModel):
    violations: List[str] = Field(default_factory=list)

class RedlineOut(BaseModel):
    proposed_text: str
    explanation: str
    negotiation_note: str
    risk: str = Field(description="Low | Medium | High")
    rationale: str