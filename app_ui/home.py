# home.py  (place at repo root for Streamlit Cloud)
import os, requests, streamlit as st
from typing import Dict, Any

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Contract Risk Analyzer", layout="wide", page_icon="⚖️")
st.title("⚖️ Contract Risk Analyzer")
st.caption("Upload a contract → detect risks → propose redlines → summarize")

with st.sidebar:
    st.header("Options")
    strict_mode = st.toggle("Strict mode", value=True)
    jurisdiction = st.selectbox("Jurisdiction", ["General", "US", "EU", "UK", "PK", "AE"])
    top_k_precedents = st.slider("Precedent grounding (k)", 0, 3, 0)
    st.divider()
    st.markdown("**Backend**:")
    st.code(API_URL)

uploaded_file = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf", "docx", "txt"], accept_multiple_files=False)
if uploaded_file:
    st.session_state["last_file_name"] = uploaded_file.name
    st.session_state["last_file_bytes"] = uploaded_file.getvalue()
    guessed = uploaded_file.type or ""
    if not guessed or guessed == "application/octet-stream":
        if uploaded_file.name.lower().endswith(".pdf"):
            guessed = "application/pdf"
        elif uploaded_file.name.lower().endswith(".docx"):
            guessed = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            guessed = "text/plain"
    st.session_state["last_file_type"] = guessed

to_email = st.text_input("Recipient email (SendGrid)", value=st.session_state.get("email_input", "your@gmail.com"), key="email_input")

colA, colB = st.columns([1,1])
with colA:
    if st.button("Analyze", type="primary", use_container_width=True):
        if "last_file_bytes" not in st.session_state:
            st.error("Please upload a file.")
            st.stop()
        with st.spinner("Analyzing..."):
            files = {"file": (st.session_state["last_file_name"], st.session_state["last_file_bytes"], st.session_state["last_file_type"])}
            params = {"strict_mode": str(strict_mode).lower(), "jurisdiction": jurisdiction, "top_k_precedents": int(top_k_precedents)}
            try:
                r = requests.post(f"{API_URL}/analyze", params=params, files=files, timeout=600)
                if r.status_code == 422:
                    dj = r.json().get("detail", {})
                    st.error(dj.get("message", "Rejected"))
                    st.info("**Contract-likeness signals (positives):**\n- " + "\n- ".join(dj.get("positives", []) or ["(none)"]))
                    st.warning("**Non-contract signals (negatives):**\n- " + "\n- ".join(dj.get("negatives", []) or ["(none)"]))
                    st.write("Score:", dj.get("score"))
                r.raise_for_status()
                st.session_state["analysis"] = r.json()
            except requests.HTTPError as e:
                try:
                    detail = r.json().get("detail")
                except Exception:
                    detail = str(e)
                st.error(f"API error: {detail}")
                st.stop()
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

with colB:
    if st.button("Override and analyze anyway", use_container_width=True):
        if "last_file_bytes" not in st.session_state:
            st.error("Upload a file first")
            st.stop()
        files = {"file": (st.session_state["last_file_name"], st.session_state["last_file_bytes"], st.session_state["last_file_type"])}
        params = {"strict_mode": str(strict_mode).lower(), "jurisdiction": jurisdiction, "top_k_precedents": int(top_k_precedents), "allow_non_contract": "true"}
        with st.spinner("Forcing analysis..."):
            r2 = requests.post(f"{API_URL}/analyze", params=params, files=files, timeout=600)
            try:
                r2.raise_for_status()
                st.session_state["analysis"] = r2.json()
                st.rerun()
            except Exception as e:
                st.error(f"Override failed: {e}")

st.divider()
if "analysis" in st.session_state:
    data: Dict[str, Any] = st.session_state["analysis"]

    c1, c2 = st.columns([3,2])
    with c1:
        st.subheader("Executive Summary")
        st.write(data.get("summary", ""))
    with c2:
        st.subheader("Risk Overview")
        hi, me, lo = data.get("high_risk_count",0), data.get("medium_risk_count",0), data.get("low_risk_count",0)
        st.metric("High", hi); st.metric("Medium", me); st.metric("Low", lo)

    st.subheader("Clauses")
    for c in data.get("clauses", []):
        with st.expander(f"{c['id']} • {c['heading']} • {c['category']} • Risk: {c['risk']}"):
            st.markdown("**Original**"); st.write(c.get("text",""))
            st.markdown("**Rationale**"); st.write(c.get("rationale",""))
            if c.get("policy_violations"):
                st.markdown("**Policy Violations**")
                for v in c.get("policy_violations", []): st.write("- ", v)
            if c.get("proposed_text"):
                st.markdown("**Suggested Redline**"); st.write(c["proposed_text"])
                st.markdown("**Why**"); st.write(c.get("explanation",""))
                st.markdown("**Negotiation Note**"); st.write(c.get("negotiation_note",""))

    st.divider()
    st.subheader("Next actions")
    file_name = st.session_state.get("last_file_name")
    file_bytes = st.session_state.get("last_file_bytes")
    if st.button("Send Email (SendGrid)"):
        if not file_bytes or not to_email or "@" not in to_email:
            st.error("Upload a file and enter a valid recipient email")
        else:
            # Build a quick HTML list of all violations
            issues = []
            for c in data.get("clauses", []):
                for v in c.get("policy_violations", []):
                    issues.append(f"<li><b>{c['id']} – {c['heading']}</b>: {v}</li>")
            html = f"<h3>Detected risks</h3><ul>{''.join(issues) or '<li>No issues detected</li>'}</ul>"
            files = {"file": (file_name, file_bytes)}
            resp = requests.post(f"{API_URL}/send_email",
                                 params={"to_email": to_email, "subject": "Contract risk report"},
                                 files=files, data={"body": html}, timeout=60)
            if resp.ok:
                st.success(f"Email sent (status {resp.json().get('provider_status')})")
            else:
                st.error(f"Email failed: {resp.status_code} {resp.text}")

st.caption("⚠️ Research prototype. Human review required.")
