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
    text = re.sub(r'\n\s*Page\s+\d+\s+of\s+\d+\s*\n', '\n', text, re.I)  # Page headers
    
    # Join hyphenated words across lines
    text = re.sub(r'-\s*\n\s*', '', text)
    
    # Collapse excessive whitespace but preserve structure
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 newlines
    text = re.sub(r'[ \t]+', ' ', text)  # Collapse spaces/tabs
    
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
    
    # Legal forms and documents
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
    """LIBERAL contract detection - analyzes ANY potentially legal document"""
    if not text or len(text.strip()) < 50:
        return False, {"score": 0, "reason": "Document too short for analysis"}
    
    # Enhanced normalization with structure preservation
    normalized = normalize_contract_text(text)
    words = len(normalized.split())
    
    # SMART REJECTION: Identify obvious non-legal documents with context
    non_legal_indicators = [
        # Academic/Educational
        (r"\b(assignment|homework|student|professor|course|syllabus|grade|semester|exam|quiz|tutorial|lesson)\b", "academic_assignment"),
        (r"\b(essay|research\s+paper|thesis|dissertation|abstract|bibliography|citation)\b", "academic_paper"),
        (r"\b(university|college|school|education|academic|study|student\s+id)\b", "educational_content"),
        
        # Technical/Code
        (r"\bimport\s+\w+", "code_file"),
        (r"\bfrom\s+\w+\s+import", "code_file"),
        (r"\bdef\s+\w+\s*\(", "code_file"),
        (r"\bclass\s+\w+", "code_file"),
        (r"\b(npm|pip|yarn)\s+install", "package_manager"),
        (r"\bversion\s*[:=]\s*[\"'][\d\.]+[\"']", "config_file"),
        
        # Business/Marketing (not legal)
        (r"\b(blog|article|news|press\s+release|marketing|advertisement|brochure)\b", "marketing_content"),
        (r"\b(recipe|cooking|ingredient|instruction|how\s+to\s+make)\b", "instructional_content"),
        (r"\b(invoice|receipt|bill|purchase\s+order|shipping)\b", "business_transaction"),
        
        # Personal/Informal
        (r"\b(dear\s+friend|hi\s+\w+|hello|thanks|best\s+regards|sincerely)\b", "personal_communication"),
        (r"\b(email|message|note|memo|reminder)\b", "informal_communication")
    ]
    
    # Check document type with context scoring
    non_legal_score = 0
    detected_type = "unknown"
    
    for pattern, doc_type in non_legal_indicators:
        matches = len(re.findall(pattern, normalized, re.I))
        if matches >= 2:  # Multiple instances
            non_legal_score += matches
            detected_type = doc_type
    
    # Check for legal terms
    has_legal_terms = bool(re.search(r"\b(legal|law|agreement|contract|party|liability|indemnif|jurisdiction|petition|form|uscis|immigration|employment|confidential|proprietary|signature|witness|whereas|therefore|covenant|warrant)\b", normalized))
    
    # SMART REJECTION: Reject if clearly non-legal AND no strong legal terms
    if non_legal_score >= 5 and not has_legal_terms:
        return False, {"score": -100, "reason": f"{detected_type.replace('_', ' ').title()} detected - not a legal document"}
    
    # Special case: Academic assignments with some legal words (common in law school)
    if detected_type in ["academic_assignment", "academic_paper", "educational_content"]:
        academic_legal_terms = re.findall(r"\b(case\s+study|legal\s+analysis|court|law\s+review|legal\s+brief|constitutional|statute)\b", normalized)
        if len(academic_legal_terms) < 3:  # Not enough legal academic content
            return False, {"score": -80, "reason": "Academic assignment - not a legal contract"}
    
    # LIBERAL APPROACH: Assume everything else could be legal and analyze it
    # Look for ANY legal indicators
    
    # Legal document indicators (very broad)
    legal_indicators = []
    
    # Government forms and legal documents
    if re.search(r"\b(form|i-\d+|uscis|immigration|petition|application|department|government|federal|state|court|legal|law)\b", normalized):
        legal_indicators.append("government_form")
    
    # Contract language (even basic)
    if re.search(r"\b(agreement|contract|terms|party|parties|shall|will|obligation|right|responsibility)\b", normalized):
        legal_indicators.append("contract_language")
    
    # Legal relationships
    if re.search(r"\b(employer|employee|client|contractor|vendor|supplier|customer|petitioner|beneficiary|plaintiff|defendant)\b", normalized):
        legal_indicators.append("legal_relationships")
    
    # Legal concepts
    if re.search(r"\b(liability|indemnif|confidential|proprietary|intellectual\s+property|payment|compensation|termination|breach|compliance|jurisdiction|governing\s+law)\b", normalized):
        legal_indicators.append("legal_concepts")
    
    # Legal structure
    if re.search(r"\b(whereas|witnesseth|now\s+therefore|in\s+consideration|effective\s+date|signature|executed|binding|enforceable)\b", normalized):
        legal_indicators.append("legal_structure")
    
    # Calculate liberal score
    score = 0
    
    # Base score for any legal indicators
    score += len(legal_indicators) * 20
    
    # Length bonus (longer docs more likely to be substantial)
    if words > 100:
        score += 10
    if words > 500:
        score += 20
    if words > 1000:
        score += 30
    
    # Pattern matching for additional signals
    strong_matches = []
    medium_matches = []
    
    for pattern in STRONG_CONTRACT_SIGNALS:
        if re.search(pattern, normalized, re.I):
            strong_matches.append(pattern)
            score += 25
    
    for pattern in MEDIUM_CONTRACT_SIGNALS:
        if re.search(pattern, normalized, re.I):
            medium_matches.append(pattern)
            score += 15
    
    # BALANCED: Analyze if it has MEANINGFUL legal characteristics
    is_legal_document = (len(legal_indicators) >= 2) or (score > 40) or (len(strong_matches) > 0) or (has_legal_terms and words > 300)
    
    # Calculate confidence level
    if score >= 80:
        confidence = "high"
    elif score >= 40:
        confidence = "medium"  
    elif score >= 20:
        confidence = "low"
    else:
        confidence = "minimal"
    
    details = {
        "score": score,
        "confidence": confidence,
        "legal_indicators": legal_indicators,
        "strong_matches": len(strong_matches),
        "medium_matches": len(medium_matches), 
        "word_count": words,
        "has_legal_terms": has_legal_terms,
        "analysis_recommendation": "analyze" if is_legal_document else "reject",
        "detected_type": "legal_document" if is_legal_document else "non_legal"
    }
    
    return is_legal_document, details

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