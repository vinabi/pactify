# agents/contract_detector.py
from __future__ import annotations
import re
from typing import Tuple, Dict, Any, List

# Core clause/term lexicons
CLAUSE_HEADINGS = [
    "confidentiality", "non-disclosure", "nda", "non disclosure",
    "governing law", "jurisdiction", "limitation of liability",
    "indemnification", "warranty", "warranties",
    "termination", "term and termination",
    "payment terms", "fees", "consideration",
    "intellectual property", "ip ownership", "license",
    "force majeure", "assignment", "entire agreement",
    "severability", "arbitration", "dispute resolution", "notice",
]

CONTRACT_SIGNALS = [
    # formation / signature
    r"\b(this\s+agreement|this\s+contract)\b",
    r"\bbetween\s+.+\s+and\s+.+\b",
    r"\b(the\s+parties|party\s+a|party\s+b)\b",
    r"\b(in witness whereof|signed\s+by|signatory|counterpart[s]?)\b",
    # elements of contract
    r"\boffer\b", r"\bacceptance\b", r"\bconsideration\b", r"\bcapacity\b", r"\bintent(ion)?\b",
    # common forms
    r"\bnon[-\s]?disclosure\s+agreement\b|\bnda\b",
    r"\bmaster\s+services?\s+agreement\b|\bmsa\b",
    r"\bstatement\s+of\s+work\b|\bsow\b",
    r"\blease\s+agreement\b|\bpurchase\s+agreement\b|\bsales?\s+contract\b",
]

NON_CONTRACT_SIGNALS = [
    r"\bblog\b|\bnewsletter\b|\bpress release\b|\bterms of use\b",
    r"\bprivacy policy\b|\bfaq(s)?\b|\btutorial\b|\bhow to\b",
]

HEADING_RE = re.compile(r"^\s*\d+(\.\d+)*\s+([A-Z][A-Za-z \-/&]{2,})\s*$", re.M)

def _count(patterns: List[str], text: str) -> int:
    return sum(1 for p in patterns if re.search(p, text, flags=re.I))

def looks_like_contract_v3(text: str) -> Tuple[bool, Dict[str, Any]]:
    """Heuristic contract detector with transparent scoring."""
    t = text if isinstance(text, str) else ""

    # Normalize
    flat = re.sub(r"\s+", " ", t).strip()

    # positive signals
    headings = [m.group(2).strip().lower() for m in HEADING_RE.finditer(t)]
    heading_hits = sum(any(h in hh for hh in headings) for h in CLAUSE_HEADINGS)
    signal_hits = _count(CONTRACT_SIGNALS, flat)

    # negative signals
    neg_hits = _count(NON_CONTRACT_SIGNALS, flat)

    # weighting
    score = 0
    score += 2 * min(heading_hits, 8)          # up to +16
    score += 3 * min(signal_hits, 6)           # up to +18
    score -= 3 * min(neg_hits, 3)              # down to -9

    # boost if explicit signatory block or “the Parties agree”
    if re.search(r"\b(the parties agree|in witness whereof)\b", flat, re.I):
        score += 6

    # decision thresholds
    is_contract = score >= 10

    details = {
        "score": score,
        "positives": [
            f"{heading_hits} clause headings matched",
            f"{signal_hits} contract signals matched",
        ],
        "negatives": [f"{neg_hits} non-contract signals matched"] if neg_hits else [],
        "example_headings": headings[:8],
    }
    return is_contract, details

# Backwards-compat alias used by your API
def looks_like_contract_v2(text: str):
    return looks_like_contract_v3(text)
