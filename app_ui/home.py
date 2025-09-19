# app_ui/home.py
import os
import requests
import streamlit as st
from typing import Dict, Any

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8080")

st.set_page_config(page_title="Contract Risk Analyzer", layout="wide")
st.title("Contract Risk Analyzer")
st.caption("Upload a contract → detect risks → propose redlines → summarize")

# ----- sidebar -----
with st.sidebar:
    st.header("Options")
    strict_mode = st.toggle("Strict mode (stricter JSON parsing)", value=True)
    jurisdiction = st.selectbox("Jurisdiction", ["General", "US", "EU", "UK", "PK", "AE"])
    top_k_precedents = st.slider("Precedent grounding (k)", 0, 3, 0)
    st.divider()
    st.markdown("**Backend**:")
    st.code(API_URL)

# ----- file upload (persist in session so buttons can reuse) -----
uploaded_file = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf", "docx", "txt"], accept_multiple_files=False)
if uploaded_file:
    # persist
    st.session_state["last_file_name"] = uploaded_file.name
    st.session_state["last_file_bytes"] = uploaded_file.getvalue()
    st.session_state["last_file_type"] = uploaded_file.type or "application/octet-stream"

# recipient email input (for SendGrid)
to_email = st.text_input("Recipient email", value=st.session_state.get("email_input", "yourgmail@gmail.com"), key="email_input")

# ----- analyze action: call API and store result in session -----
if st.button("Analyze", use_container_width=True, type="primary"):
    if "last_file_bytes" not in st.session_state:
        st.error("Please upload a file.")
        st.stop()

    with st.spinner("Analyzing... this can take 10–40s for longer files"):
        files = {"file": (st.session_state["last_file_name"], st.session_state["last_file_bytes"], st.session_state["last_file_type"])}
        params = {
            "strict_mode": str(strict_mode).lower(),
            "jurisdiction": jurisdiction,
            "top_k_precedents": int(top_k_precedents),
        }
        try:
            r = requests.post(f"{API_URL}/analyze", params=params, files=files, timeout=600)
            r.raise_for_status()
            st.session_state["analysis"] = r.json()
        except requests.HTTPError as e:
            # 422 contract gate or other HTTP errors
            try:
                dj = r.json().get("detail")
                if isinstance(dj, dict) and "score" in dj:
                    st.error(f"{dj.get('message','Rejected')} (score {dj['score']})")
                    if dj.get("positives"):
                        st.info("**Detected contract-like signals:**\n- " + "\n- ".join(dj["positives"]))
                    if dj.get("negatives"):
                        st.warning("**Detected non-contract signals:**\n- " + "\n- ".join(dj["negatives"]))
                    st.stop()
                else:
                    st.error(dj or str(e))
                    st.stop()
            except Exception:
                st.error(str(e))
                st.stop()
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

# allow override button to force analysis of non-contract
if st.button("Override and analyze anyway"):
    if "last_file_bytes" not in st.session_state:
        st.error("Please upload a file.")
        st.stop()
    with st.spinner("Forcing analysis..."):
        files = {"file": (st.session_state["last_file_name"], st.session_state["last_file_bytes"], st.session_state["last_file_type"])}
        params = {
            "strict_mode": str(strict_mode).lower(),
            "jurisdiction": jurisdiction,
            "top_k_precedents": int(top_k_precedents),
            "allow_non_contract": "true",
        }
        r2 = requests.post(f"{API_URL}/analyze", params=params, files=files, timeout=600)
        try:
            r2.raise_for_status()
            st.session_state["analysis"] = r2.json()
            st.rerun()
        except Exception as e:
            st.error(f"Override failed: {e}")
            st.stop()

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
                for v in c.get("policy_violations", []): st.write("- ", v)
            if c.get("proposed_text"):
                st.markdown("**Suggested Redline**"); st.write(c["proposed_text"])
                st.markdown("**Why**"); st.write(c.get("explanation",""))
                st.markdown("**Negotiation Note**"); st.write(c.get("negotiation_note",""))

    st.markdown("⚠️ Note: This is a research prototype. Do not use for real contracts without human review.")

    # ----- next actions -----
    st.divider()
    st.subheader("Next actions")

    file_name = st.session_state.get("last_file_name")
    file_bytes = st.session_state.get("last_file_bytes")
    file_type = st.session_state.get("last_file_type", "application/octet-stream")

    # Email input and send button
    st.markdown("**Send analyzed contract via Email**")
    to_email = st.text_input("Recipient Email Address", value=st.session_state.get("email_input", ""), key="email_input")

    if st.button("Send Email", key="send_email_btn"):
        if not file_bytes:
            st.error("Upload a file first")
        elif not to_email or "@" not in to_email:
            st.error("Please enter a valid recipient email address.")
        else:
            files = {"file": (file_name, file_bytes)}
            params = {"to_email": to_email, "subject": "Revised contract"}
            try:
                resp = requests.post(f"{API_URL}/send_email", params=params, files=files, timeout=60)
                if resp.ok:
                    status = resp.json().get("provider_status", resp.status_code)
                    st.success(f"Email sent (status {status})")
                else:
                    st.error(f"Email failed: {resp.status_code} {resp.text}")
            except Exception as e:
                st.error(f"Email API error: {e}")

    colA, colB = st.columns(2)

    with colA:
        if st.button("Send via Email (SendGrid)"):
            if not file_bytes:
                st.error("Upload a file first")
            elif not to_email or "@" not in to_email:
                st.error("Enter a valid recipient email")
            else:
                files = {"file": (file_name, file_bytes)}
                params = {"to_email": to_email, "subject": "Revised contract"}
                try:
                    resp = requests.post(f"{API_URL}/send_email", params=params, files=files, timeout=60)
                    if resp.ok:
                        status = resp.json().get("provider_status", resp.status_code)
                        st.success(f"Email sent (SendGrid status {status})")
                    else:
                        st.error(f"Email failed: {resp.status_code} {resp.text}")
                except Exception as e:
                    st.error(f"SendGrid API error: {e}")

    with colB:
        if st.button("Send via DocuSign"):
            if not file_bytes:
                st.error("Upload a file first")
            else:
                files = {"file": (file_name, file_bytes, file_type)}
                params = {"signer_email": to_email or "recipient@example.com", "signer_name": "Recipient"}
                try:
                    r = requests.post(f"{API_URL}/send_for_signature", params=params, files=files, timeout=60)
                    if r.ok:
                        st.success(r.json())
                    else:
                        st.error(f"DocuSign error: {r.status_code} {r.text}")
                except Exception as e:
                    st.error(f"DocuSign API error: {e}")
