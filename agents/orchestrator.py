# agents/orchestrator.py - MASTER CONTRACT PIPELINE ORCHESTRATOR
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from loguru import logger
import asyncio
from datetime import datetime

from .tools_parser import read_any
from .tools_email import send_email_sendgrid
from .contract_detector import looks_like_contract_v2, find_red_flags, compare_to_templates
from .pipeline import analyze_contract
from api.models import AnalyzeRequest

# Optional DocuSign import
try:
    from .tools_docusign import send_contract_for_signature
    DOCUSIGN_AVAILABLE = True
except ImportError:
    DOCUSIGN_AVAILABLE = False

@dataclass
class ContractReviewResult:
    """Complete contract review results"""
    # Stage 1: Ingestion
    document_id: str
    filename: str
    extracted_text: str
    confidence_score: float
    
    # Stage 2: Comparison  
    contract_type: str
    template_matches: List[Dict]
    deviations: List[Dict]
    
    # Stage 3: Risk Identification
    red_flags: List[Dict]
    risk_score: int  # 0-100
    critical_issues: List[str]
    
    # Stage 4: Suggestions
    suggested_clauses: List[Dict]
    redlined_version: str
    
    # Stage 5: Summary
    executive_summary: str
    recommendation: str  # "APPROVE", "NEGOTIATE", "REJECT"
    next_steps: List[str]
    
    # Metadata
    created_at: datetime
    processing_time_seconds: float

class ContractOrchestrator:
    """Master orchestrator for the 5-stage contract review pipeline"""
    
    def __init__(self, vector_client=None):
        self.vector_client = vector_client
        self.processing_stats = {"processed": 0, "errors": 0}
    
    async def process_contract(
        self, 
        file_bytes: bytes, 
        filename: str,
        requester_email: Optional[str] = None,
        jurisdiction: str = "General",
        strict_mode: bool = True
    ) -> ContractReviewResult:
        """Execute the complete 5-stage pipeline"""
        start_time = datetime.now()
        doc_id = f"contract_{start_time.strftime('%Y%m%d_%H%M%S')}_{filename}"
        
        try:
            logger.info(f"🚀 Starting contract review pipeline for {filename}")
            
            # STAGE 1: CONTRACT INGESTION
            logger.info("📥 Stage 1: Contract Ingestion")
            text = await self._stage_1_ingestion(file_bytes, filename)
            
            # STAGE 2: CONTRACT COMPARISON
            logger.info("🔍 Stage 2: Contract Comparison") 
            is_contract, detection_details = looks_like_contract_v2(text)
            if not is_contract and strict_mode:
                raise ValueError(f"Document doesn't appear to be a contract (score: {detection_details.get('score', 0)})")
            
            contract_type, template_data = await self._stage_2_comparison(text)
            
            # STAGE 3: RISK IDENTIFICATION  
            logger.info("⚖️ Stage 3: Risk Identification")
            red_flags, risk_score, critical_issues = await self._stage_3_risk_identification(text)
            
            # STAGE 4: CLAUSE SUGGESTIONS
            logger.info("✏️ Stage 4: Clause Suggestions")
            suggestions, redlined_text = await self._stage_4_suggestions(text, red_flags)
            
            # STAGE 5: SUMMARY FOR REVIEW
            logger.info("📋 Stage 5: Summary Generation")
            summary, recommendation, next_steps = await self._stage_5_summary(
                red_flags, risk_score, critical_issues, contract_type
            )
            
            # Build final result
            processing_time = (datetime.now() - start_time).total_seconds()
            result = ContractReviewResult(
                document_id=doc_id,
                filename=filename,
                extracted_text=text[:1000] + "..." if len(text) > 1000 else text,
                confidence_score=detection_details.get('score', 0) / 100.0,
                contract_type=contract_type,
                template_matches=template_data.get('template_matches', []),
                deviations=template_data.get('deviations', []),
                red_flags=red_flags,
                risk_score=risk_score,
                critical_issues=critical_issues,
                suggested_clauses=suggestions,
                redlined_version=redlined_text,
                executive_summary=summary,
                recommendation=recommendation,
                next_steps=next_steps,
                created_at=start_time,
                processing_time_seconds=processing_time
            )
            
            # Send email if requested
            if requester_email:
                await self._send_review_email(result, requester_email, file_bytes)
            
            self.processing_stats["processed"] += 1
            logger.info(f"✅ Pipeline completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.processing_stats["errors"] += 1
            logger.error(f"❌ Pipeline failed: {e}")
            raise
    
    async def _stage_1_ingestion(self, file_bytes: bytes, filename: str) -> str:
        """Stage 1: Extract and normalize text from any format"""
        try:
            text = read_any(file_bytes, filename)
            if not text or len(text.strip()) < 50:
                raise ValueError("Document appears to be empty or corrupted")
            logger.info(f"📄 Extracted {len(text)} characters from {filename}")
            return text
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise ValueError(f"Could not process {filename}: {e}")
    
    async def _stage_2_comparison(self, text: str) -> Tuple[str, Dict]:
        """Stage 2: Compare against standard templates"""
        try:
            comparison_data = compare_to_templates(text, self.vector_client)
            contract_type = comparison_data.get('identified_type', 'Unknown')
            logger.info(f"🔍 Identified as: {contract_type}")
            return contract_type, comparison_data
        except Exception as e:
            logger.warning(f"Template comparison failed: {e}")
            return "Unknown", {"template_matches": [], "deviations": []}
    
    async def _stage_3_risk_identification(self, text: str) -> Tuple[List[Dict], int, List[str]]:
        """Stage 3: Identify risks and red flags"""
        try:
            red_flags = find_red_flags(text)
            
            # Calculate risk score (0-100)
            high_risks = [rf for rf in red_flags if rf.get('severity') == 'high']
            medium_risks = [rf for rf in red_flags if rf.get('severity') == 'medium'] 
            low_risks = [rf for rf in red_flags if rf.get('severity') == 'low']
            
            risk_score = min(100, len(high_risks) * 30 + len(medium_risks) * 15 + len(low_risks) * 5)
            
            # Extract critical issues
            critical_issues = [rf['label'] for rf in high_risks[:5]]  # Top 5 critical
            
            logger.info(f"⚖️ Risk Score: {risk_score}/100, Critical Issues: {len(critical_issues)}")
            return red_flags, risk_score, critical_issues
            
        except Exception as e:
            logger.warning(f"Risk identification failed: {e}")
            return [], 0, []
    
    async def _stage_4_suggestions(self, text: str, red_flags: List[Dict]) -> Tuple[List[Dict], str]:
        """Stage 4: Generate clause suggestions and redlined version"""
        try:
            suggestions = []
            redlined_sections = []
            
            # For now, create basic suggestions based on red flags
            for rf in red_flags[:10]:  # Top 10 issues
                if rf.get('severity') == 'high':
                    suggestion = {
                        'issue': rf['label'],
                        'current_risk': rf['description'],
                        'suggested_action': f"Review and revise {rf['category']} clause",
                        'priority': 'high'
                    }
                    suggestions.append(suggestion)
                    redlined_sections.append(f"🔴 HIGH RISK: {rf['label']} - {rf['description']}")
            
            redlined_text = "REDLINED VERSION:\n\n" + "\n".join(redlined_sections)
            
            logger.info(f"✏️ Generated {len(suggestions)} suggestions")
            return suggestions, redlined_text
            
        except Exception as e:
            logger.warning(f"Suggestion generation failed: {e}")
            return [], "Redlining failed - manual review required"
    
    async def _stage_5_summary(
        self, 
        red_flags: List[Dict], 
        risk_score: int, 
        critical_issues: List[str],
        contract_type: str
    ) -> Tuple[str, str, List[str]]:
        """Stage 5: Generate executive summary and recommendations"""
        try:
            # Determine recommendation
            if risk_score >= 70:
                recommendation = "REJECT"
            elif risk_score >= 40:
                recommendation = "NEGOTIATE"
            else:
                recommendation = "APPROVE"
            
            # Generate summary
            summary = f"""
EXECUTIVE SUMMARY - {contract_type}

RISK ASSESSMENT: {risk_score}/100 ({recommendation})

KEY FINDINGS:
• {len([rf for rf in red_flags if rf.get('severity') == 'high'])} High Risk Issues
• {len([rf for rf in red_flags if rf.get('severity') == 'medium'])} Medium Risk Issues  
• {len([rf for rf in red_flags if rf.get('severity') == 'low'])} Low Risk Issues

CRITICAL CONCERNS:
{chr(10).join(f'• {issue}' for issue in critical_issues[:5]) if critical_issues else '• None identified'}

RECOMMENDATION: {recommendation}
"""
            
            # Next steps based on recommendation
            if recommendation == "REJECT":
                next_steps = [
                    "Do not sign - risks too high",
                    "Request major revisions",
                    "Consider walking away if terms can't be improved"
                ]
            elif recommendation == "NEGOTIATE": 
                next_steps = [
                    "Negotiate high-risk clauses",
                    "Request liability caps and mutual terms",
                    "Obtain legal review before signing"
                ]
            else:
                next_steps = [
                    "Final legal review recommended",
                    "Address minor issues if possible",
                    "Proceed with signing"
                ]
            
            logger.info(f"📋 Summary: {recommendation} with {len(next_steps)} action items")
            return summary.strip(), recommendation, next_steps
            
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return "Summary generation failed", "MANUAL_REVIEW", ["Requires human analysis"]
    
    async def _send_review_email(
        self, 
        result: ContractReviewResult, 
        recipient_email: str,
        original_file: bytes
    ):
        """Send comprehensive review email with recommendations"""
        try:
            # Build HTML email content
            risk_color = {"APPROVE": "green", "NEGOTIATE": "orange", "REJECT": "red"}[result.recommendation]
            
            html_body = f"""
<h2>Contract Review Complete: {result.filename}</h2>

<div style="padding: 15px; background-color: {risk_color}; color: white; border-radius: 5px;">
    <h3>RECOMMENDATION: {result.recommendation}</h3>
    <p>Risk Score: {result.risk_score}/100</p>
</div>

<h3>Executive Summary</h3>
<pre>{result.executive_summary}</pre>

<h3>Critical Issues ({len(result.critical_issues)})</h3>
<ul>
{''.join(f'<li style="color: red;"><b>{issue}</b></li>' for issue in result.critical_issues[:5])}
</ul>

<h3>Next Steps</h3>
<ol>
{''.join(f'<li>{step}</li>' for step in result.next_steps)}
</ol>

<h3>Contract Details</h3>
<ul>
<li><b>Type:</b> {result.contract_type}</li>
<li><b>Processing Time:</b> {result.processing_time_seconds:.2f}s</li>
<li><b>High Risk Issues:</b> {len([rf for rf in result.red_flags if rf.get('severity') == 'high'])}</li>
<li><b>Template Matches:</b> {len(result.template_matches)}</li>
</ul>

<p><i>Generated by Pactify Contract Risk Analyzer</i></p>
"""
            
            subject = f"Contract Review: {result.recommendation} - {result.filename}"
            
            # Send email with original file attached
            send_email_sendgrid(
                to_email=recipient_email,
                subject=subject,
                body=html_body,
                attachment_bytes=original_file,
                attachment_name=result.filename
            )
            
            logger.info(f"📧 Review email sent to {recipient_email}")
            
        except Exception as e:
            logger.error(f"Failed to send review email: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "processed_contracts": self.processing_stats["processed"],
            "failed_contracts": self.processing_stats["errors"],
            "success_rate": self.processing_stats["processed"] / max(1, self.processing_stats["processed"] + self.processing_stats["errors"])
        }
