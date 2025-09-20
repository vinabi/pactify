from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# === Tunables (softer for short docs) ===
MIN_WORDS_FULL = 350        # was 400
MIN_WORDS_SHORT = 120       # was 150
ACCEPT_SCORE = 55           # was 60

# ---------- helpers ----------
_WORD = r"[A-Za-z0-9'’\-&.,()\/]"

TITLE_PAT = re.compile(
    r"""(?mx)
    ^\s*
    (?:(?:MASTER|PROFESSIONAL|SOFTWARE|SERVICES|LICENSING|
         NON[-\s]DISCLOSURE|MUTUAL\s+NDA|EMPLOYMENT|LEASE|SUPPLY|PURCHASE|SUBSCRIPTION|
         MEMORANDUM\s+OF\s+UNDERSTANDING|MOU|LETTER\s+OF\s+INTENT)\s+)?   # more titles
    (?:AGREEMENT|CONTRACT|TERMS(?:\s+AND\s+CONDITIONS)?|
       STATEMENT\s+OF\s+WORK|SOW|CONFIDENTIALITY\s+AGREEMENT)\b
    """,
    re.IGNORECASE,
)

PARTIES_PAT = re.compile(
    r"""(?ix)
    \b(?:this\s+agreement\s+is\s+made\s+(?:as\s+of\s+)?(?:the\s+)?[^,\n]{0,120}?
       \s+by\s+and\s+between\b
      |between\b\s+{w}{{2,120}}\s+(?:and|&)\s+{w}{{2,120}}
      |party\s+A.*\bparty\s+B  # very rough fallback
    )""".format(w=_WORD),
)

SIG_BLOCK_PAT = re.compile(
    r"(IN\s+WITNESS\s+WHEREOF|SIGNATURES?|By:\s*__|Signed\s+by|Name:\s|Title:\s|Date:\s|Authorized\s+Signatory)",
    re.IGNORECASE,
)

GOV_LAW_PAT = re.compile(r"\b(governing\s+law|jurisdiction|venue|courts?\s+of)\b", re.IGNORECASE)

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
        score -= 20  # softer penalty (was -25)
    elif is_short:
        reasons_pos.append(f"Short document mode ({n_words} words)")

    # L1 — structural cues
    if TITLE_PAT.search(t[:4000]):
        score += 22 if is_short else 15
        reasons_pos.append("Title indicates agreement/contract")

    if PARTIES_PAT.search(t[:8000]):
        score += 18
        reasons_pos.append("Intro references parties")

    head_hits = min(_count(HEAD_PAT, t), 20)
    if head_hits >= (2 if is_short else 5):
        bump = 12 if is_short else 10
        score += bump
        reasons_pos.append(f"Has {head_hits} section headings (+{bump})")

    if SIG_BLOCK_PAT.search(t[-max(1400, n_chars // 4):]):
        score += 18
        reasons_pos.append("Signature block indicators near end")

    if GOV_LAW_PAT.search(t):
        score += 8
        reasons_pos.append("Governing-law / venue language present")

    # L2 — clause density
    clause_hits = sum(1 for term in BOILERPLATE if re.search(rf"\b{re.escape(term)}\b", t, re.IGNORECASE))
    clause_points = min(24, int((2.2 if is_short else 1.6) * clause_hits))  # a little higher
    score += clause_points
    if clause_hits:
        reasons_pos.append(f"{clause_hits} common contract clauses found (+{clause_points})")

    # L3 — negatives
    neg_hits = [term for term in NEGATIVE_TERMS if term.lower() in t.lower()]
    if neg_hits:
        score -= 18  # softer than -25
        reasons_neg.append(f"Developer/guide vocabulary detected: {', '.join(neg_hits[:5])}")

    bullets = len(re.findall(r"^\s*(?:-|\*|•|\d+\.)\s+", t, re.MULTILINE))
    lines = max(1, len(t.splitlines()))
    if (bullets / lines) > (0.55 if is_short else 0.35):  # less sensitive for short docs
        score -= 8
        reasons_neg.append("Bullet-heavy document")

    # Explicit accept rule for short docs
    accept_rule = None
    if is_short:
        has_title = bool(TITLE_PAT.search(t[:4000]))
        has_parties = bool(PARTIES_PAT.search(t[:8000]))
        has_sig = bool(SIG_BLOCK_PAT.search(t[-max(1400, n_chars // 4):]))
        if (has_title and clause_hits >= 4) or (has_parties and clause_hits >= 4) or (has_sig and clause_hits >= 4):
            accept_rule = "short_doc_rule"
            reasons_pos.append("Short-doc accept rule matched")

    # Decision
    score = max(0, min(100, score))
    is_contract = (score >= ACCEPT_SCORE) or (accept_rule is not None)

    details = {"score": score, "positives": reasons_pos, "negatives": reasons_neg}
    if accept_rule:
        details["rule"] = accept_rule
    return is_contract, details
