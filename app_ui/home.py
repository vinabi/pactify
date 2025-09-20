# app_ui/home.py  — minimal changes to keep Override visible
import os, requests, json
import streamlit as st
from typing import Dict, Any

API_URL = st.secrets.get("API_URL", os.environ.get("API_URL", "http://127.0.0.1:8080"))

st.set_page_config(page_title="Contract Risk Analyzer", layout="wide")
st.title("⚖️ Contract Risk Analyzer")
st.caption("Upload a contract → detect risks → propose redlines → summarize")

# ----- sidebar -----
with st.sidebar:
    st.header("Options")
    strict_mode = st.toggle("Strict mode (stricter JSON parsing)", value=True)
    jurisdiction = st.selectbox("Jurisdiction", ["General", "US", "EU", "UK", "PK", "AE"])
    top_k_precedents = st.slider("Precedent grounding (k)", 0, 3, 0)
    st.divider()
    st.markdown("**Backend:**")
    st.code(API_URL)

# ----- file upload (persist in session so buttons can reuse) -----
uploaded_file = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf", "docx", "txt"], accept_multiple_files=False)
if uploaded_file:
    st.session_state["last_file_name"] = uploaded_file.name
    st.session_state["last_file_bytes"] = uploaded_file.getvalue()
    st.session_state["last_file_type"] = uploaded_file.type or "application/octet-stream"

# recipient email input
to_email = st.text_input("Recipient email", value=st.session_state.get("email_input", "yourgmail@gmail.com"), key="email_input")

def _current_file_triplet():
    return (
        st.session_state.get("last_file_name"),
        st.session_state.get("last_file_bytes"),
        st.session_state.get("last_file_type", "application/octet-stream"),
    )

def _render_gate_panel(gate_detail: Dict[str, Any]):
    # Pretty message + keep the override button visible
    msg = gate_detail.get("message", "This file doesn’t look like a contract.")
    score = gate_detail.get("score")
    st.error(f"{msg} (score {score})")
    cols = st.columns(2)
    with cols[0]:
        positives = gate_detail.get("positives") or []
        if positives:
            st.info("**Detected contract-like signals:**\n- " + "\n- ".join(positives))
    with cols[1]:
        negatives = gate_detail.get("negatives") or []
        if negatives:
            st.warning("**Detected non-contract signals:**\n- " + "\n- ".join(negatives))

    # Always show override button here
    if st.button("Override and analyze anyway", key="override_btn", use_container_width=True):
        fname, fbytes, ftype = _current_file_triplet()
        if not fbytes:
            st.error("Upload a file first")
            return
        with st.spinner("Forcing analysis..."):
            files = {"file": (fname, fbytes, ftype)}
            params = {
                "strict_mode": str(st.session_state.get("strict_mode_override", strict_mode)).lower(),
                "jurisdiction": jurisdiction,
                "top_k_precedents": int(top_k_precedents),
                "allow_non_contract": "true",
            }
            r2 = requests.post(f"{API_URL}/analyze", params=params, files=files, timeout=120)
            try:
                r2.raise_for_status()
                st.session_state["analysis"] = r2.json()
                st.session_state.pop("gate_detail", None)  # clear the gate notice
                st.rerun()
            except requests.HTTPError:
                st.error(f"Backend error {r2.status_code}: {r2.text[:400]}")
            except Exception as e:
                st.error(f"Override failed: {e}\nRaw: {r2.text[:400]}")

# ----- analyze action -----
if st.button("Analyze", use_container_width=True, type="primary"):
    fname, fbytes, ftype = _current_file_triplet()
    if not fbytes:
        st.error("Please upload a file.")
    else:
        with st.spinner("Analyzing... this can take 10–40s for longer files"):
            files = {"file": (fname, fbytes, ftype)}
            params = {
                "strict_mode": str(strict_mode).lower(),
                "jurisdiction": jurisdiction,
                "top_k_precedents": int(top_k_precedents),
            }
            r = requests.post(f"{API_URL}/analyze", params=params, files=files, timeout=120)
            try:
                r.raise_for_status()
                st.session_state["analysis"] = r.json()
                st.session_state.pop("gate_detail", None)
            except requests.HTTPError:
                # try to parse gate (422) detail
                try:
                    dj = r.json().get("detail")
                except Exception:
                    dj = None
                if isinstance(dj, dict) and "score" in dj:
                    st.session_state["gate_detail"] = dj
                    st.session_state.pop("analysis", None)
                else:
                    st.error(f"Backend error {r.status_code}: {r.text[:400]}")
            except Exception as e:
                st.error(f"API error: {e}\nRaw: {r.text[:400]}")

# ----- show gate panel if set -----
if "gate_detail" in st.session_state:
    _render_gate_panel(st.session_state["gate_detail"])

# ===== render results if present =====
if "analysis" in st.session_state:
    data: Dict[str, Any] = st.session_state["analysis"]

    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Executive Summary")
        st.write(data.get("summary", ""))
    with col2:
        st.subheader("Risk Overview")
        hi, me, lo = data.get("high_risk_count", 0), data.get("medium_risk_count", 0), data.get("low_risk_count", 0)
        st.metric("High", hi)
        st.metric("Medium", me)
        st.metric("Low", lo)

    st.divider()
    st.subheader("Clauses")
    for c in data.get("clauses", []):
        with st.expander(f"{c['id']} • {c['heading']} • {c['category']} • Risk: {c['risk']}"):
            st.markdown("**Original**"); st.write(c.get("text",""))
            st.markdown("**Rationale**"); st.write(c.get("rationale",""))
            if c.get("policy_violations"):
                st.markdown("**Policy Violations**")
                for v in c.get("policy_violations", []):
                    st.write("- ", v)
            if c.get("proposed_text"):
                st.markdown("**Suggested Redline**"); st.write(c["proposed_text"])
                st.markdown("**Why**"); st.write(c.get("explanation",""))
                st.markdown("**Negotiation Note**"); st.write(c.get("negotiation_note",""))

    st.divider()
    st.subheader("Next actions")

    # email action (SendGrid backend)
    fname, fbytes, _ = _current_file_triplet()
    to_email2 = st.text_input("Recipient Email Address", value=st.session_state.get("email_input", ""), key="email_input_next")
    if st.button("Send via Email (SendGrid)"):
        if not fbytes:
            st.error("Upload a file first")
        elif not to_email2 or "@" not in to_email2:
            st.error("Enter a valid recipient email")
        else:
            files = {"file": (fname, fbytes)}
            params = {"to_email": to_email2, "subject": "Revised contract"}
            resp = requests.post(f"{API_URL}/send_email", params=params, files=files, timeout=60)
            if resp.ok:
                status = resp.json().get("provider_status", resp.status_code)
                st.success(f"Email sent (SendGrid status {status})")
            else:
                st.error(f"Email failed: {resp.status_code} {resp.text}")
