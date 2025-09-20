# agents/contract_detector.py
from __future__ import annotations
import re
from typing import Tuple, Dict, Any, List

# ---------- stronger contract-likeness signals ----------
POS_PATTERNS = [
    r"\b(non-?disclosure|nda)\b",
    r"\b(master (services?|service) agreement|msa)\b",
    r"\b(statement of work|sow)\b",
    r"\b(terms?\s+and\s+conditions|t&c)\b",
    r"\b(confidentiality|proprietary information)\b",
    r"\b(indemnif(?:y|ication))\b",
    r"\b(limit(?:ation)? of liability|liability cap)\b",
    r"\b(governing law|venue|jurisdiction)\b",
    r"\b(term(?:ination)?|renewal)\b",
    r"\b(intellectual property|ip ownership|work[- ]?made[- ]?for[- ]?hire)\b",
    r"\b(payment|fees|invoice)\b",
]
NEG_PATTERNS = [
    r"\bblog\b", r"\bpress release\b", r"\bsyllabus\b", r"\bhow to\b", r"\bnewsletter\b",
    r"\bprivacy policy\b", r"\bcookie policy\b"
]

def looks_like_contract_v2(text: str) -> Tuple[bool, Dict[str, Any]]:
    t = " ".join((text or "").split())
    pos = [p for p in POS_PATTERNS if re.search(p, t, re.I)]
    neg = [n for n in NEG_PATTERNS if re.search(n, t, re.I)]
    words = len(t.split())
    has_sections = bool(re.search(r"\b(section|clause|article)\b", t, re.I))
    has_sign = bool(re.search(r"\bsign(?:ed|ature)\b", t, re.I))
    score = 0
    score += 3 * min(len(pos), 7)
    score += 2 if has_sections else 0
    score += 1 if has_sign else 0
    score += 2 if words > 250 else 0
    score -= 3 * min(len(neg), 3)
    return (score >= 8, {"score": score, "positives": pos, "negatives": neg})

# ---------- deterministic red-flags ----------
RED_FLAGS: List[Dict[str, Any]] = [
    {
        "label": "Unlimited liability (includes indirect/consequential/punitive; no cap/limit)",
        "severity": "high",
        "pattern": r"\b(no|without)\s+(?:any\s+)?(?:limit|cap)\b|(?:all|any)\s+damages(?:,|\s)+(?:including\s+)?(?:consequential|special|punitive|indirect)",
    },
    {
        "label": "Unilateral indemnity favoring other party",
        "severity": "high",
        "pattern": r"\bindemnif(?:y|ication)\b.{0,120}\bhold harmless\b.{0,120}\b(?:provider|client|company|contractor)\b",
    },
    {
        "label": "Over-broad IP assignment / work-made-for-hire",
        "severity": "medium",
        "pattern": r"\b(all|any)\s+(?:inventions|developments|works|ip)\b.{0,40}\b(assign|belong)\b|work[- ]?made[- ]?for[- ]?hire",
    },
    {
        "label": "Auto-renewal without clear notice",
        "severity": "medium",
        "pattern": r"\b(auto[- ]?renew|automatic(?:ally)?\s+renew)s?\b",
    },
    {
        "label": "No termination for convenience / unilateral termination only",
        "severity": "medium",
        "pattern": r"\bterminate\b.{0,40}\b(?:only|sole(?:ly)?)\b|\bno\s+right\s+to\s+terminate\b",
    },
    {
        "label": "Missing liability cap clause",
        "severity": "medium",
        "pattern": r"(?!.*limit(?:ation)?\s+of\s+liability)",
        "needs_absence_check": True,
    },
]

def find_red_flags(text: str) -> List[Dict[str, Any]]:
    t = " ".join((text or "").split())
    hits: List[Dict[str, Any]] = []
    for rf in RED_FLAGS:
        if rf.get("needs_absence_check"):
            if not re.search(r"\blimit(?:ation)?\s+of\s+liability|liability\s+cap", t, re.I):
                hits.append({"label": rf["label"], "severity": rf["severity"]})
        else:
            if re.search(rf["pattern"], t, re.I | re.S):
                hits.append({"label": rf["label"], "severity": rf["severity"], "pattern": rf["pattern"]})
    return hits
