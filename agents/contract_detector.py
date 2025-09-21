# agents/contract_detector.py - ENHANCED CONTRACT DETECTION + TEMPLATE COMPARISON
from __future__ import annotations
import re
from typing import Tuple, Dict, Any, List, Optional
from loguru import logger

# ---------- COMPREHENSIVE CONTRACT PATTERNS ----------
STRONG_CONTRACT_SIGNALS = [
    # Contract types
    r"\b(non-?disclosure|confidentiality)\s+agreement\b",
    r"\b(master\s+)?service(s)?\s+agreement\b", 
    r"\b(employment|consulting|independent\s+contractor)\s+(agreement|contract)\b",
    r"\b(license|licensing)\s+(agreement|contract)\b",
    r"\b(purchase|sales?|supply)\s+(agreement|contract|order)\b",
    r"\b(partnership|joint\s+venture)\s+agreement\b",
    r"\b(franchise|distribution|reseller)\s+agreement\b",
    r"\b(terms\s+and\s+conditions|terms\s+of\s+(service|use))\b",
    r"\b(statement\s+of\s+work|scope\s+of\s+work|sow)\b",
    
    # Legal structure patterns
    r"\bwhereas\b.*\bnow\s+therefore\b",
    r"\bin\s+consideration\s+of\b",
    r"\bthe\s+parties\s+agree\s+as\s+follows\b",
    r"\bthis\s+agreement\s+is\s+(made|entered\s+into)\b",
    r"\b(effective|commencement)\s+date\b",
    
    # Core contract clauses
    r"\bindemnif(y|ication)\b.*\bhold\s+harmless\b",
    r"\blimit(ation)?\s+of\s+liability\b",
    r"\bgoverning\s+law\b.*\bjurisdiction\b",
    r"\btermination\b.*\b(breach|cause|convenience)\b",
    r"\bintellectual\s+property\b.*\b(ownership|rights)\b",
    r"\bconfidential(ity)?\b.*\binformation\b",
    r"\bpayment\b.*\b(terms|schedule|invoice)\b",
    r"\bwarrant(y|ies)\b.*\bdisclaim(er)?\b",
    r"\bdispute\s+resolution\b.*\b(arbitration|mediation)\b",
    r"\bforce\s+majeure\b",
    
    # Signature and execution
    r"\bin\s+witness\s+whereof\b",
    r"\bexecuted\s+.*\s+(date|day)\s+first\s+written\b",
    r"\bsignature\s+page\b",
    r"\bduly\s+authorized\b",
]

MEDIUM_CONTRACT_SIGNALS = [
    r"\b(section|clause|article|paragraph)\s+\d+\b",
    r"\b(shall|will)\s+(not\s+)?(be\s+)?(liable|responsible|obligated)\b",
    r"\b(party|parties)\s+(agree|consent|acknowledge)\b",
    r"\b(including\s+but\s+not\s+limited\s+to|without\s+limitation)\b",
    r"\b(reasonable|best)\s+efforts\b",
    r"\b(material|substantial)\s+(breach|default|change)\b",
    r"\b(cure|remedy)\s+period\b",
    r"\b(successor|assign)\b.*\bbinding\b",
    r"\bentire\s+agreement\b",
    r"\bseverability\b",
]

WEAK_CONTRACT_SIGNALS = [
    r"\b(agreement|contract|terms)\b",
    r"\b(provide|perform|deliver)\b.*\bservice\b",
    r"\b(payment|fee|cost|price)\b",
    r"\b(date|deadline|timeline)\b",
    r"\b(contact|email|phone)\b.*\binformation\b",
]

NON_CONTRACT_SIGNALS = [
    r"\b(blog|article|post|news)\b",
    r"\b(privacy\s+policy|cookie\s+policy)\b", 
    r"\b(user\s+manual|instructions|tutorial)\b",
    r"\b(press\s+release|announcement)\b",
    r"\b(syllabus|curriculum|course)\b",
    r"\b(recipe|how\s+to|guide)\b",
    r"\b(newsletter|bulletin|update)\b",
    r"\b(academic\s+paper|research|study)\b",
    r"\b(invoice|receipt|bill)\b",
    r"\b(memo|memorandum|note)\b",
]

def looks_like_contract_v2(text: str) -> Tuple[bool, Dict[str, Any]]:
    """Enhanced contract detection with comprehensive pattern matching"""
    if not text or len(text.strip()) < 50:
        return False, {"score": 0, "reason": "Too short"}
    
    # Normalize text
    normalized = " ".join(text.split()).lower()
    words = len(normalized.split())
    
    # Pattern matching with weighted scores
    strong_matches = []
    medium_matches = []
    weak_matches = []
    negative_matches = []
    
    for pattern in STRONG_CONTRACT_SIGNALS:
        if re.search(pattern, normalized, re.I):
            strong_matches.append(pattern)
    
    for pattern in MEDIUM_CONTRACT_SIGNALS:
        if re.search(pattern, normalized, re.I):
            medium_matches.append(pattern)
            
    for pattern in WEAK_CONTRACT_SIGNALS:
        if re.search(pattern, normalized, re.I):
            weak_matches.append(pattern)
            
    for pattern in NON_CONTRACT_SIGNALS:
        if re.search(pattern, normalized, re.I):
            negative_matches.append(pattern)
    
    # Structural analysis
    has_parties = bool(re.search(r"\b(party\s+a|party\s+b|client|contractor|company|vendor)\b", normalized))
    has_legal_structure = bool(re.search(r"\b(whereas|witnesseth|now\s+therefore|in\s+consideration)\b", normalized))
    has_signatures = bool(re.search(r"\b(sign|signature|execute|authorized)\b", normalized))
    has_sections = len(re.findall(r"\b(section|clause|article)\s+\d+", normalized))
    has_definitions = bool(re.search(r"\b(define|means|shall\s+mean|definition)\b", normalized))
    
    # Calculate weighted score
    score = 0
    
    # Strong signals (high weight)
    score += len(strong_matches) * 10
    
    # Medium signals  
    score += len(medium_matches) * 5
    
    # Weak signals
    score += len(weak_matches) * 2
    
    # Structural elements
    score += 8 if has_legal_structure else 0
    score += 5 if has_parties else 0
    score += 3 if has_signatures else 0
    score += min(has_sections * 2, 10)  # Cap sections bonus
    score += 3 if has_definitions else 0
    
    # Length bonus (longer documents more likely to be contracts)
    if words > 500:
        score += 5
    elif words > 1000:
        score += 8
    elif words > 2000:
        score += 10
        
    # Penalties for negative signals
    score -= len(negative_matches) * 8
    
    # Special penalty for very short documents
    if words < 100:
        score -= 10
        
    # Determine if it's a contract
    is_contract = score >= 20  # Raised threshold for better accuracy
    
    details = {
        "score": score,
        "strong_matches": len(strong_matches),
        "medium_matches": len(medium_matches), 
        "weak_matches": len(weak_matches),
        "negative_matches": len(negative_matches),
        "word_count": words,
        "has_legal_structure": has_legal_structure,
        "has_parties": has_parties,
        "has_signatures": has_signatures,
        "section_count": has_sections,
        "positives": strong_matches[:5],  # Top 5 for display
        "negatives": negative_matches[:3],  # Top 3 negatives
    }
    
    return is_contract, details

# ---------- COMPREHENSIVE RED FLAGS ----------
RED_FLAGS: List[Dict[str, Any]] = [
    # HIGH RISK - Deal breakers
    {
        "label": "Unlimited liability exposure",
        "severity": "high",
        "category": "liability",
        "pattern": r"\b(unlimited|without\s+limit|no\s+cap|all\s+damages)\b.*\b(liability|damages|loss)\b",
        "description": "Exposes party to unlimited financial risk"
    },
    {
        "label": "One-sided indemnification",
        "severity": "high", 
        "category": "indemnity",
        "pattern": r"\b(?:contractor|vendor|party)\s+(?:shall|will|agrees?\s+to)\s+indemnify.*(?!.*mutual|each\s+party)",
        "description": "Only one party bears indemnification burden"
    },
    {
        "label": "Broad IP assignment beyond scope",
        "severity": "high",
        "category": "intellectual_property", 
        "pattern": r"\b(all|any)\s+(?:inventions?|developments?|works?|intellectual\s+property)\b.*\b(assign|transfer|belong)\b",
        "description": "Assigns IP beyond project deliverables"
    },
    {
        "label": "Termination only for cause",
        "severity": "high",
        "category": "termination",
        "pattern": r"\btermination?\b.*\b(?:only|solely)\s+(?:for\s+cause|upon\s+breach)\b",
        "description": "No termination for convenience option"
    },
    
    # MEDIUM RISK - Significant concerns  
    {
        "label": "Auto-renewal without adequate notice",
        "severity": "medium",
        "category": "termination",
        "pattern": r"\b(?:auto(?:matic(?:ally)?)?|shall)\s+(?:renew|extend)\b.*(?!(?:30|60|90)\s+days?\s+notice)",
        "description": "Auto-renewal without sufficient notice period"
    },
    {
        "label": "Payment terms exceeding NET 60",
        "severity": "medium", 
        "category": "payment",
        "pattern": r"\bnet\s+(?:6[5-9]|[7-9]\d|\d{3,})\s+days?\b|\bpayment.*(?:90|120|\d{3,})\s+days?\b",
        "description": "Extended payment terms harm cash flow"
    },
    {
        "label": "Confidentiality without time limit",
        "severity": "medium",
        "category": "confidentiality", 
        "pattern": r"\bconfidential.*\b(?!.*(?:\d+\s+years?|term\s+of|upon\s+termination))",
        "description": "Perpetual confidentiality obligations"
    },
    {
        "label": "Non-compete exceeding 1 year",
        "severity": "medium",
        "category": "restrictions",
        "pattern": r"\bnon[- ]?compete.*\b(?:[2-9]\d*|[1-9]\d+)\s+years?\b",
        "description": "Excessive non-compete restriction period"
    },
    {
        "label": "Governing law in unfavorable jurisdiction",
        "severity": "medium",
        "category": "dispute",
        "pattern": r"\bgoverning\s+law.*\b(?:delaware|new\s+york|california)\b(?!.*mutual)",
        "description": "May favor other party's jurisdiction"
    },
    {
        "label": "Mandatory arbitration with limited discovery", 
        "severity": "medium",
        "category": "dispute",
        "pattern": r"\barbitration\b.*\b(?:final|binding)\b.*(?!.*discovery|appeal)",
        "description": "Limits legal recourse and discovery rights"
    },
    
    # LOW RISK - Minor concerns
    {
        "label": "Missing liability cap clause",
        "severity": "low",
        "category": "liability", 
        "pattern": r"(?!.*limit(?:ation)?\s+of\s+liability)",
        "needs_absence_check": True,
        "description": "Should include liability limitations"
    },
    {
        "label": "Vague performance standards",
        "severity": "low",
        "category": "performance",
        "pattern": r"\b(?:reasonable|best|commercially\s+reasonable)\s+efforts?\b",
        "description": "Performance standards are subjective"
    },
    {
        "label": "Force majeure without mutual protection",
        "severity": "low", 
        "category": "force_majeure",
        "pattern": r"\bforce\s+majeure\b.*(?!.*both\s+parties|each\s+party)",
        "description": "Force majeure may not protect both parties"
    }
]

def find_red_flags(text: str) -> List[Dict[str, Any]]:
    """Enhanced red flag detection with categorization"""
    if not text:
        return []
        
    normalized = " ".join(text.split()).lower()
    hits: List[Dict[str, Any]] = []
    
    for rf in RED_FLAGS:
        if rf.get("needs_absence_check"):
            # Check for absence of required clauses
            if rf["category"] == "liability":
                if not re.search(r"\blimit(?:ation)?\s+of\s+liability|liability\s+(?:cap|limit)", normalized):
                    hits.append({
                        "label": rf["label"], 
                        "severity": rf["severity"],
                        "category": rf["category"],
                        "description": rf["description"]
                    })
        else:
            # Pattern-based detection
            if re.search(rf["pattern"], normalized, re.I | re.S):
                hits.append({
                    "label": rf["label"], 
                    "severity": rf["severity"],
                    "category": rf["category"], 
                    "description": rf["description"],
                    "pattern": rf["pattern"]
                })
                
    return hits


# ---------- TEMPLATE COMPARISON SYSTEM ----------
def identify_contract_type(text: str) -> Tuple[str, float]:
    """Identify the most likely contract type based on content analysis"""
    if not text:
        return "unknown", 0.0
        
    normalized = text.lower()
    
    # Contract type patterns with confidence scores
    contract_types = {
        "Non-Disclosure Agreement": [
            (r"\b(?:non[- ]?disclosure|confidentiality)\s+agreement\b", 0.9),
            (r"\bconfidential\s+information\b", 0.3),
            (r"\bdisclosure\b.*\bconfidential\b", 0.4),
            (r"\breceiving\s+party\b.*\bdisclosing\s+party\b", 0.7)
        ],
        "Service Agreement": [
            (r"\b(?:master\s+)?service(?:s)?\s+agreement\b", 0.9),
            (r"\bstatement\s+of\s+work\b", 0.8),
            (r"\bservice(?:s)?\b.*\bperform\b", 0.3),
            (r"\bdeliverable(?:s)?\b", 0.4)
        ],
        "Employment Agreement": [
            (r"\bemployment\s+agreement\b", 0.9),
            (r"\bemployee\b.*\bemployer\b", 0.7),
            (r"\bsalary\b.*\bbenefits?\b", 0.5),
            (r"\btermination\s+of\s+employment\b", 0.6)
        ],
        "License Agreement": [
            (r"\blicens(?:e|ing)\s+agreement\b", 0.9),
            (r"\blicensor\b.*\blicensee\b", 0.8),
            (r"\bintellectual\s+property\s+rights?\b", 0.4),
            (r"\broyalt(?:y|ies)\b", 0.5)
        ],
        "Purchase Agreement": [
            (r"\b(?:purchase|sales?)\s+agreement\b", 0.9),
            (r"\bbuyer\b.*\bseller\b", 0.7),
            (r"\bpurchase\s+price\b", 0.6),
            (r"\bclosing\s+date\b", 0.4)
        ],
        "Partnership Agreement": [
            (r"\bpartnership\s+agreement\b", 0.9),
            (r"\bpartner(?:s)?\b.*\bprofit(?:s)?\b", 0.6),
            (r"\bjoint\s+venture\b", 0.8),
            (r"\bequity\s+distribution\b", 0.5)
        ],
        "Terms of Service": [
            (r"\bterms?\s+(?:of\s+service|and\s+conditions)\b", 0.9),
            (r"\buser\s+agreement\b", 0.7),
            (r"\bacceptable\s+use\b", 0.4),
            (r"\bservice\s+provider\b", 0.3)
        ]
    }
    
    best_type = "unknown"
    best_score = 0.0
    
    for contract_type, patterns in contract_types.items():
        score = 0.0
        for pattern, weight in patterns:
            if re.search(pattern, normalized):
                score += weight
        
        # Normalize score by number of patterns
        normalized_score = score / len(patterns)
        
        if normalized_score > best_score:
            best_score = normalized_score
            best_type = contract_type
    
    return best_type, best_score


def compare_to_templates(contract_text: str, vect_client=None) -> Dict[str, Any]:
    """Compare contract against standard templates using vector similarity"""
    if not vect_client or not contract_text:
        return {"template_matches": [], "deviations": [], "coverage_score": 0.0}
    
    try:
        # Identify contract type first
        contract_type, type_confidence = identify_contract_type(contract_text)
        
        # Search for similar template clauses
        from .tools_vector import retrieve_snippets
        
        # Get template matches from vector DB
        template_matches = []
        try:
            matches = retrieve_snippets(vect_client, "contract_templates", contract_text, k=5)
            for meta, doc in matches:
                template_matches.append({
                    "template_type": meta.get("contract_type", "Unknown"),
                    "clause_type": meta.get("clause_type", "General"),
                    "similarity_score": meta.get("score", 0.5),
                    "template_text": doc[:300] + "..." if len(doc) > 300 else doc
                })
        except Exception as e:
            logger.warning(f"Template retrieval failed: {e}")
        
        # Analyze deviations (clauses that don't match standard patterns)
        deviations = analyze_template_deviations(contract_text, contract_type)
        
        # Calculate coverage score (how much of the contract matches templates)
        coverage_score = calculate_template_coverage(contract_text, template_matches)
        
        return {
            "identified_type": contract_type,
            "type_confidence": type_confidence,
            "template_matches": template_matches,
            "deviations": deviations,
            "coverage_score": coverage_score,
            "recommendations": generate_template_recommendations(deviations)
        }
        
    except Exception as e:
        logger.error(f"Template comparison failed: {e}")
        return {"error": str(e), "template_matches": [], "deviations": []}


def analyze_template_deviations(text: str, contract_type: str) -> List[Dict[str, Any]]:
    """Identify clauses that deviate from standard templates"""
    deviations = []
    
    # Standard clause expectations by contract type
    expected_clauses = {
        "Non-Disclosure Agreement": [
            "confidential_information_definition",
            "permitted_disclosures", 
            "return_of_information",
            "term_duration"
        ],
        "Service Agreement": [
            "scope_of_work",
            "payment_terms",
            "intellectual_property",
            "termination_rights",
            "liability_limitations"
        ],
        "Employment Agreement": [
            "job_responsibilities",
            "compensation_benefits",
            "termination_conditions", 
            "non_compete_clause",
            "confidentiality"
        ]
    }
    
    expected = expected_clauses.get(contract_type, [])
    normalized = text.lower()
    
    # Check for missing standard clauses
    for clause_type in expected:
        if not has_clause_type(normalized, clause_type):
            deviations.append({
                "type": "missing_clause",
                "clause_type": clause_type,
                "severity": "medium",
                "description": f"Missing standard {clause_type.replace('_', ' ')} clause"
            })
    
    # Check for unusual or risky clauses
    unusual_patterns = [
        (r"\bperpetual\b", "perpetual_term", "Unusual perpetual term"),
        (r"\btrial\s+by\s+jury\s+waiver\b", "jury_waiver", "Jury trial waiver clause"),
        (r"\bexclusive\s+jurisdiction\b", "exclusive_jurisdiction", "Exclusive jurisdiction clause"),
        (r"\battorney(?:s)?\s+fees?\b.*\bprevailing\s+party\b", "attorney_fees", "Attorney fees clause")
    ]
    
    for pattern, clause_type, description in unusual_patterns:
        if re.search(pattern, normalized):
            deviations.append({
                "type": "unusual_clause",
                "clause_type": clause_type,
                "severity": "low",
                "description": description
            })
    
    return deviations


def has_clause_type(text: str, clause_type: str) -> bool:
    """Check if text contains a specific type of clause"""
    patterns = {
        "confidential_information_definition": r"\bconfidential\s+information\b.*\bmeans\b",
        "permitted_disclosures": r"\bpermitted\s+disclosure\b|\bexceptions?\b.*\bconfidentialit",
        "return_of_information": r"\breturn\b.*\b(?:information|materials?|documents?)\b",
        "term_duration": r"\bterm\b.*\b(?:years?|months?|period)\b",
        "scope_of_work": r"\bscope\s+of\s+work\b|\bservice(?:s)?\s+(?:to\s+be\s+)?provided\b",
        "payment_terms": r"\bpayment\s+terms?\b|\bcompensation\b|\bfees?\b",
        "intellectual_property": r"\bintellectual\s+property\b|\bownership\b.*\bwork\s+product\b",
        "termination_rights": r"\btermination\b.*\b(?:rights?|notice)\b",
        "liability_limitations": r"\blimitation\s+of\s+liability\b|\bliability\s+cap\b"
    }
    
    pattern = patterns.get(clause_type)
    if pattern:
        return bool(re.search(pattern, text, re.I))
    return False


def calculate_template_coverage(text: str, matches: List[Dict]) -> float:
    """Calculate how much of the contract is covered by standard templates"""
    if not matches:
        return 0.0
        
    # Simple heuristic: average similarity scores weighted by length
    total_score = sum(match.get("similarity_score", 0) for match in matches)
    return min(total_score / len(matches), 1.0) if matches else 0.0


def generate_template_recommendations(deviations: List[Dict]) -> List[str]:
    """Generate recommendations based on template analysis"""
    recommendations = []
    
    missing_count = sum(1 for d in deviations if d["type"] == "missing_clause")
    unusual_count = sum(1 for d in deviations if d["type"] == "unusual_clause")
    
    if missing_count > 2:
        recommendations.append("Consider adding missing standard clauses to improve contract completeness")
    
    if unusual_count > 0:
        recommendations.append("Review unusual clauses for potential risks and enforceability issues")
        
    if missing_count == 0 and unusual_count == 0:
        recommendations.append("Contract structure aligns well with standard templates")
    
    return recommendations
