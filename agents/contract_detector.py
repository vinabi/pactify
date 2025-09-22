# agents/contract_detector.py - ENHANCED CONTRACT DETECTION + TEMPLATE COMPARISON
from __future__ import annotations
import re
from typing import Tuple, Dict, Any, List, Optional
from loguru import logger

def normalize_contract_text(text: str) -> str:
    """Enhanced text normalization for contract analysis"""
    if not text:
        return ""
    # Fix encoding issues
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    # Remove common PDF artifacts
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)  # Page numbers
    text = re.sub(r'\n\s*Page\s+\d+\s+of\s+\d+\s*\n', '\n', text, flags=re.I)  # Page headers
    # Join hyphenated words across lines
    text = re.sub(r'-\s*\n\s*', '', text)
    # Collapse excessive whitespace but preserve structure
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 newlines
    text = re.sub(r'[ \t]+', ' ', text)           # Collapse spaces/tabs
    # Normalize to lowercase for analysis
    return " ".join(text.split()).lower()

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
    
    # Legal forms and documents (kept from your original file)
    r"\b(i-130|i-140|i-485|i-765|i-131)\b",  # Immigration forms
    r"\b(petition\s+for|application\s+for|form\s+i-\d+)\b",
    r"\b(uscis|immigration|petition|beneficiary|petitioner)\b",
    r"\b(legal\s+document|official\s+form|government\s+form)\b",
    
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
    """FORMAL LEGAL CONTRACT CLASSIFIER — rigid, with a 'legal but not a contract' path"""
    if not text or len(text.strip()) < 50:
        return False, {"score": 0, "reason": "Document too short for analysis"}

    # --- Normalize (preserve light structure) ---
    def _normalize(s: str) -> str:
        s = s.encode("utf-8", errors="ignore").decode("utf-8")
        s = re.sub(r'\n\s*\d+\s*\n', '\n', s)
        s = re.sub(r'\n\s*Page\s+\d+\s+of\s+\d+\s*\n', '\n', s, flags=re.I)
        s = re.sub(r'-\s*\n\s*', '', s)              # join hyphenated words across lines
        s = re.sub(r'\n\s*\n\s*\n+', '\n\n', s)      # cap blank lines
        s = re.sub(r'[ \t]+', ' ', s)                # collapse spaces/tabs
        return " ".join(s.split()).lower()

    normalized = _normalize(text)
    words = len(normalized.split())

    # --- Strict "obvious non-legal" rejection (resume, code, homework, etc.) ---
    non_legal_patterns = [
        # academic
        r"\b(assignment|homework|professor|semester|syllabus|quiz|midterm|final exam)\b",
        r"\b(essay|thesis|dissertation|bibliography|references)\b",
        # code / package metadata
        r"\bdef\s+\w+\s*\(|\bclass\s+\w+\s*:|\bimport\s+\w+|\bfrom\s+\w+\s+import\b",
        r"\bpackage\.json\b|\brequirements\.txt\b|\bsetup\.py\b|\bREADME\.md\b",
        r"\bnpm\s+install\b|\byarn\s+add\b|\bpip\s+install\b",
        # resume / personal docs
        r"\b(resume|curriculum\s+vitae|cv|cover\s+letter)\b",
        r"\b(dear\s+hiring\s+manager|objective|skills|experience|education)\b",
    ]
    non_legal_hits = sum(1 for p in non_legal_patterns if re.search(p, normalized, re.I))
    if non_legal_hits >= 2:
        return False, {
            "score": -120,
            "reason": "Non-legal content detected (code/resume/assignment)",
            "detected_type": "non_legal",
            "essential_elements": 0,
            "confidence": "none",
            "word_count": words
        }

    # --- Contract element gates (Offer/Acceptance, Consideration, Legal Intent, Capacity) ---
    gates = {
        "offer_acceptance": [
            r"\b(hereby\s+agree|agree\s+to|acceptance\s+of|offer\s+is\s+accepted)\b",
            r"\b(the\s+parties\s+agree|this\s+agreement)\b",
        ],
        "consideration": [
            r"\b(consideration|in\s+exchange\s+for|compensation|fee|salary|remuneration|payment)\b",
            r"\b(mutual\s+covenants|reciprocal\s+obligations)\b",
        ],
        "legal_intent": [
            r"\b(legally\s+binding|binding\s+agreement|enforceable)\b",
            r"\b(governed\s+by\s+law|breach.*(remedy|damages)|dispute\s+resolution|arbitration|jurisdiction)\b",
            r"\b(whereas|witnesseth|now\s+therefore)\b",
        ],
        "capacity": [
            r"\b(party|parties|between\s+.*\s+and)\b",
            r"\b(company|corporation|llc|inc\.?|ltd\.?|contractor|client|employer|employee|vendor|supplier)\b",
            r"\b(authorized|duly\s+authorized|legal\s+capacity)\b",
        ],
    }

    def _has_any(patterns: List[str]) -> bool:
        return any(re.search(p, normalized, re.I) for p in patterns)

    elements = {
        "offer_acceptance": _has_any(gates["offer_acceptance"]),
        "consideration": _has_any(gates["consideration"]),
        "legal_intent": _has_any(gates["legal_intent"]),
        "capacity": _has_any(gates["capacity"]),
    }
    essential_count = sum(1 for v in elements.values() if v)

    # --- Formal structure & substantive terms (supportive signals) ---
    formal_structure = any(re.search(p, normalized, re.I) for p in [
        r"\b(effective\s+date|commencement\s+date|term\s+of\s+agreement)\b",
        r"\b(section|clause|article|paragraph)\s+\d+\b",
        r"\b(signature|executed|in\s+witness\s+whereof)\b",
        r"\b(definitions?|shall\s+mean)\b",
    ])
    substantive_terms = any(re.search(p, normalized, re.I) for p in [
        r"\b(shall|will|must|required\s+to|obligated\s+to)\b",
        r"\b(rights|obligations|duties|responsibilities)\b",
        r"\b(termination|expiration|renewal|cancellation)\b",
        r"\b(liability|damages|indemnif|warranty|representation)\b",
    ])

    # --- Compute a robust score (not the gate) ---
    score = 0
    score += essential_count * 25
    if formal_structure:   score += 20
    if substantive_terms:  score += 15
    if words > 800:        score += 5
    if words > 1600:       score += 5

    # Penalty if lots of generic web/article signals present
    negative_hits = sum(1 for p in [
        r"\b(blog|article|press\s+release|announcement|newsletter)\b",
        r"\b(user\s+manual|tutorial|how\s+to)\b",
        r"\b(recipe|syllabus|course|curriculum)\b",
    ] if re.search(p, normalized, re.I))
    score -= negative_hits * 10
    if words < 120:
        score -= 10

    # --- Decision logic (strict) ---
    # CONTRACT = >= 3 essentials AND some structure
    is_contract = (essential_count >= 3) and (formal_structure or substantive_terms)

    # If clearly legal-ish but not a contract, surface a helpful path
    legal_indicators = []
    for k in ["legal_intent", "capacity"]:
        if elements[k]:
            legal_indicators.append(k)
    if ("governing law" in normalized) or ("jurisdiction" in normalized):
        legal_indicators.append("legal_structure")
    if "witnesseth" in normalized or "whereas" in normalized:
        legal_indicators.append("recitals")

    if is_contract:
        confidence = "high" if essential_count == 4 else "medium"
        return True, {
            "score": score,
            "confidence": confidence,
            "essential_elements": essential_count,
            "offer_acceptance": elements["offer_acceptance"],
            "consideration": elements["consideration"],
            "legal_intent": elements["legal_intent"],
            "capacity": elements["capacity"],
            "formal_structure": formal_structure,
            "substantive_terms": substantive_terms,
            "word_count": words,
            "detected_type": "contract",
            "analysis_recommendation": "analyze",
            "legal_indicators": legal_indicators[:6],
        }

    # Not a contract. If there are legal indicators, mark it as legal document.
    if legal_indicators or substantive_terms:
        return False, {
            "score": max(-10, score - 20),
            "confidence": "low",
            "reason": "Legal document detected but failed contract elements/structure",
            "essential_elements": essential_count,
            "offer_acceptance": elements["offer_acceptance"],
            "consideration": elements["consideration"],
            "legal_intent": elements["legal_intent"],
            "capacity": elements["capacity"],
            "formal_structure": formal_structure,
            "substantive_terms": substantive_terms,
            "word_count": words,
            "detected_type": "legal_document",
            "analysis_recommendation": "analyze_non_contract",
            "legal_indicators": legal_indicators[:6],
        }

    # Otherwise, treat as non-legal
    return False, {
        "score": -40,
        "confidence": "none",
        "reason": "No legal/contract signals found",
        "essential_elements": essential_count,
        "formal_structure": formal_structure,
        "substantive_terms": substantive_terms,
        "word_count": words,
        "detected_type": "non_legal"
    }
    
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
        "pattern": r"\b(?:client|contractor|vendor|party)\s+(?:shall|will|agrees?\s+to)\s+indemnify.*(?!.*mutual|each\s+party)",
        "description": "Only one party bears indemnification burden"
    },
    {
        "label": "Broad IP assignment beyond scope",
        "severity": "high",
        "category": "intellectual_property", 
        "pattern": r"\b(all|any)\s+(?:inventions?|developments?|works?|intellectual\s+property|improvements)\b.*\b(assign|transfer|belong|property|sole\s+property)\b",
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
        "pattern": r"\b(?:auto(?:matic(?:ally)?)?|shall)\s+(?:renew|extend)\b",
        "description": "Auto-renewal clause detected"
    },
    {
        "label": "Excessive interest or penalty rates",
        "severity": "medium",
        "category": "payment",
        "pattern": r"\b(?:1[8-9]|2[0-9]|[3-9][0-9])%\s+(?:per\s+annum|interest|penalty)",
        "description": "Interest or penalty rates above 18% annually"
    },
    {
        "label": "Unlimited indemnification scope",
        "severity": "high",
        "category": "indemnity", 
        "pattern": r"\bindemnify.*\b(?:regardless|whether\s+caused\s+by|all\s+claims)",
        "description": "Indemnification without carve-outs for gross negligence"
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
                if not re.search(r"\blimit(?:ation)?\s+of\s+liability|liability\s+(?:cap|limit)", normalized, re.I):
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
    deviations: List[Dict[str, Any]] = []
    
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
        
    total_score = sum(match.get("similarity_score", 0) for match in matches)
    return min(total_score / len(matches), 1.0) if matches else 0.0


def generate_template_recommendations(deviations: List[Dict]) -> List[str]:
    """Generate recommendations based on template analysis"""
    recommendations: List[str] = []
    
    missing_count = sum(1 for d in deviations if d["type"] == "missing_clause")
    unusual_count = sum(1 for d in deviations if d["type"] == "unusual_clause")
    
    if missing_count > 2:
        recommendations.append("Consider adding missing standard clauses to improve contract completeness")
    
    if unusual_count > 0:
        recommendations.append("Review unusual clauses for potential risks and enforceability issues")
        
    if missing_count == 0 and unusual_count == 0:
        recommendations.append("Contract structure aligns well with standard templates")
    
    return recommendations
