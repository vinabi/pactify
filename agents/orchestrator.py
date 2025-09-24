# agents/orchestrator.py - MASTER CONTRACT PIPELINE ORCHESTRATOR (with early gate)
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import asyncio
from datetime import datetime

from .tools_parser import read_any
from .tools_email import send_email_sendgrid
from .contract_detector import classify_document, find_red_flags, compare_to_templates
from .pipeline import analyze_contract
from api.models import AnalyzeRequest

# Optional DocuSign
try:
    from .tools_docusign import send_contract_for_signature  # noqa
    DOCUSIGN_AVAILABLE = True
except Exception:
    DOCUSIGN_AVAILABLE = False

@dataclass
class ContractReviewResult:
    document_id: str
    filename: str
    extracted_text: str
    confidence_score: float
    contract_type: str
    template_matches: List[Dict]
    deviations: List[Dict]
    red_flags: List[Dict]
    risk_score: int
    critical_issues: List[str]
    suggested_clauses: List[Dict]
    redlined_version: str
    executive_summary: str
    recommendation: str
    next_steps: List[str]
    created_at: datetime
    processing_time_seconds: float

class ContractOrchestrator:
    def __init__(self, vector_client=None):
        self.vector_client = vector_client
        self.processing_stats = {"processed": 0, "errors": 0}

    async def process_contract(
        self,
        file_bytes: bytes,
        filename: str,
        requester_email: Optional[str] = None,
        jurisdiction: str = "General",
        strict_mode: bool = True,
    ) -> ContractReviewResult:
        start_time = datetime.now()
        doc_id = f"contract_{start_time.strftime('%Y%m%d_%H%M%S')}_{filename}"

        try:
            logger.info(f"🚀 Starting pipeline for {filename}")

            # Stage 1 — Ingestion
            text = await self._stage_1_ingestion(file_bytes, filename)

            # Stage 1.5 — **GATE** (accept: contract or legal_document; reject: non_legal)
            gate = classify_document(text)
            if not gate.accept:
                raise ValueError(f"Rejected: {gate.reason}")
            logger.info(f"🛂 Gate accepted as {gate.label} ({gate.confidence})")

            # Stage 2 — Comparison / type
            contract_type, template_data = await self._stage_2_comparison(text)

            # Stage 3 — Risks
            red_flags, risk_score, critical_issues = await self._stage_3_risk_identification(text)

            # Stage 4 — Suggestions (light)
            suggestions, redlined_text = await self._stage_4_suggestions(text, red_flags)

            # Stage 5 — Summary
            summary, recommendation, next_steps = await self._stage_5_summary(
                red_flags, risk_score, critical_issues, contract_type
            )

            processing_time = (datetime.now() - start_time).total_seconds()
            result = ContractReviewResult(
                document_id=doc_id,
                filename=filename,
                extracted_text=text[:1000] + "..." if len(text) > 1000 else text,
                confidence_score=max(0.0, min(1.0, (gate.details.get("score", 0) / 100.0))),
                contract_type=contract_type,
                template_matches=template_data.get("template_matches", []),
                deviations=template_data.get("deviations", []),
                red_flags=red_flags,
                risk_score=risk_score,
                critical_issues=critical_issues,
                suggested_clauses=suggestions,
                redlined_version=redlined_text,
                executive_summary=summary,
                recommendation=recommendation,
                next_steps=next_steps,
                created_at=start_time,
                processing_time_seconds=processing_time,
            )

            if requester_email:
                await self._send_review_email(result, requester_email, file_bytes)

            self.processing_stats["processed"] += 1
            logger.info(f"Pipeline completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            self.processing_stats["errors"] += 1
            logger.error(f"Pipeline failed: {e}")
            raise

    async def _stage_1_ingestion(self, file_bytes: bytes, filename: str) -> str:
        try:
            text = read_any(file_bytes, filename)
            if not text or len(text.strip()) < 50:
                raise ValueError("Document appears to be empty or corrupted")
            return text
        except Exception as e:
            raise ValueError(f"Could not process {filename}: {e}")

    async def _stage_2_comparison(self, text: str) -> Tuple[str, Dict]:
        try:
            comparison = compare_to_templates(text, self.vector_client)
            ctype = comparison.get("identified_type", "Unknown")
            return ctype, comparison
        except Exception:
            return "Unknown", {"template_matches": [], "deviations": []}

    async def _stage_3_risk_identification(self, text: str) -> Tuple[List[Dict], int, List[str]]:
        try:
            red_flags = find_red_flags(text)
            high = [rf for rf in red_flags if rf.get("severity") == "high"]
            med  = [rf for rf in red_flags if rf.get("severity") == "medium"]
            low  = [rf for rf in red_flags if rf.get("severity") == "low"]
            risk_score = min(100, len(high) * 30 + len(med) * 15 + len(low) * 5)
            critical = [rf["label"] for rf in high[:5]]
            return red_flags, risk_score, critical
        except Exception:
            return [], 0, []

    async def _stage_4_suggestions(self, text: str, red_flags: List[Dict]) -> Tuple[List[Dict], str]:
        suggestions, redlined = [], []
        for rf in red_flags[:10]:
            if rf.get("severity") == "high":
                suggestions.append({
                    "issue": rf["label"],
                    "current_risk": rf.get("description", ""),
                    "suggested_action": f"Review and revise {rf.get('category','clause')} clause",
                    "priority": "high",
                })
                redlined.append(f"HIGH RISK: {rf['label']} - {rf.get('description','')}")
        return suggestions, ("REDLINED VERSION:\n\n" + "\n".join(redlined) if redlined else "No redlines generated")

    async def _stage_5_summary(self, red_flags: List[Dict], risk_score: int, critical_issues: List[str], contract_type: str) -> Tuple[str, str, List[str]]:
        if risk_score >= 70:
            recommendation = "REJECT"
        elif risk_score >= 40:
            recommendation = "NEGOTIATE"
        else:
            recommendation = "APPROVE"
        summary = f"""EXECUTIVE SUMMARY - {contract_type}

RISK ASSESSMENT: {risk_score}/100 ({recommendation})

KEY FINDINGS:
• {len([rf for rf in red_flags if rf.get('severity') == 'high'])} High Risk Issues
• {len([rf for rf in red_flags if rf.get('severity') == 'medium'])} Medium Risk Issues  
• {len([rf for rf in red_flags if rf.get('severity') == 'low'])} Low Risk Issues

CRITICAL CONCERNS:
{chr(10).join('• ' + c for c in (critical_issues[:5] or ['None identified']))}

RECOMMENDATION: {recommendation}
""".strip()
        if recommendation == "REJECT":
            next_steps = ["Do not sign - risks too high", "Request major revisions", "Consider walking away if terms can't be improved"]
        elif recommendation == "NEGOTIATE":
            next_steps = ["Negotiate high-risk clauses", "Request liability caps and mutual terms", "Obtain legal review before signing"]
        else:
            next_steps = ["Final legal review recommended", "Address minor issues if possible", "Proceed with signing"]
        return summary, recommendation, next_steps

    async def _send_review_email(self, result: ContractReviewResult, recipient_email: str, original_file: bytes):
        try:
            color = {"APPROVE": "green", "NEGOTIATE": "orange", "REJECT": "red"}[result.recommendation]
            html = f"""
<h2>Contract Review Complete: {result.filename}</h2>
<div style="padding: 15px; background-color: {color}; color: white; border-radius: 5px;">
  <h3>RECOMMENDATION: {result.recommendation}</h3>
  <p>Risk Score: {result.risk_score}/100</p>
</div>
<h3>Executive Summary</h3>
<pre>{result.executive_summary}</pre>
<h3>Critical Issues ({len(result.critical_issues)})</h3>
<ul>{''.join(f'<li style="color:red"><b>{i}</b></li>' for i in result.critical_issues[:5])}</ul>
<h3>Next Steps</h3>
<ol>{''.join(f'<li>{s}</li>' for s in result.next_steps)}</ol>
<p><i>Generated by Pactify Contract Risk Analyzer</i></p>
"""
            send_email_sendgrid(to_email=recipient_email, subject=f"Contract Review: {result.recommendation} - {result.filename}",
                                body=html, attachment_bytes=original_file, attachment_name=result.filename)
        except Exception as e:
            logger.error(f"Failed to send review email: {e}")

    def get_stats(self) -> Dict[str, Any]:
        processed = self.processing_stats["processed"]
        errors = self.processing_stats["errors"]
        return {
            "processed_contracts": processed,
            "failed_contracts": errors,
            "success_rate": processed / max(1, processed + errors),
        }
