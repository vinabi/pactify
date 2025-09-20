# home.py
import os
import requests
import streamlit as st
from typing import Dict, Any

# Read the backend URL from Streamlit secrets first, then env, then fallback
API_URL = st.secrets.get("API_URL", os.environ.get("API_URL", "http://127.0.0.1:8080"))

st.set_page_config(page_title="Contract Risk Analyzer", layout="wide", page_icon="⚖️")
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

# ----- file upload (persist for reuse) -----
uploaded = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf", "docx", "txt"], accept_multiple_files=False)
if uploaded:
    st.session_state["last_file_name"] = uploaded.name
    st.session_state["last_file_bytes"] = uploaded.getvalue()
    st.session_state["last_file_type"] = uploaded.type or "application/octet-stream"

# recipient email input
to_email = st.text_input("Recipient email", value=st.session_state.get("email_input", "yourgmail@gmail.com"), key="email_input")

def _current_file():
    return (
        st.session_state.get("last_file_name"),
        st.session_state.get("last_file_bytes"),
        st.session_state.get("last_file_type", "application/octet-stream"),
    )

def _render_gate_panel(detail: Dict[str, Any]):
    msg = detail.get("message", "This file doesn't look like a contract.")
    score = detail.get("score")
    st.error(f"{msg} (score {score})")

    colA, colB = st.columns(2)
    with colA:
        pos = detail.get("positives") or []
        if pos:
            st.info("**Detected contract-like signals:**\n- " + "\n- ".join(pos))
    with colB:
        neg = detail.get("negatives") or []
        if neg:
            st.warning("**Detected non-contract signals:**\n- " + "\n- ".join(neg))

    # Always show override button
    if st.button("Override and analyze anyway", key="override_btn", use_container_width=True):
        fname, fbytes, ftype = _current_file()
        if not fbytes:
            st.error("Upload a file first")
            return
        with st.spinner("Forcing analysis..."):
            files = {"file": (fname, fbytes, ftype)}
            params = {
                "strict_mode": str(strict_mode).lower(),
                "jurisdiction": jurisdiction,
                "top_k_precedents": int(top_k_precedents),
                "allow_non_contract": "true",
            }
            r2 = requests.post(f"{API_URL}/analyze", params=params, files=files, timeout=180)
            try:
                r2.raise_for_status()
                st.session_state["analysis"] = r2.json()
                st.session_state.pop("gate_detail", None)
                st.rerun()
            except requests.HTTPError:
                st.error(f"Backend error {r2.status_code}: {r2.text[:500]}")
            except Exception as e:
                st.error(f"Override failed: {e}\nRaw: {r2.text[:500]}")

# ----- Analyze -----
if st.button("Analyze", use_container_width=True, type="primary"):
    fname, fbytes, ftype = _current_file()
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
            r = requests.post(f"{API_URL}/analyze", params=params, files=files, timeout=180)
            try:
                r.raise_for_status()
                st.session_state["analysis"] = r.json()
                st.session_state.pop("gate_detail", None)
            except requests.HTTPError:
                # Show 422 gate nicely
                try:
                    dj = r.json().get("detail")
                except Exception:
                    dj = None
                if isinstance(dj, dict) and "score" in dj:
                    st.session_state["gate_detail"] = dj
                    st.session_state.pop("analysis", None)
                else:
                    st.error(f"Backend error {r.status_code}: {r.text[:500]}")
            except Exception as e:
                st.error(f"API error: {e}\nRaw: {r.text[:500]}")

# ----- Gate panel if present -----
if "gate_detail" in st.session_state:
    _render_gate_panel(st.session_state["gate_detail"])

# ===== Render results =====
if "analysis" in st.session_state:
    data: Dict[str, Any] = st.session_state["analysis"]

    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Executive Summary")
        st.write(data.get("summary", ""))
    with col2:
        st.subheader("Risk Overview")
        st.metric("High", data.get("high_risk_count", 0))
        st.metric("Medium", data.get("medium_risk_count", 0))
        st.metric("Low", data.get("low_risk_count", 0))

    st.divider()
    st.subheader("Clauses")
    for c in data.get("clauses", []):
        with st.expander(f"{c['id']} • {c['heading']} • {c['category']} • Risk: {c['risk']}"):
            st.markdown("**Original**");         st.write(c.get("text",""))
            st.markdown("**Rationale**");        st.write(c.get("rationale",""))
            if c.get("policy_violations"):
                st.markdown("**Policy Violations**")
                for v in c.get("policy_violations", []): st.write("- ", v)
            if c.get("proposed_text"):
                st.markdown("**Suggested Redline**"); st.write(c["proposed_text"])
                st.markdown("**Why**");               st.write(c.get("explanation",""))
                st.markdown("**Negotiation Note**");  st.write(c.get("negotiation_note",""))

    st.divider()
    st.subheader("Next actions")

    # SendGrid email action
    fname, fbytes, _ = _current_file()
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

    st.caption("Research prototype — human review required before use on real contracts.")
