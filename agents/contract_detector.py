# agents/contract_detector.py
# Rule-based "is this a contract?" detector:
# - Jargon / clause cues
# - Parties phrasing
# - Section/heading structure
# - Signature blocks
# - Governing-law style language
# Returns (bool, details) with a 0..100 score and reasons.

from __future__ import annotations
import re
from typing import Dict, List, Tuple

# ----- Tunables -----
SHORT_MIN_WORDS = 100     # accept short NDAs
FULL_MIN_WORDS  = 350
ACCEPT_SCORE    = 55      # final threshold to accept
BINARY_MAX_RATIO = 0.20   # if >20% non-text bytes -> treat as parsing failure

# ----- Keyword banks -----
JARGON = [
    "whereas", "herein", "hereto", "thereof", "therein", "thereby",
    "notwithstanding", "pursuant", "indemnify", "indemnification",
    "warrant", "covenant", "assigns", "counterparts", "severability",
    "force majeure", "governing law", "venue", "jurisdiction",
    "confidentiality", "non-disclosure", "entire agreement",
    "limitation of liability", "arbitration", "remedies", "waiver",
]

CLAUSES = [
    "term", "termination", "confidentiality", "indemnity", "indemnification",
    "limitation of liability", "warranty", "representations", "assignment",
    "notices", "force majeure", "severability", "entire agreement", "waiver",
    "remedies", "dispute", "arbitration", "payment", "consideration",
    "scope of work", "deliverables", "acceptance",
    "intellectual property", "license", "non-solicitation", "non-compete",
    "governing law", "venue", "jurisdiction",
]

NEGATIVE_HINTS = [
    "```", "requirements.txt", "package.json", "pip install", "import ",
    "SELECT ", "CREATE TABLE", "api reference", "tutorial", "chapter",
    "lesson", "syllabus", "how to", "project manual",
]

# ----- Regexes -----
TITLE_PAT = re.compile(
    r"""(?imx)
    ^\s*(?:
        (?:MASTER|PROFESSIONAL|SOFTWARE|SERVICES|LICENSING|SUBSCRIPTION|
           NON[-\s]?DISCLOSURE|MUTUAL\s+NDA|EMPLOYMENT|LEASE|SUPPLY|PURCHASE|
           MEMORANDUM\s+OF\s+UNDERSTANDING|MOU|LETTER\s+OF\s+INTENT)\s+)?
       (?:AGREEMENT|CONTRACT|TERMS(?:\s+AND\s+CONDITIONS)?|
          STATEMENT\s+OF\s+WORK|SOW|CONFIDENTIALITY\s+AGREEMENT)\b
    """
)

WORD_FOR_PARTY = r"[A-Za-z0-9'’\-&.,()/ ]"
PARTIES_PAT = re.compile(
    rf"""(?ix)
    \b(?:
        this\s+agreement\s+is\s+made\s+(?:as\s+of\s+)?(?:the\s+)?[^,\n]{{0,120}}?\s+by\s+and\s+between
      | between\s+{WORD_FOR_PARTY}{{2,120}}\s+(?:and|&)\s+{WORD_FOR_PARTY}{{2,120}}
      | party\s+A.*\bparty\s+B
    )\b
    """
)

SIG_PAT = re.compile(
    r"(IN\s+WITNESS\s+WHEREOF|SIGNATURES?|By:\s*__|Signed\s+by|Name:\s|Title:\s|Date:\s|Authorized\s+Signatory)",
    re.IGNORECASE,
)

GOVLAW_PAT = re.compile(r"\b(governing\s+law|jurisdiction|venue|courts?\s+of)\b", re.IGNORECASE)

HEAD_PAT = re.compile(
    r"^(?:\d+(?:\.\d+){0,3}\s*[-.:)]\s*)?[A-Z][A-Z \-/]{3,}$|^SECTION\s+\d+\b.*$",
    re.MULTILINE,
)

# Utility
def _count(pattern: re.Pattern, text: str) -> int:
    return len(pattern.findall(text))

def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))

def _looks_binary(text: str) -> bool:
    # if the upstream PDF parser failed and we got bytes-like noise,
    # non-text chars ratio will be high.
    if not text:
        return False
    nonprint = sum(ch < " " and ch not in "\n\r\t" for ch in text)
    ratio = nonprint / max(1, len(text))
    return ratio > BINARY_MAX_RATIO

def looks_like_contract_v2(text: str) -> Tuple[bool, Dict]:
    reasons_pos: List[str] = []
    reasons_neg: List[str] = []
    score = 0

    t = text or ""
    n_words = _word_count(t)
    is_short = SHORT_MIN_WORDS <= n_words < FULL_MIN_WORDS

    # Binary/gibberish guard (parsing failed)
    if _looks_binary(t[:4000]):
        reasons_neg.append("Document appears binary/gibberish — PDF text extraction failed (-25)")
        score -= 25

    # Length gates (soft penalties, not hard fails)
    if n_words < SHORT_MIN_WORDS:
        reasons_neg.append(f"Very short: {n_words} words (<{SHORT_MIN_WORDS}) (-20)")
        score -= 20
    elif is_short:
        reasons_pos.append(f"Short-doc mode: {n_words} words")

    # Title cue
    if TITLE_PAT.search(t[:4000]):
        bump = 20 if is_short else 15
        reasons_pos.append(f"Title indicates agreement/contract (+{bump})")
        score += bump

    # Parties / Between … and …
    if PARTIES_PAT.search(t[:8000]):
        reasons_pos.append("Intro references the parties (+18)")
        score += 18

    # Headings / structure
    head_hits = min(_count(HEAD_PAT, t), 24)
    if head_hits >= (2 if is_short else 5):
        bump = 12 if is_short else 10
        reasons_pos.append(f"Found {head_hits} section headings (+{bump})")
        score += bump

    # Signature end block
    tail = t[-max(1400, len(t) // 4):]
    if SIG_PAT.search(tail):
        reasons_pos.append("Signature block near the end (+18)")
        score += 18

    # Governing-law style language
    if GOVLAW_PAT.search(t):
        reasons_pos.append("Governing-law / venue language (+8)")
        score += 8

    # Clause density
    clause_hits = 0
    for term in CLAUSES:
        if re.search(rf"\b{re.escape(term)}\b", t, re.IGNORECASE):
            clause_hits += 1
    clause_points = min(24, int((2.0 if is_short else 1.6) * clause_hits))
    if clause_hits:
        reasons_pos.append(f"{clause_hits} common clauses present (+{clause_points})")
        score += clause_points

    # Negative hints (tutorial/code/docs)
    neg_found = [term for term in NEGATIVE_HINTS if term.lower() in t.lower()]
    if neg_found:
        reasons_neg.append(f"Developer/guide vocabulary detected: {', '.join(neg_found[:5])} (-16)")
        score -= 16

    # Bullet-heavy penalty
    bullets = len(re.findall(r"^\s*(?:-|\*|•|\d+\.)\s+", t, re.MULTILINE))
    lines = max(1, len(t.splitlines()))
    if (bullets / lines) > (0.55 if is_short else 0.35):
        reasons_neg.append("Bullet-heavy document (-8)")
        score -= 8

    # Short-doc accept rule: any two of (title | parties | signature) + ≥4 clauses
    accept_rule = None
    if is_short:
        has_title = bool(TITLE_PAT.search(t[:4000]))
        has_parties = bool(PARTIES_PAT.search(t[:8000]))
        has_sig = bool(SIG_PAT.search(tail))
        strong = sum([has_title, has_parties, has_sig])
        if strong >= 2 and clause_hits >= 4:
            accept_rule = "short_doc_rule"
            reasons_pos.append("Short-doc accept rule matched")

    # Clamp and decide
    score = max(0, min(100, score))
    is_contract = (score >= ACCEPT_SCORE) or (accept_rule is not None)

    details: Dict = {"score": score, "positives": reasons_pos, "negatives": reasons_neg}
    if accept_rule:
        details["rule"] = accept_rule
    return is_contract, details
