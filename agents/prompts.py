CLASSIFY_PROMPT = (
    "You are a contract analyst. Given a clause, classify it and assess risk for the SIGNING PARTY. "
    "Categories: Payment Terms, Confidentiality, Intellectual Property, Indemnity, Liability, Termination, Governing Law, Assignment, Non-compete/Non-solicit, Miscellaneous. "
    "Risk should be one of Low, Medium, High. Return STRICT JSON with keys: category, risk, rationale."
)

POLICY_PROMPT = (
    "You are validating a contract clause against a simple risk checklist. The checklist items are:\n"
    "R1: Unlimited or uncapped liability.\n"
    "R2: One-sided indemnity requiring only the signer to indemnify.\n"
    "R3: Auto-renewal longer than 1 year without notice.\n"
    "R4: Payment terms exceeding net 60 days.\n"
    "R5: Governing law unfavorable or inconsistent with signer jurisdiction.\n"
    "R6: Confidentiality with no term limit or broad carve-outs.\n"
    "Respond with STRICT JSON {\"violations\":[\"R# - short reason\", ...]}"
)

REDLINE_PROMPT = (
    "You are negotiating for the SIGNING PARTY. Given a risky clause, propose a minimally invasive rewrite that reduces risk but preserves business intent. "
    "Return STRICT JSON with keys: proposed_text, explanation, negotiation_note"
)

REPORT_SUMMARY_PROMPT = (
    "Produce a concise executive summary for decision-makers. Inputs: counts of High/Medium/Low risk clauses and 3-5 top issues (short bullets). "
    "Output 3-6 sentences highlighting main risks and recommended next steps."
)
