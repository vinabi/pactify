# agents/contract_detector.py
from __future__ import annotations
import re, json
from typing import Tuple, Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger

# Reuse your existing LLM setup so we don't add new deps
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from api.settings import settings
from api.utils import JsonRepair

# --------------------------------------------------------------------------------------
# NORMALIZATION (kept – helpful for downstream tools)
# --------------------------------------------------------------------------------------
def normalize_contract_text(text: str) -> str:
    if not text:
        return ""
    text = text.encode("utf-8", errors="ignore").decode("utf-8")
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)  # page numbers
    text = re.sub(r"\n\s*Page\s+\d+\s+of\s+\d+\s*\n", "\n", text, flags=re.I)
    text = re.sub(r"-\s*\n\s*", "", text)        # join hyphenated words
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)# cap blank lines
    text = re.sub(r"[ \t]+", " ", text)
    return " ".join(text.split())

# --------------------------------------------------------------------------------------
# LLM-BASED CLASSIFIER (context-aware)
# --------------------------------------------------------------------------------------
def _make_llm():
    api_key = settings.groq_api_key
    model = settings.groq_model
    temperature = float(settings.groq_temperature)
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. See .env")
    return ChatGroq(groq_api_key=api_key, model_name=model, temperature=temperature)

_CLASSIFY_SYS = (
    "You are a legal document gatekeeper. "
    "Classify the provided text as one of: contract, legal_document, non_legal. "
    "Be strict and context-aware (not keyword counting). "
    "Detect the 4 contract essentials: offer_acceptance, consideration, legal_intent, capacity. "
    "Return STRICT JSON with this schema:\n"
    "{"
    '"label": "contract|legal_document|non_legal",'
    '"confidence": "high|medium|low|none",'
    '"reason": "<short reason>",'
    '"features": {'
        '"essential_elements": {"offer_acceptance": bool, "consideration": bool, "legal_intent": bool, "capacity": bool},'
        '"has_signature_blocks": bool,'
        '"num_distinct_parties": int,'
        '"max_heading_depth": int,'
        '"word_count": int'
    "}"
    "}"
)

def _classify_with_llm(text: str) -> Dict[str, Any]:
    llm = _make_llm()
    txt = normalize_contract_text(text)[:18000]  # keep prompt safe
    msgs = [
        SystemMessage(content=_CLASSIFY_SYS),
        HumanMessage(content=f"Document text:\n\n{txt}")
    ]
    res = llm.invoke(msgs)
    raw = res.content if isinstance(res.content, str) else str(res.content)
    data = JsonRepair.extract_json(raw)
    # sanity defaults
    label = (data.get("label") or "non_legal").lower().strip()
    conf = (data.get("confidence") or "low").lower().strip()
    reason = data.get("reason") or "No reason provided"
    features = data.get("features") or {}
    essentials = features.get("essential_elements") or {}
    # normalize essentials into dict of 4 keys
    essentials = {
        "offer_acceptance": bool(essentials.get("offer_acceptance", False)),
        "consideration": bool(essentials.get("consideration", False)),
        "legal_intent": bool(essentials.get("legal_intent", False)),
        "capacity": bool(essentials.get("capacity", False)),
    }
    features["essential_elements"] = essentials
    # add a convenience count
    features["essential_count"] = sum(1 for v in essentials.values() if v)
    out = {
        "label": label,
        "confidence": conf,
        "reason": reason,
        "features": {
            "has_signature_blocks": bool(features.get("has_signature_blocks", False)),
            "num_distinct_parties": int(features.get("num_distinct_parties", 0) or 0),
            "max_heading_depth": int(features.get("max_heading_depth", 0) or 0),
            "word_count": int(features.get("word_count", 0) or 0),
            "essential_elements": essentials,
            "essential_count": features["essential_count"],
        },
    }
    return out

# --------------------------------------------------------------------------------------
# SEMANTIC SIMILARITY GATE (embedding-based, no keyword rules)
# --------------------------------------------------------------------------------------
def _semantic_contract_similarity(text: str) -> Optional[float]:
    """
    Compute a semantic similarity score of the document to contract templates
    using sentence embeddings stored in Chroma. Returns None if unavailable.
    Scale: ~0.0 (unrelated) to ~1.0 (very similar).
    """
    try:
        # Local import to avoid hard dep at import-time
        import chromadb
        from chromadb.utils import embedding_functions

        client = chromadb.PersistentClient(path=settings.chroma_dir)
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        coll = client.get_or_create_collection(
            name="contract_templates", embedding_function=ef
        )
        # Query a trimmed version to keep perf good
        q = normalize_contract_text(text)[:4000]
        res = coll.query(query_texts=[q], n_results=5)
        distances = (res.get("distances") or [[]])[0]
        if not distances:
            return None
        # Chroma cosine distance -> similarity
        sims = [max(0.0, min(1.0, 1.0 - float(d))) for d in distances]
        return sum(sims) / max(1, len(sims))
    except Exception as e:
        logger.debug(f"Semantic similarity unavailable: {e}")
        return None

# --------------------------------------------------------------------------------------
# PUBLIC SURFACE (names preserved)
# --------------------------------------------------------------------------------------
def looks_like_contract_v2(text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Backwards-compatible API.
    Returns (is_contract: bool, details: Dict) where details['detected_type'] is one of:
    'contract', 'legal_document', 'non_legal'.
    """
    if not text or len(text.strip()) < 50:
        return False, {
            "detected_type": "non_legal",
            "confidence": "none",
            "reason": "Document too short for analysis",
            "features": {"word_count": len(text or "")},
        }
    try:
        result = _classify_with_llm(text)
        label = result["label"]
        # decorate to match old callers' expectations
        details = {
            "detected_type": label,
            "confidence": result.get("confidence", "low"),
            "reason": result.get("reason", ""),
            "features": result.get("features", {}),
        }
        return (label == "contract"), details
    except Exception as e:
        logger.exception("LLM classification failed; defaulting to non_legal")
        return False, {
            "detected_type": "non_legal",
            "confidence": "none",
            "reason": f"classifier_error: {e}",
            "features": {"word_count": len(text or "")},
        }

@dataclass
class DocGateResult:
    accept: bool
    label: str               # "contract" | "legal_document" | "non_legal"
    confidence: str
    reason: str
    details: Dict[str, Any]

def classify_document(text: str) -> DocGateResult:
    """
    Single source of truth for gating.
    Accept = contract OR legal_document. Reject = non_legal.
    """
    is_contract, details = looks_like_contract_v2(text)
    label = details.get("detected_type") or ("contract" if is_contract else "non_legal")
    conf = details.get("confidence", "low")
    reason = details.get("reason", "")

    # Derive structured features for context-aware gating
    feats = details.get("features", {}) if isinstance(details, dict) else {}
    essential_count = int(feats.get("essential_count") or 0)
    has_signatures = bool(feats.get("has_signature_blocks") or False)
    num_parties = int(feats.get("num_distinct_parties") or 0)
    word_count = int(feats.get("word_count") or 0)

    # Semantic similarity to known contract templates (if available)
    sem_sim = _semantic_contract_similarity(text)

    # Tighten acceptance: require joint semantic and structural evidence
    if is_contract:
        sim = (sem_sim or 0.0)
        strong_llm = conf in ("high", "medium") and essential_count >= 3
        strong_structure = num_parties >= 2 and (has_signatures or essential_count >= 3)
        strong_semantic = sim >= 0.55
        long_enough = word_count >= 150
        if strong_llm and strong_structure and strong_semantic and long_enough:
            return DocGateResult(
                accept=True, label="contract", confidence=conf,
                reason=reason or "Accepted: classified as contract",
                details={**details, "semantic_similarity": sem_sim},
            )
        return DocGateResult(
            accept=False, label="non_legal", confidence=conf,
            reason=(
                "Rejected: insufficient joint evidence (similarity, essentials, parties/signatures, length)"
            ),
            details={**details, "semantic_similarity": sem_sim},
        )

    if label == "legal_document":
        # Accept only with strong corroboration; otherwise reject to prevent false positives
        sim = (sem_sim or 0.0)
        supportive_semantic = sim >= 0.60
        supportive_structure = (essential_count >= 2 and num_parties >= 2) or has_signatures
        long_enough = word_count >= 120
        if conf in ("high", "medium") and long_enough and (supportive_semantic and supportive_structure):
            return DocGateResult(
                accept=True, label="legal_document", confidence=conf,
                reason=reason or "Accepted: legal document (not a full contract)",
                details={**details, "semantic_similarity": sem_sim},
            )
        return DocGateResult(
            accept=False, label="non_legal", confidence=conf,
            reason=(
                "Rejected: lacks strong semantic and structural evidence of legal document"
            ),
            details={**details, "semantic_similarity": sem_sim},
        )

    return DocGateResult(
        accept=False, label="non_legal", confidence=conf,
        reason=reason or "Rejected: not a legal or contract-like document",
        details=details,
    )

# --------------------------------------------------------------------------------------
# RISK/TYPE UTILITIES (unchanged behaviour)
# --------------------------------------------------------------------------------------
RED_FLAGS: List[Dict[str, Any]] = [
    {"label": "Unlimited liability exposure","severity": "high","category": "liability",
     "pattern": r"\b(unlimited|without\s+limit|no\s+cap|all\s+damages)\b.*\b(liability|damages|loss)\b",
     "description": "Exposes party to unlimited financial risk"},
    {"label": "One-sided indemnification","severity": "high","category": "indemnity",
     "pattern": r"\b(?:client|contractor|vendor|party)\s+(?:shall|will|agrees?\s+to)\s+indemnify.*(?!.*mutual|each\s+party)",
     "description": "Only one party bears indemnification burden"},
    {"label": "Broad IP assignment beyond scope","severity": "high","category": "intellectual_property",
     "pattern": r"\b(all|any)\s+(?:inventions?|developments?|works?|intellectual\s+property|improvements)\b.*\b(assign|transfer|belong|property|sole\s+property)\b",
     "description": "Assigns IP beyond project deliverables"},
    {"label": "Termination only for cause","severity": "high","category": "termination",
     "pattern": r"\btermination?\b.*\b(?:only|solely)\s+(?:for\s+cause|upon\s+breach)\b",
     "description": "No termination for convenience option"},
    {"label": "Auto-renewal without adequate notice","severity": "medium","category": "termination",
     "pattern": r"\b(?:auto(?:matic(?:ally)?)?|shall)\s+(?:renew|extend)\b",
     "description": "Auto-renewal clause detected"},
    {"label": "Excessive interest or penalty rates","severity": "medium","category": "payment",
     "pattern": r"\b(?:1[8-9]|2[0-9]|[3-9][0-9])%\s+(?:per\s+annum|interest|penalty)",
     "description": "Interest or penalty rates above 18% annually"},
    {"label": "Unlimited indemnification scope","severity": "high","category": "indemnity",
     "pattern": r"\bindemnify.*\b(?:regardless|whether\s+caused\s+by|all\s+claims)",
     "description": "Indemnification without carve-outs for gross negligence"},
    {"label": "Payment terms exceeding NET 60","severity": "medium","category": "payment",
     "pattern": r"\bnet\s+(?:6[5-9]|[7-9]\d|\d{3,})\s+days?\b|\bpayment.*(?:90|120|\d{3,})\s+days?\b",
     "description": "Extended payment terms harm cash flow"},
    {"label": "Confidentiality without time limit","severity": "medium","category": "confidentiality",
     "pattern": r"\bconfidential.*\b(?!.*(?:\d+\s+years?|term\s+of|upon\s+termination))",
     "description": "Perpetual confidentiality obligations"},
    {"label": "Non-compete exceeding 1 year","severity": "medium","category": "restrictions",
     "pattern": r"\bnon[- ]?compete.*\b(?:[2-9]\d*|[1-9]\d+)\s+years?\b",
     "description": "Excessive non-compete restriction period"},
    {"label": "Governing law in unfavorable jurisdiction","severity": "medium","category": "dispute",
     "pattern": r"\bgoverning\s+law.*\b(?:delaware|new\s+york|california)\b(?!.*mutual)",
     "description": "May favor other party's jurisdiction"},
    {"label": "Mandatory arbitration with limited discovery","severity": "medium","category": "dispute",
     "pattern": r"\barbitration\b.*\b(?:final|binding)\b.*(?!.*discovery|appeal)",
     "description": "Limits legal recourse and discovery rights"},
    {"label": "Missing liability cap clause","severity": "low","category": "liability",
     "pattern": r"(?!.*limit(?:ation)?\s+of\s+liability)", "needs_absence_check": True,
     "description": "Should include liability limitations"},
    {"label": "Vague performance standards","severity": "low","category": "performance",
     "pattern": r"\b(?:reasonable|best|commercially\s+reasonable)\s+efforts?\b",
     "description": "Performance standards are subjective"},
    {"label": "Force majeure without mutual protection","severity": "low","category": "force_majeure",
     "pattern": r"\bforce\s+majeure\b.*(?!.*both\s+parties|each\s+party)",
     "description": "Force majeure may not protect both parties"},
]

def find_red_flags(text: str) -> List[Dict[str, Any]]:
    if not text: return []
    normalized = " ".join(text.split()).lower()
    hits: List[Dict[str, Any]] = []
    for rf in RED_FLAGS:
        if rf.get("needs_absence_check"):
            if rf["category"] == "liability":
                if not re.search(r"\blimit(?:ation)?\s+of\s+liability|liability\s+(?:cap|limit)", normalized, re.I):
                    hits.append({"label": rf["label"], "severity": rf["severity"], "category": rf["category"], "description": rf["description"]})
        else:
            if re.search(rf["pattern"], normalized, re.I | re.S):
                hits.append({"label": rf["label"], "severity": rf["severity"], "category": rf["category"], "description": rf["description"], "pattern": rf["pattern"]})
    return hits

# ---------- Template/type helpers (left as before) ----------
def identify_contract_type(text: str) -> (str, float):
    if not text: return "unknown", 0.0
    normalized = text.lower()
    contract_types = {
        "Non-Disclosure Agreement": [
            (r"\b(?:non[- ]?disclosure|confidentiality)\s+agreement\b", 0.9),
            (r"\bconfidential\s+information\b", 0.3),
            (r"\bdisclosure\b.*\bconfidential\b", 0.4),
            (r"\breceiving\s+party\b.*\bdisclosing\s+party\b", 0.7),
        ],
        "Service Agreement": [
            (r"\b(?:master\s+)?service(?:s)?\s+agreement\b", 0.9),
            (r"\bstatement\s+of\s+work\b", 0.8),
            (r"\bservice(?:s)?\b.*\bperform\b", 0.3),
            (r"\bdeliverable(?:s)?\b", 0.4),
        ],
        "Employment Agreement": [
            (r"\bemployment\s+agreement\b", 0.9),
            (r"\bemployee\b.*\bemployer\b", 0.7),
            (r"\bsalary\b.*\bbenefits?\b", 0.5),
            (r"\btermination\s+of\s+employment\b", 0.6),
        ],
    }
    best_type, best_score = "unknown", 0.0
    for ctype, patterns in contract_types.items():
        score = 0.0
        for pattern, weight in patterns:
            if re.search(pattern, normalized): score += weight
        normalized_score = score / len(patterns)
        if normalized_score > best_score:
            best_score, best_type = normalized_score, ctype
    return best_type, best_score

def compare_to_templates(contract_text: str, vect_client=None) -> Dict[str, Any]:
    if not vect_client or not contract_text:
        return {"template_matches": [], "deviations": [], "coverage_score": 0.0}
    try:
        ctype, type_conf = identify_contract_type(contract_text)
        from .tools_vector import retrieve_snippets
        template_matches = []
        try:
            matches = retrieve_snippets(vect_client, "contract_templates", contract_text, k=5)
            for meta, doc in matches:
                template_matches.append({
                    "template_type": meta.get("contract_type", "Unknown"),
                    "clause_type": meta.get("clause_type", "General"),
                    "similarity_score": meta.get("score", 0.5),
                    "template_text": (doc[:300] + "...") if len(doc) > 300 else doc,
                })
        except Exception as e:
            logger.warning(f"Template retrieval failed: {e}")

        deviations = analyze_template_deviations(contract_text, ctype)
        coverage_score = calculate_template_coverage(contract_text, template_matches)
        return {
            "identified_type": ctype,
            "type_confidence": type_conf,
            "template_matches": template_matches,
            "deviations": deviations,
            "coverage_score": coverage_score,
            "recommendations": generate_template_recommendations(deviations),
        }
    except Exception as e:
        logger.error(f"Template comparison failed: {e}")
        return {"error": str(e), "template_matches": [], "deviations": []}

def analyze_template_deviations(text: str, contract_type: str) -> List[Dict]:
    deviations: List[Dict[str, Any]] = []
    expected_clauses = {
        "Non-Disclosure Agreement": ["confidential_information_definition","permitted_disclosures","return_of_information","term_duration"],
        "Service Agreement": ["scope_of_work","payment_terms","intellectual_property","termination_rights","liability_limitations"],
        "Employment Agreement": ["job_responsibilities","compensation_benefits","termination_conditions","non_compete_clause","confidentiality"],
    }
    expected = expected_clauses.get(contract_type, [])
    normalized = text.lower()
    for clause_type in expected:
        if not has_clause_type(normalized, clause_type):
            deviations.append({"type": "missing_clause","clause_type": clause_type,"severity": "medium","description": f"Missing standard {clause_type.replace('_', ' ')} clause"})
    unusual_patterns = [
        (r"\bperpetual\b", "perpetual_term", "Unusual perpetual term"),
        (r"\btrial\s+by\s+jury\s+waiver\b", "jury_waiver", "Jury trial waiver clause"),
        (r"\bexclusive\s+jurisdiction\b", "exclusive_jurisdiction", "Exclusive jurisdiction clause"),
        (r"\battorney(?:s)?\s+fees?\b.*\bprevailing\s+party\b", "attorney_fees", "Attorney fees clause"),
    ]
    for pattern, clause_type, description in unusual_patterns:
        if re.search(pattern, normalized):
            deviations.append({"type": "unusual_clause","clause_type": clause_type,"severity": "low","description": description})
    return deviations

def has_clause_type(text: str, clause_type: str) -> bool:
    patterns = {
        "confidential_information_definition": r"\bconfidential\s+information\b.*\bmeans\b",
        "permitted_disclosures": r"\bpermitted\s+disclosure\b|\bexceptions?\b.*\bconfidentialit",
        "return_of_information": r"\breturn\b.*\b(?:information|materials?|documents?)\b",
        "term_duration": r"\bterm\b.*\b(?:years?|months?|period)\b",
        "scope_of_work": r"\bscope\s+of\s+work\b|\bservice(?:s)?\s+(?:to\s+be\s+)?provided\b",
        "payment_terms": r"\bpayment\s+terms?\b|\bcompensation\b|\bfees?\b",
        "intellectual_property": r"\bintellectual\s+property\b|\bownership\b.*\bwork\s+product\b",
        "termination_rights": r"\btermination\b.*\b(?:rights?|notice)\b",
        "liability_limitations": r"\blimitation\s+of\s+liability\b|\bliability\s+cap\b",
    }
    pattern = patterns.get(clause_type)
    return bool(re.search(pattern, text, re.I)) if pattern else False

def calculate_template_coverage(text: str, matches: List[Dict]) -> float:
    if not matches: return 0.0
    total = sum(m.get("similarity_score", 0) for m in matches)
    return min(total / len(matches), 1.0)

def generate_template_recommendations(deviations: List[Dict]) -> List[str]:
    recs: List[str] = []
    missing = sum(1 for d in deviations if d["type"] == "missing_clause")
    unusual = sum(1 for d in deviations if d["type"] == "unusual_clause")
    if missing > 2: recs.append("Consider adding missing standard clauses to improve contract completeness")
    if unusual > 0: recs.append("Review unusual clauses for potential risks and enforceability issues")
    if not missing and not unusual: recs.append("Contract structure aligns well with standard templates")
    return recs
