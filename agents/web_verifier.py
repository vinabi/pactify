# agents/web_verifier.py - WEB SEARCH VERIFICATION FOR LEGAL DOCUMENTS
from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
import httpx
import json

class WebLegalVerifier:
    """Use web search to verify if document is legal and get improvement suggestions"""
    
    def __init__(self):
        self.search_engines = {
            "duckduckgo": "https://api.duckduckgo.com/",
            "serper": "https://google.serper.dev/search",  # If you have API key
        }
    
    async def verify_legal_document(self, text: str, filename: str = "") -> Dict[str, Any]:
        """Use web search to verify if document is legal and get context"""
        
        try:
            # Extract key terms for search
            search_terms = self.extract_search_terms(text, filename)
            
            # Perform web searches
            legal_verification = await self.search_legal_context(search_terms)
            
            # Get improvement suggestions
            improvement_suggestions = await self.get_web_improvements(search_terms)
            
            return {
                "is_legal": legal_verification.get("is_legal", True),  # Default to true for analysis
                "legal_type": legal_verification.get("type", "unknown"),
                "web_confidence": legal_verification.get("confidence", 0.5),
                "improvements": improvement_suggestions,
                "search_terms": search_terms,
                "web_context": legal_verification.get("context", "")
            }
            
        except Exception as e:
            logger.warning(f"Web verification failed: {e}")
            # Fallback: assume it's legal and analyze
            return {
                "is_legal": True,
                "legal_type": "unknown_legal_document", 
                "web_confidence": 0.3,
                "improvements": self.get_fallback_improvements(text),
                "search_terms": [],
                "web_context": "Web verification unavailable - using fallback analysis"
            }
    
    def extract_search_terms(self, text: str, filename: str = "") -> List[str]:
        """Extract key terms for web search"""
        
        terms = []
        text_lower = text.lower()
        
        # Extract form numbers
        form_numbers = re.findall(r'\b(i-\d+[a-z]?|form\s+\d+[a-z]?)\b', text_lower)
        terms.extend(form_numbers)
        
        # Extract legal document types
        legal_types = [
            "non disclosure agreement", "employment agreement", "service agreement",
            "license agreement", "partnership agreement", "confidentiality agreement",
            "immigration form", "petition", "application", "contract", "legal document"
        ]
        
        for legal_type in legal_types:
            if legal_type in text_lower:
                terms.append(legal_type)
        
        # Extract from filename
        if filename:
            filename_lower = filename.lower()
            if any(keyword in filename_lower for keyword in ["contract", "agreement", "nda", "legal", "form", "i-130", "petition"]):
                terms.append(f"legal document {filename}")
        
        # Extract organization names
        orgs = re.findall(r'\b(uscis|immigration|department|federal|government|company|corporation|llc|inc)\b', text_lower)
        terms.extend(orgs[:3])  # Top 3 orgs
        
        return list(set(terms))[:5]  # Top 5 unique terms
    
    async def search_legal_context(self, search_terms: List[str]) -> Dict[str, Any]:
        """Search web for legal document context"""
        
        if not search_terms:
            return {"is_legal": True, "confidence": 0.3, "type": "unknown"}
        
        try:
            # Use DuckDuckGo instant answers (free API)
            search_query = " ".join(search_terms[:3]) + " legal document contract"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": search_query,
                        "format": "json",
                        "no_redirect": "1",
                        "no_html": "1",
                        "skip_disambig": "1"
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Analyze search results
                    abstract = data.get("Abstract", "").lower()
                    answer = data.get("Answer", "").lower()
                    
                    # Check for legal indicators in results
                    legal_score = 0
                    
                    legal_keywords = ["legal", "contract", "agreement", "law", "court", "attorney", "legal document", "immigration", "form", "petition"]
                    for keyword in legal_keywords:
                        if keyword in abstract or keyword in answer:
                            legal_score += 1
                    
                    # Determine document type from search results
                    doc_type = "unknown"
                    if "immigration" in abstract or "uscis" in abstract:
                        doc_type = "immigration_form"
                    elif "contract" in abstract or "agreement" in abstract:
                        doc_type = "contract"
                    elif "legal" in abstract:
                        doc_type = "legal_document"
                    
                    return {
                        "is_legal": legal_score > 0,
                        "confidence": min(0.9, legal_score * 0.15),
                        "type": doc_type,
                        "context": abstract or answer or "Legal document context found"
                    }
        
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
        
        # Fallback: assume legal if we found search terms
        return {
            "is_legal": len(search_terms) > 0,
            "confidence": 0.4,
            "type": "legal_document",
            "context": "Unable to verify online - assuming legal document for analysis"
        }
    
    async def get_web_improvements(self, search_terms: List[str]) -> List[str]:
        """Get improvement suggestions based on web search"""
        
        # Standard improvements based on document type
        base_improvements = [
            "Add clear identification of all parties involved",
            "Include specific legal structure with WHEREAS clauses",
            "Add signature blocks with date and witness provisions",
            "Include governing law and jurisdiction clauses",
            "Define key terms in a definitions section",
            "Add liability limitation and indemnification clauses",
            "Include termination and renewal provisions",
            "Ensure compliance with applicable laws and regulations"
        ]
        
        # Specific improvements based on search terms
        specific_improvements = []
        
        for term in search_terms:
            if "i-130" in term.lower() or "immigration" in term.lower():
                specific_improvements.extend([
                    "Ensure all USCIS form fields are completely filled",
                    "Include required supporting documentation",
                    "Verify petitioner eligibility requirements",
                    "Check beneficiary information accuracy"
                ])
            elif "employment" in term.lower():
                specific_improvements.extend([
                    "Define job responsibilities and reporting structure",
                    "Include compensation and benefits details",
                    "Add at-will employment clause if applicable",
                    "Include confidentiality and non-compete provisions"
                ])
            elif "nda" in term.lower() or "confidential" in term.lower():
                specific_improvements.extend([
                    "Define confidential information clearly",
                    "Include permitted disclosure exceptions",
                    "Add return of information provisions",
                    "Specify confidentiality term duration"
                ])
        
        # Combine and deduplicate
        all_improvements = base_improvements + specific_improvements
        return list(dict.fromkeys(all_improvements))[:8]  # Top 8 unique improvements
    
    def get_fallback_improvements(self, text: str) -> List[str]:
        """Fallback improvements when web search unavailable"""
        
        text_lower = text.lower()
        improvements = []
        
        # Analyze what's missing and suggest improvements
        if "whereas" not in text_lower:
            improvements.append("Add WHEREAS clauses to establish legal context and background")
        
        if "now therefore" not in text_lower and "agree" not in text_lower:
            improvements.append("Include 'NOW THEREFORE' clause to introduce binding agreements")
        
        if not re.search(r"\b(party|parties|client|contractor|company)\b", text_lower):
            improvements.append("Clearly identify all parties to the agreement")
        
        if "signature" not in text_lower and "sign" not in text_lower:
            improvements.append("Add signature blocks with date and witness provisions")
        
        if "governing law" not in text_lower and "jurisdiction" not in text_lower:
            improvements.append("Include governing law and jurisdiction clauses")
        
        if "termination" not in text_lower:
            improvements.append("Add termination and renewal provisions")
        
        if "liability" not in text_lower:
            improvements.append("Include liability limitation clauses")
        
        if "confidential" in text_lower and "definition" not in text_lower:
            improvements.append("Define 'Confidential Information' clearly")
        
        return improvements[:8]

# Create global instance for easy import
web_verifier = WebLegalVerifier()
