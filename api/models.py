from pydantic import BaseModel, Field
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    strict_mode: bool = Field(default=True)
    jurisdiction: str = Field(default="General")
    top_k_precedents: int = Field(default=0, ge=0, le=5)

class Clause(BaseModel):
    id: str
    heading: str
    text: str
    category: str
    risk: str
    rationale: str
    policy_violations: List[str] = []
    proposed_text: Optional[str] = None
    explanation: Optional[str] = None
    negotiation_note: Optional[str] = None

class AnalyzeResponse(BaseModel):
    summary: str
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    clauses: List[Clause]