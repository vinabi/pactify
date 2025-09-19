# api/main.py
from __future__ import annotations
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.settings import settings
from api.models import AnalyzeRequest, AnalyzeResponse
from agents.tools_parser import read_any  # PDF/DOCX/TXT → text
from agents.contract_detector import looks_like_contract_v2  # heuristic gate
from agents.pipeline import analyze_contract  # your LLM pipeline
from agents.tools_email import send_email_sendgrid  # SendGrid mailer

# ---------- app & CORS ----------
app = FastAPI(title="Contract Risk Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- helpers ----------
ALLOWED_EXTS = {".pdf", ".docx", ".txt"}


def _ext_ok(name: str) -> bool:
    n = (name or "").lower()
    return any(n.endswith(ext) for ext in ALLOWED_EXTS)


# ---------- routes ----------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    strict_mode: bool = Query(True),
    jurisdiction: str = Query("General"),
    top_k_precedents: int = Query(0, ge=0, le=10),
    allow_non_contract: bool = Query(False),
    file: UploadFile = File(...),
):
    """
    Analyze uploaded contract-like file.
    - enforce allowed extensions
    - parse file -> text
    - run heuristic contract detector (explainable)
    - run LLM pipeline
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    if not _ext_ok(file.filename):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.filename}. Allowed: PDF, DOCX, TXT.",
        )

    # read bytes first (size guard) and parse to text
    raw = await file.read()

    if raw is None or len(raw) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    size_mb = len(raw) / (1024 * 1024)
    if size_mb > settings.max_file_mb:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_mb}MB")

    # parse to text
    try:
        text = read_any(raw, file.filename)
    except Exception as e:
        logger.exception("Could not parse file")
        raise HTTPException(status_code=400, detail=f"Could not parse {file.filename}. Is it a valid PDF/DOCX/TXT?")

    # contract heuristic gate (explainable)
    is_contract, details = looks_like_contract_v2(text)
    if not is_contract and not allow_non_contract:
        # return structured reasons the UI can show (score, positives, negatives etc)
        raise HTTPException(
            status_code=422,
            detail={
                "message": "This file doesn't look like a contract.",
                **(details or {}),
                "tip": "Upload a formal contract (NDA, MSA, SOW, etc.). To override, set allow_non_contract=true.",
            },
        )

    # run main pipeline
    try:
        req = AnalyzeRequest(
            strict_mode=strict_mode,
            jurisdiction=jurisdiction,
            top_k_precedents=top_k_precedents,
        )
        result = analyze_contract(req, raw, file.filename)
        # trim clauses just in case
        result.clauses = result.clauses[: settings.max_clauses]
        return result
    except Exception as e:
        logger.exception("Analysis pipeline failed")
        raise HTTPException(status_code=500, detail="Analysis failed. Check server logs.")


@app.post("/send_email")
async def send_email_api(
    to_email: str,
    subject: str = "Revised contract",
    file: UploadFile = File(None),
):
    """
    Send email with optional attachment via SendGrid helper.
    Requires SENDGRID_API_KEY and EMAIL_SENDER in environment (checked by helper).
    """
    file_bytes = None
    fname = None
    if file:
        file_bytes = await file.read()
        fname = file.filename

    try:
        resp = send_email_sendgrid(
            to_email=to_email,
            subject=subject,
            body="<p>Please find attached the revised contract.</p>",
            attachment_bytes=file_bytes,
            attachment_name=fname,
        )
        # helper should return dict with status_code or similar
        return {"status": "sent", "provider_status": resp.get("status_code", 202) if isinstance(resp, dict) else 202}
    except Exception as e:
        logger.exception("Send email failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send_for_signature")
async def send_for_signature(
    signer_email: str,
    signer_name: str = "Recipient",
    file: UploadFile = File(...),
):
    """
    DocuSign demo stub: returns fake envelope. Replace with real SDK if you have sandbox credentials.
    """
    _ = await file.read()  # normally you'd pass the bytes to DocuSign SDK
    # If you have DocuSign sandbox credentials, implement here and return envelope id.
    return {
        "status": "sent",
        "signer": signer_email,
        "envelopeId": "demo-envelope-123",
        "note": "DocuSign is stubbed due to sandbox/geo restrictions; replace with real SDK when available.",
    }
