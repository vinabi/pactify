# agents/contract_detector.py
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Tunables
MIN_WORDS_FULL = 400       # full contract expected above this length
MIN_WORDS_SHORT = 150      # short-doc mode between MIN_WORDS_SHORT..MIN_WORDS_FULL
ACCEPT_SCORE = 60          # score needed to accept (unless short-doc accept rule fires)

# ---------- helpers ----------
_WORD = r"[A-Za-z0-9'’\-&.,()\/]"

TITLE_PAT = re.compile(
    r"^\s*(?:(?:MASTER|PROFESSIONAL|SOFTWARE|SERVICES|LICENSING|NON[- ]DISCLOSURE|EMPLOYMENT|LEASE|SUPPLY|PURCHASE|SUBSCRIPTION)\s+)?"
    r"(?:AGREEMENT|CONTRACT|TERMS(?:\s+AND\s+CONDITIONS)?|STATEMENT\s+OF\s+WORK|SOW)\b",
    re.IGNORECASE | re.MULTILINE,
)

PARTIES_PAT = re.compile(
    r"\b(this\s+agreement\s+is\s+made\s+(?:as\s+of\s+)?(?:the\s+)?[^,]{0,80}?\s+by\s+and\s+between\b|\bbetween\b\s+"
    rf"{_WORD}{{2,80}}\s+(?:and|&)\s+{_WORD}{{2,80}})",
    re.IGNORECASE,
)

SIG_BLOCK_PAT = re.compile(
    r"(IN\s+WITNESS\s+WHEREOF|SIGNATURES?|By:\s*__|Signed\s+by|Name:\s|Title:\s|Date:\s)",
    re.IGNORECASE,
)

GOV_LAW_PAT = re.compile(r"\b(governing\s+law|jurisdiction|venue|courts?\s+of)\b", re.IGNORECASE)

# headings like "1.", "1.1", "SECTION 5 – CONFIDENTIALITY", "CONFIDENTIALITY"
HEAD_PAT = re.compile(
    r"^(?:\d+(?:\.\d+){0,3}\s*[-.:)]\s*)?[A-Z][A-Z \-/]{3,}$|^SECTION\s+\d+\b.*$",
    re.MULTILINE,
)

BOILERPLATE = [
    "term", "termination", "confidential", "non-disclosure", "indemn", "limitation of liability",
    "warranty", "representation", "assignment", "notices", "force majeure", "severability",
    "entire agreement", "waiver", "remedies", "dispute", "arbitration", "audit",
    "compliance", "payment", "consideration", "scope of work", "deliverables", "acceptance",
    "intellectual property", "license", "non-solicitation", "non-compete", "counterpart",
    "amendment", "survival", "governing law",
]

NEGATIVE_TERMS = [
    "pip install", "import ", "SELECT ", "CREATE TABLE", "json:", "yaml", "```", "requirements.txt",
    "package.json", "readme", "tutorial", "chapter", "lesson", "homework", "syllabus",
    "how to", "step 1", "step 2", "project manual", "api reference",
]

@dataclass
class ContractHeuristics:
    score: int
    reasons_pos: List[str]
    reasons_neg: List[str]

    def to_dict(self) -> Dict:
        return {"score": self.score, "positives": self.reasons_pos, "negatives": self.reasons_neg}

def _count(pattern: re.Pattern, text: str) -> int:
    return len(pattern.findall(text))

def looks_like_contract_v2(text: str) -> Tuple[bool, Dict]:
    """Return (is_contract, details). Deterministic scoring 0..100 with short-doc mode."""
    reasons_pos: List[str] = []
    reasons_neg: List[str] = []
    score = 0

    t = text or ""
    n_chars = len(t)
    n_words = len(re.findall(r"\b\w+\b", t))
    is_short = MIN_WORDS_SHORT <= n_words < MIN_WORDS_FULL

    # L0 — sanity
    if n_words < MIN_WORDS_SHORT:
        reasons_neg.append(f"Too short: {n_words} words (<{MIN_WORDS_SHORT})")
        score -= 25
    elif is_short:
        reasons_pos.append(f"Short document mode ({n_words} words)")

    # L1 — structural cues
    if TITLE_PAT.search(t[:3000]):
        score += 20 if is_short else 15
        reasons_pos.append("Title indicates agreement/contract")

    if PARTIES_PAT.search(t[:6000]):
        score += 20
        reasons_pos.append("Intro references parties")

    head_hits = min(_count(HEAD_PAT, t), 15)
    if head_hits >= (2 if is_short else 5):
        score += 10
        reasons_pos.append(f"Has {head_hits} section headings")

    if SIG_BLOCK_PAT.search(t[-max(1000, n_chars // 5):]):
        score += 20
        reasons_pos.append("Signature block indicators near end")

    if GOV_LAW_PAT.search(t):
        score += 10
        reasons_pos.append("Governing-law / venue language present")

    # L2 — clause density
    clause_hits = sum(1 for term in BOILERPLATE if re.search(rf"\b{re.escape(term)}\b", t, re.IGNORECASE))
    clause_points = min(20, int((2.0 if is_short else 1.5) * clause_hits))
    score += clause_points
    if clause_hits:
        reasons_pos.append(f"{clause_hits} common contract clauses found (+{clause_points})")

    # L3 — negatives
    neg_hits = [term for term in NEGATIVE_TERMS if term.lower() in t.lower()]
    if neg_hits:
        score -= 25
        reasons_neg.append(f"Developer/guide vocabulary detected: {', '.join(neg_hits[:5])}")

    bullets = len(re.findall(r"^\s*(?:-|\*|•|\d+\.)\s+", t, re.MULTILINE))
    lines = max(1, len(t.splitlines()))
    if (bullets / lines) > (0.45 if is_short else 0.30):
        score -= 10
        reasons_neg.append("Bullet-heavy document")

    # Explicit accept rule for short docs
    accept_rule = None
    if is_short:
        has_title = bool(TITLE_PAT.search(t[:3000]))
        has_parties = bool(PARTIES_PAT.search(t[:6000]))
        has_sig = bool(SIG_BLOCK_PAT.search(t[-max(1000, n_chars // 5):]))
        if (has_title and clause_hits >= 6) or (has_parties and clause_hits >= 4) or (has_sig and clause_hits >= 4):
            accept_rule = "short_doc_rule"
            reasons_pos.append("Short-doc accept rule matched")

    # Decision
    score = max(0, min(100, score))
    is_contract = (score >= ACCEPT_SCORE) or (accept_rule is not None)

    details = {"score": score, "positives": reasons_pos, "negatives": reasons_neg}
    if accept_rule:
        details["rule"] = accept_rule
    return is_contract, details
