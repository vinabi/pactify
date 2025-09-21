# api/main.py
from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.settings import settings
from api.models import AnalyzeRequest, AnalyzeResponse
from agents.tools_parser import read_any
from agents.contract_detector import looks_like_contract_v2
from agents.pipeline import analyze_contract
from agents.tools_email import send_email_sendgrid
from agents.orchestrator import ContractOrchestrator

app = FastAPI(title="Contract Risk Analyzer", version="0.3.0")

# Initialize the orchestrator
orchestrator = ContractOrchestrator()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTS = {".pdf", ".docx", ".txt"}

def _ext_ok(name: str) -> bool:
    n = (name or "").lower()
    return any(n.endswith(ext) for ext in ALLOWED_EXTS)

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
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    if not _ext_ok(file.filename):
        raise HTTPException(status_code=415, detail=f"Unsupported type: {file.filename} (use PDF/DOCX/TXT).")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw)/(1024*1024) > settings.max_file_mb:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_mb}MB")

    try:
        text = read_any(raw, file.filename)
    except ValueError as e:
        msg = str(e)
        if "scanned" in msg.lower():
            raise HTTPException(status_code=400, detail="PDF appears scanned (no extractable text). Upload DOCX/TXT or a text-based PDF.")
        raise HTTPException(status_code=400, detail=f"Could not parse {file.filename}: {msg}")
    except Exception:
        logger.exception("Parser failed")
        raise HTTPException(status_code=400, detail=f"Could not parse {file.filename}. Is it valid?")

    is_contract, details = looks_like_contract_v2(text)
    if not is_contract and not allow_non_contract:
        raise HTTPException(status_code=422, detail={
            "message": "This file doesn't look like a contract.",
            **(details or {}),
            "tip": "Upload a formal contract (NDA, MSA, SOW, etc.). Or set allow_non_contract=true to force analysis.",
        })

    try:
        req = AnalyzeRequest(strict_mode=strict_mode, jurisdiction=jurisdiction, top_k_precedents=top_k_precedents)
        result = analyze_contract(req, raw, file.filename)
        result.clauses = result.clauses[: settings.max_clauses]
        return result
    except Exception:
        logger.exception("Analysis pipeline failed")
        raise HTTPException(status_code=500, detail="Analysis failed. Check server logs.")

@app.post("/send_email")
async def send_email_api(
    to_email: str = Query(...),
    subject: str = Query("Contract risk report"),
    body: Optional[str] = Form(None),
    file: UploadFile = File(None),
):
    file_bytes = None
    fname = None
    if file:
        file_bytes = await file.read()
        fname = file.filename
    try:
        html = body or "<p>Please find attached the revised contract.</p>"
        resp = send_email_sendgrid(
            to_email=to_email, subject=subject, body=html,
            attachment_bytes=file_bytes, attachment_name=fname,
        )
        return {"status": "sent", "provider_status": (resp or {}).get("status_code", 202)}
    except Exception as e:
        logger.exception("Send email failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review_pipeline") 
async def review_pipeline(
    requester_email: str = Query(...),
    jurisdiction: str = Query("General"),
    strict_mode: bool = Query(True),
    file: UploadFile = File(...),
):
    """Complete 5-stage contract review pipeline with email delivery"""
    if not _ext_ok(file.filename):
        raise HTTPException(status_code=400, detail="Invalid file extension")
    
    try:
        file_bytes = await file.read()
        
        # Run the complete pipeline
        result = await orchestrator.process_contract(
            file_bytes=file_bytes,
            filename=file.filename,
            requester_email=requester_email,
            jurisdiction=jurisdiction,
            strict_mode=strict_mode
        )
        
        # Return summary for API response
        return {
            "status": "completed",
            "document_id": result.document_id,
            "filename": result.filename,
            "contract_type": result.contract_type,
            "recommendation": result.recommendation,
            "risk_score": result.risk_score,
            "critical_issues": result.critical_issues[:3],  # Top 3 for API
            "processing_time": result.processing_time_seconds,
            "email_sent": requester_email is not None,
            "next_steps": result.next_steps
        }
        
    except ValueError as ve:
        logger.warning(f"Invalid contract: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail="Pipeline processing failed")

@app.get("/pipeline_stats")
async def get_pipeline_stats():
    """Get processing statistics"""
    return orchestrator.get_stats()

@app.post("/send_for_signature")
async def send_for_signature(signer_email: str, signer_name: str = "Recipient", file: UploadFile = File(...)):
    _ = await file.read()
    return {"status": "sent", "signer": signer_email, "envelopeId": "demo-envelope-123",
            "note": "DocuSign is stubbed due to sandbox/geo restrictions; replace with real SDK when available."}
