# api/main.py
from __future__ import annotations
import json
import os
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.contract_detector import looks_like_contract_v2  # uses your uploaded module

# ---- CORS / app ----
app = FastAPI(title="Contract Risk Analyzer", version="0.2.0")

def _load_cors():
    raw = os.getenv("CORS_ALLOW_ORIGINS", '["*"]')
    try:
        vals = json.loads(raw)
        if not isinstance(vals, list): raise ValueError
        return vals
    except Exception:
        return ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs", "health": "/healthz"}

@app.get("/healthz")
def health():
    return {"status": "ok"}

# ---- Request/Response models ----
class Clause(BaseModel):
    id: str
    heading: str
    text: str
    category: str
    risk: str
    rationale: str
    policy_violations: list[str] = []
    proposed_text: Optional[str] = None
    explanation: Optional[str] = None
    negotiation_note: Optional[str] = None

class AnalyzeResponse(BaseModel):
    summary: str
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    clauses: list[Clause]

# You likely already have your pipeline wired; import here.
# from agents.pipeline import analyze_contract
# For demo resilience, here’s a tiny mock you can remove once your real pipeline is imported:

def _mock_analyze(text: str) -> AnalyzeResponse:
    sample = Clause(
        id="C001",
        heading="Confidentiality",
        text=text[:800],
        category="Confidentiality",
        risk="Low",
        rationale="No clear conflicts found; generic clause.",
        policy_violations=[],
        proposed_text=None,
        explanation=None,
        negotiation_note="Consider adding explicit data handling timelines."
    )
    return AnalyzeResponse(
        summary="Overall risk looks low for this small sample.",
        high_risk_count=0, medium_risk_count=0, low_risk_count=1,
        clauses=[sample],
    )

# ---- Helpers ----
async def _read_bytes(f: UploadFile) -> bytes:
    b = await f.read()
    if not b:
        raise HTTPException(status_code=400, detail="Empty file.")
    max_mb = float(os.getenv("MAX_FILE_MB", "10"))
    if len(b) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large (> {max_mb} MB).")
    return b

def _to_text(raw: bytes, filename: str) -> str:
    # naive fallback; your real parser likely handles PDF/DOCX/TXT
    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""

# ---- Analyze endpoint ----
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    strict_mode: bool = Query(True),
    jurisdiction: str = Query("General"),
    top_k_precedents: int = Query(0, ge=0, le=5),
    allow_non_contract: bool = Query(False),
):
    raw = await _read_bytes(file)
    text = _to_text(raw, file.filename or "uploaded.txt")

    # Gate: detect if it looks like a contract (heuristic)
    is_contract, details = looks_like_contract_v2(text)
    if not is_contract and not allow_non_contract:
        # 422 with rich detail; UI renders an override panel
        raise HTTPException(
            status_code=422,
            detail={
                "message": "This file doesn't look like a contract.",
                **details,
            },
        )

    # Run your real pipeline here:
    try:
        # result = analyze_contract(req, raw, file.filename)  # your implementation
        result = _mock_analyze(text)  # replace with your pipeline return
        return result
    except HTTPException:
        raise
    except Exception as e:
        # Surface a helpful error to the UI (no HTML)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

# ---- Send email endpoint (optional) ----
from fastapi import Form
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, Disposition, FileContent, FileName

@app.post("/send_email")
async def send_email(
    to_email: str = Query(...),
    subject: str = Query("Revised contract"),
    file: UploadFile = File(None),
):
    api_key = os.getenv("SENDGRID_API_KEY")
    sender = os.getenv("EMAIL_SENDER")
    if not api_key or not sender:
        raise HTTPException(status_code=400, detail="Email not configured on the server.")

    content = f"Contract analysis attached.\n\n– Pactify"
    message = Mail(from_email=sender, to_emails=to_email, subject=subject, plain_text_content=content)

    if file is not None:
        raw = await file.read()
        if raw:
            import base64
            att = Attachment()
            att.file_content = FileContent(base64.b64encode(raw).decode("utf-8"))
            att.file_name = FileName(file.filename or "contract.txt")
            att.disposition = Disposition("attachment")
            message.attachment = att

    try:
        sg = SendGridAPIClient(api_key)
        resp = sg.send(message)
        return {"ok": True, "provider_status": resp.status_code}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SendGrid error: {e}")
