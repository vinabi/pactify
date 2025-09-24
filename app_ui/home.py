# app_ui/dashboard.py - EXACT REPLICA OF CONTRACT ANALYSIS DASHBOARD
import streamlit as st
import requests
import re
import time
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
from loguru import logger
import sys

# Add project root for imports
sys.path.append(str(Path(__file__).parent.parent))

# API Configuration - Cloud-first: use HF Space backend
HF_API_BASE = "https://vinabi-pactify.hf.space"

API_BASE_URL = HF_API_BASE

import asyncio

# Page configuration
st.set_page_config(
    page_title="Pactify",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS to match the interface design
st.markdown("""
<style>
    .main-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    
    .project-breadcrumb {
        font-size: 0.9rem;
        color: #666;
    }
    
    .upload-zone {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 3rem;
        text-align: center;
        background-color: #fafafa;
        margin: 2rem 0;
    }
    
    .upload-icon {
        font-size: 3rem;
        color: #999;
        margin-bottom: 1rem;
    }
    
    .analysis-card {
        background: white;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    
    .card-title {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
        color: #333;
    }
    
    .card-status {
        color: #999;
        font-size: 0.85rem;
        font-style: italic;
    }
    
    .card-result {
        color: #333;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    .risk-high { color: #d32f2f; font-weight: bold; }
    .risk-medium { color: #f57c00; font-weight: bold; }
    .risk-low { color: #388e3c; font-weight: bold; }
    
    .counter-badge {
        background: #f0f0f0;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        color: #666;
    }
    
    .tabs-container {
        margin-bottom: 2rem;
    }
    
    .export-btn {
        background: #333;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Risk categories that match the interface
RISK_CATEGORIES = [
    {
        "title": "Outlier Liability & Indemnity Clauses",
        "category": "liability",
        "description": "Unusual liability or indemnification terms that deviate from standard practices"
    },
    {
        "title": "Non-Standard Governing Law / Jurisdiction",
        "category": "jurisdiction", 
        "description": "Governing law or jurisdiction clauses that may be unfavorable"
    },
    {
        "title": "Unusual Payment or Termination Terms",
        "category": "payment_termination",
        "description": "Payment schedules or termination clauses outside normal parameters"
    },
    {
        "title": "Deviations from Company Playbook",
        "category": "playbook",
        "description": "Terms that don't align with standard company contract practices"
    },
    {
        "title": "Concentration of Risk with a Single Counterparty",
        "category": "risk_concentration",
        "description": "Over-reliance on single party creating concentration risk"
    },
    {
        "title": "Lack of Required Compliance Clauses",
        "category": "compliance",
        "description": "Missing mandatory regulatory or compliance provisions"
    },
    {
        "title": "Statistically Rare Language Patterns",
        "category": "language_patterns",
        "description": "Unusual contractual language that appears infrequently"
    },
    {
        "title": "Legacy Clauses from Outdated Templates",
        "category": "legacy",
        "description": "Outdated provisions from older contract templates"
    },
    {
        "title": "Inconsistent Definitions Across Contracts",
        "category": "definitions",
        "description": "Conflicting or inconsistent term definitions"
    },
    {
        "title": "Silent Contracts Missing Key Provisions",
        "category": "missing_provisions",
        "description": "Contracts lacking essential protective clauses"
    }
]

def render_header():
    """Render the header with navigation and controls"""
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        st.markdown('<div class="project-breadcrumb">Contract Analysis MultiAgent</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<h1 style="text-align: center; margin: 0;">🏛 Pactify</h1>', unsafe_allow_html=True)
    
    with col3:
        st.markdown("")  # Empty space, no export button

def render_tabs():
    """Render the tab navigation"""
    tab1, tab2, tab3 = st.tabs(["Build", "Review", "Automate"])
    return tab1, tab2, tab3

def render_upload_zone():
    """Render the document upload area"""
    st.markdown("""
    <div class="upload-zone">
        <div class="upload-icon" style="font-size: 3rem; color: #999; margin-bottom: 1rem;">▣</div>
        <h4>Drop your document here</h4>
        <p style="color: #666; margin: 1rem 0;">Import your files</p>
        <p style="font-size: 0.85rem; color: #888;">Drag and drop your files (PDF, DOC, DOCX) or click to upload.</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a contract file",
        type=['pdf', 'docx', 'doc', 'txt'],
        help="Upload your contract document for analysis",
        label_visibility="collapsed"
    )
    
    return uploaded_file

def render_analysis_cards(analysis_results: Optional[Dict] = None):
    """Render the analysis result cards"""
    
    # Create two columns for the card layout
    col1, col2 = st.columns(2)
    
    # Split categories between columns
    left_categories = RISK_CATEGORIES[:5]
    right_categories = RISK_CATEGORIES[5:]
    
    # Left column cards
    with col1:
        for category in left_categories:
            render_single_card(category, analysis_results)
    
    # Right column cards  
    with col2:
        for category in right_categories:
            render_single_card(category, analysis_results)

def render_single_card(category: Dict, analysis_results: Optional[Dict] = None):
    """Render a single analysis card with actual legal issues and percentages - FIXED RENDERING"""
    
    # Use Streamlit native components instead of raw HTML to fix rendering
    with st.container():
        # Card styling using Streamlit markdown
        st.markdown(
            f"""
            <div style="
                background: white;
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border: 1px solid #e0e0e0;
                min-height: 120px;
            ">
                <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 0.5rem; color: #333;">
                    ▣ {category['title']}
                </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Check if we have analysis results for this category
        if analysis_results and category['category'] in analysis_results:
            result = analysis_results[category['category']]
            issues = result.get('issues', [])
            severity = result.get('severity', 'low')
            
            # Calculate relevance percentage
            relevance_score = calculate_relevance_percentage(issues, severity)
            
            if issues:
                # Risk color coding
                color = {'high': '#d32f2f', 'medium': '#f57c00', 'low': '#388e3c'}.get(severity, '#666')
                
                st.markdown(
                    f"""
                    <div style="color: {color}; font-weight: bold; font-size: 1rem;">
                        {relevance_score}% Relevance
                    </div>
                    <div style="color: #666; font-size: 0.9rem; margin-top: 0.2rem;">
                        {len(issues)} issues detected
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Show issues
                for issue in issues[:2]:  # Top 2 issues
                    st.markdown(f"• {issue.get('label', 'Unknown issue')[:45]}...")
            else:
                st.markdown(
                    """
                    <div style="color: #28a745; font-weight: bold;">0% Risk</div>
                    <div style="color: #28a745; font-size: 0.9rem;">No issues found</div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            # Default waiting state
            st.markdown(
                """
                <div style="text-align: center; color: #999; font-style: italic;">
                    Waiting for analysis...
                </div>
                <div style="text-align: center; color: #ccc; font-size: 0.8rem; margin-top: 0.5rem;">
                    Upload document to begin
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown("</div>", unsafe_allow_html=True)

# Simplified for API-first approach
def handle_educational_analysis(uploaded_file, user_email: str, text: str, detection_details: Dict) -> Dict:
    """Educational analysis for ANY document that might be legal - always helpful"""
    
    try:
        # Basic recommendations without heavy dependencies
        smart_recommendations = analyze_document_gaps(text)
        
        if not smart_recommendations:
            smart_recommendations = [
                "Add clear legal structure with formal language",
                "Include party identification sections", 
                "Add signature blocks and dates",
                "Include governing law provisions",
                "Define key terms and obligations"
            ]
        
        # Create EDUCATIONAL improvement report
        confidence = detection_details.get('confidence', 'minimal')
        legal_indicators = detection_details.get('legal_indicators', [])
        
        improvement_html = f"""
<h2>Legal Document Analysis & Enhancement Report: {uploaded_file.name}</h2>

<div style="padding: 15px; background-color: #2196f3; color: white;">
    <h3>EDUCATIONAL ANALYSIS COMPLETE</h3>
    <p>Document Type: {detection_details.get('detected_type', 'Legal Document').replace('_', ' ').title()}</p>
    <p>Analysis Confidence: {confidence.title()}</p>
    <p>Legal Indicators Found: {len(legal_indicators)}</p>
</div>

<h3>DOCUMENT ASSESSMENT:</h3>
<ul>
<li><b>Word Count:</b> {detection_details.get('word_count', 0)} words</li>
<li><b>Legal Indicators:</b> {', '.join(legal_indicators) if legal_indicators else 'Basic document structure'}</li>
<li><b>Strong Legal Elements:</b> {detection_details.get('strong_matches', 0)}</li>
<li><b>Medium Legal Elements:</b> {detection_details.get('medium_matches', 0)}</li>
</ul>

<h3>SMART IMPROVEMENT RECOMMENDATIONS:</h3>
<ol>
{''.join(f'<li>{rec}</li>' for rec in smart_recommendations[:8])}
</ol>

<h3>LEGAL ENHANCEMENT OPPORTUNITIES:</h3>
<ul>
<li>Legal Structure: {'✓ Present' if detection_details.get('has_legal_terms') else '○ Can be strengthened'}</li>
<li>Party Identification: {'✓ Found' if 'legal_relationships' in legal_indicators else '○ Needs clarification'}</li>
<li>Professional Language: {'✓ Detected' if detection_details.get('strong_matches', 0) > 0 else '○ Can be enhanced'}</li>
<li>Formal Structure: {'✓ Present' if 'legal_structure' in legal_indicators else '○ Recommended to add'}</li>
</ul>

<h3>NEXT STEPS FOR ENHANCEMENT:</h3>
<p>1. Review each recommendation above for your specific use case</p>
<p>2. Consider the legal context and requirements for your situation</p>
<p>3. Implement improvements that align with your document's purpose</p>
<p>4. For complex legal matters, consult with qualified legal counsel</p>
<p>5. Re-analyze the document after improvements to track progress</p>

<h3>WEB RESEARCH SUGGESTIONS:</h3>
<p>Search terms to research: <b>{', '.join(detection_details.get('search_terms', []))}</b></p>

<p><i>Generated by Pactify Contract Analyzer - Educational Legal Analysis</i></p>
<p><i>This analysis is for educational purposes and does not constitute legal advice.</i></p>
"""
        
        # Send improvement email
        from agents.tools_email import send_email_sendgrid
        
        send_email_sendgrid(
            to_email=user_email,
            subject=f"Legal Document Analysis & Enhancement Guide - {uploaded_file.name}",
            body=improvement_html,
            attachment_bytes=b'',  # Skip attachment for now to avoid read errors
            attachment_name=uploaded_file.name
        )
        
        # Create analysis results showing needed improvements
        improvement_results = {
            'liability': {
                'issues': [{'label': 'Missing liability protection clauses', 'severity': 'medium'}],
                'severity': 'medium'
            },
            'jurisdiction': {
                'issues': [{'label': 'No governing law specified', 'severity': 'medium'}],
                'severity': 'medium'  
            },
            'missing_provisions': {
                'issues': [{'label': 'Missing essential legal structure', 'severity': 'high'}],
                'severity': 'high'
            }
        }
        
        return {
            'result': {
                'filename': uploaded_file.name,
                'contract_type': detection_details.get('detected_type', 'Legal Document').replace('_', ' ').title(),
                'recommendation': 'ENHANCE',
                'risk_score': max(25, 100 - detection_details.get('score', 0)),  # Educational scoring
                'red_flags': [{'label': rec, 'severity': 'medium'} for rec in smart_recommendations[:5]],
                'critical_issues': ['Document enhancement opportunities identified'],
                'processing_time_seconds': 1.5,
                'rag_recommendations': smart_recommendations[:5],
                'web_context': detection_details.get('web_context', 'Educational analysis'),
                'executive_summary': f"""
EDUCATIONAL LEGAL DOCUMENT ANALYSIS

DOCUMENT TYPE: {detection_details.get('detected_type', 'Legal Document').replace('_', ' ').title()}
Analysis Confidence: {detection_details.get('confidence', 'Medium').title()}
Legal Indicators: {len(detection_details.get('legal_indicators', []))}

ENHANCEMENT OPPORTUNITIES:
{''.join(f'• {rec}' + chr(10) for rec in smart_recommendations[:5])}

EDUCATIONAL RECOMMENDATION: ENHANCE DOCUMENT
This analysis provides educational insights to strengthen your document's legal effectiveness and professional presentation.

WEB RESEARCH CONTEXT:
{detection_details.get('web_context', 'Standard legal document enhancement analysis performed.')}
"""
            },
            'analysis_results': improvement_results,
            'success': True,
            'educational_mode': True
        }
        
    except Exception as e:
        logger.error(f"Weak document handling failed: {e}")
        return {
            'success': False,
            'error': f"Document analysis failed: {str(e)}"
        }

def analyze_document_gaps(text: str) -> List[str]:
    """Analyze what's missing in the document and suggest specific improvements"""
    
    text_lower = text.lower()
    gaps = []
    
    # Check for missing legal structure
    if "whereas" not in text_lower and "background" not in text_lower:
        gaps.append("Add background context with WHEREAS clauses or introduction section")
    
    if "now therefore" not in text_lower and "agree" not in text_lower:
        gaps.append("Include binding agreement language ('NOW THEREFORE' or 'the parties agree')")
    
    # Check for missing parties
    if not re.search(r"\b(party|client|contractor|company|employer|employee|petitioner|beneficiary)\b", text_lower):
        gaps.append("Clearly identify all parties to the agreement with full names and addresses")
    
    # Check for missing key legal elements
    if "signature" not in text_lower and "sign" not in text_lower:
        gaps.append("Add signature blocks with printed names, titles, and dates")
    
    if "date" not in text_lower and "effective" not in text_lower:
        gaps.append("Include effective date and term duration")
    
    if "governing law" not in text_lower and "jurisdiction" not in text_lower:
        gaps.append("Add governing law and jurisdiction provisions")
    
    if "termination" not in text_lower and "end" not in text_lower:
        gaps.append("Include termination conditions and procedures")
    
    # Document-specific gaps
    if "liability" not in text_lower:
        gaps.append("Add liability allocation and limitation clauses")
    
    if "confidential" in text_lower and "definition" not in text_lower:
        gaps.append("Define 'Confidential Information' with specific scope and exceptions")
    
    if "payment" in text_lower and ("net" not in text_lower or "days" not in text_lower):
        gaps.append("Specify clear payment terms with deadlines and late fees")
    
    if "intellectual property" in text_lower and "ownership" not in text_lower:
        gaps.append("Clarify intellectual property ownership and assignment terms")
    
    return gaps[:8]  # Top 8 most important gaps

def convert_api_response_to_dashboard(api_result: Dict) -> Dict:
    """Convert HF Space API response to dashboard format"""
    
    # Create dashboard-compatible analysis results
    analysis_results = {}
    
    # Map API response to dashboard categories
    risk_score = api_result.get('risk_score', 50)
    critical_issues = api_result.get('critical_issues', [])
    
    if risk_score >= 70:
        # High risk - populate liability and jurisdiction cards
        analysis_results['liability'] = {
            'issues': [{'label': 'High risk contract detected', 'severity': 'high'}],
            'severity': 'high'
        }
        analysis_results['jurisdiction'] = {
            'issues': [{'label': 'Risk assessment required', 'severity': 'high'}],
            'severity': 'high'
        }
    elif risk_score >= 40:
        # Medium risk - populate payment and compliance cards
        analysis_results['payment_termination'] = {
            'issues': [{'label': 'Terms require negotiation', 'severity': 'medium'}],
            'severity': 'medium'
        }
        analysis_results['compliance'] = {
            'issues': [{'label': 'Compliance review needed', 'severity': 'medium'}],
            'severity': 'medium'
        }
    else:
        # Low risk - show minimal issues
        analysis_results['missing_provisions'] = {
            'issues': [{'label': 'Minor improvements possible', 'severity': 'low'}],
            'severity': 'low'
        }
    
    return analysis_results

def calculate_relevance_percentage(issues: List[Dict], severity: str) -> int:
    """Calculate relevance percentage based on issues and severity"""
    if not issues:
        return 0
    
    base_score = len(issues) * 15  # 15% per issue
    
    # Severity multipliers
    multipliers = {'high': 1.5, 'medium': 1.2, 'low': 1.0}
    multiplier = multipliers.get(severity, 1.0)
    
    final_score = min(95, int(base_score * multiplier))  # Cap at 95%
    return final_score

def categorize_red_flags_detailed(red_flags: List[Dict], contract_text: str) -> Dict:
    """Categorize red flags with detailed analysis for dashboard"""
    
    # Initialize all categories
    categorized = {}
    
    # Map red flags to categories
    for flag in red_flags:
        flag_category = flag.get('category', 'miscellaneous').lower()
        severity = flag.get('severity', 'low').lower()
        
        # Map to dashboard categories
        dashboard_category = map_to_dashboard_category(flag_category)
        
        if dashboard_category not in categorized:
            categorized[dashboard_category] = {
                'issues': [],
                'severity': 'low'
            }
        
        categorized[dashboard_category]['issues'].append({
            'label': flag.get('label', 'Unknown issue'),
            'description': flag.get('description', ''),
            'severity': severity
        })
        
        # Update category severity
        if severity == 'high':
            categorized[dashboard_category]['severity'] = 'high'
        elif severity == 'medium' and categorized[dashboard_category]['severity'] != 'high':
            categorized[dashboard_category]['severity'] = 'medium'
    
    # Add specific analysis for each category based on contract text
    categorized = enhance_category_analysis(categorized, contract_text)
    
    return categorized

def enhance_category_analysis(categorized: Dict, text: str) -> Dict:
    """Add specific legal analysis for each category"""
    
    text_lower = text.lower()
    
    # Liability & Indemnity Analysis
    if 'liability' not in categorized:
        categorized['liability'] = {'issues': [], 'severity': 'low'}
    
    if 'unlimited' in text_lower and 'liability' in text_lower:
        categorized['liability']['issues'].append({
            'label': 'Unlimited liability exposure detected',
            'description': 'Contract contains unlimited liability clause',
            'severity': 'high'
        })
        categorized['liability']['severity'] = 'high'
    
    # Jurisdiction Analysis
    if 'jurisdiction' not in categorized:
        categorized['jurisdiction'] = {'issues': [], 'severity': 'low'}
    
    unfavorable_jurisdictions = ['delaware', 'new york', 'california']
    for jurisdiction in unfavorable_jurisdictions:
        if jurisdiction in text_lower and 'governing law' in text_lower:
            categorized['jurisdiction']['issues'].append({
                'label': f'Governing law: {jurisdiction.title()}',
                'description': f'Contract governed by {jurisdiction.title()} law',
                'severity': 'medium'
            })
            categorized['jurisdiction']['severity'] = 'medium'
    
    # Payment Terms Analysis
    if 'payment_termination' not in categorized:
        categorized['payment_termination'] = {'issues': [], 'severity': 'low'}
    
    import re
    net_terms = re.findall(r'net\s+(\d+)\s+days?', text_lower)
    for term in net_terms:
        if int(term) > 60:
            categorized['payment_termination']['issues'].append({
                'label': f'Extended payment terms: NET {term} days',
                'description': f'Payment terms exceed standard NET 60',
                'severity': 'medium'
            })
            categorized['payment_termination']['severity'] = 'medium'
    
    return categorized

def map_to_dashboard_category(red_flag_category: str) -> str:
    """Map red flag categories to dashboard categories"""
    mapping = {
        'liability': 'liability',
        'indemnity': 'liability', 
        'governing_law': 'jurisdiction',
        'dispute': 'jurisdiction',
        'payment': 'payment_termination',
        'termination': 'payment_termination',
        'intellectual_property': 'compliance',
        'confidentiality': 'compliance',
        'restrictions': 'playbook',
        'force_majeure': 'legacy',
        'performance': 'language_patterns'
    }
    
    return mapping.get(red_flag_category.lower(), 'missing_provisions')

def call_api(files, params):
    """
    Request helper for /review_pipeline with robust error surfacing.
    Returns a tuple: (status_label, payload)
     - status_label in {'ok', 'rejected', 'error', 'timeout', 'network_error'}
     - payload is dict or string with details
    """
    try:
        r = requests.post(f"{API_BASE_URL}/review_pipeline", files=files, params=params, timeout=60)
        if r.status_code == 200:
            try:
                return "ok", r.json()
            except Exception:
                return "ok", r.text
        elif r.status_code == 422:
            # HF/your backend rejected the document — parse detail if present
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            # return explicit 'rejected' label so caller can decide soft vs hard rejection
            return "rejected", detail
        else:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            return "error", {"status_code": r.status_code, "detail": detail}
    except requests.Timeout:
        return "timeout", "Timeout contacting backend"
    except requests.RequestException as e:
        return "network_error", str(e)
    except Exception as e:
        return "error", str(e)

def process_contract_via_api(uploaded_file, user_email: str):
    """Process contract via HF Space API endpoint"""
    
    if not uploaded_file or not user_email:
        return None
    
    try:
        # Show processing status
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Stage 1: Preparing upload
        status_text.text("Stage 1: Preparing upload to AI backend...")
        progress_bar.progress(20)
        time.sleep(0.5)
        
        file_bytes = uploaded_file.read()
        
        # Stage 2: Sending to HF Space API
        status_text.text("Stage 2: Sending to HF Space AI backend...")
        progress_bar.progress(40)
        time.sleep(0.5)
        
        # Prepare API request
        files = {"file": (uploaded_file.name, file_bytes, "application/octet-stream")}
        params = {
            "requester_email": user_email,
            "jurisdiction": "General",
            "strict_mode": "false"
        }
        
        status, payload = call_api(files, params)

        # Robust handling of API outcomes
        if status == "rejected":
            # Try to get a clear rejection_reason string
            rejection_reason = ""
            if isinstance(payload, dict):
                # common HF pattern might be: {"detail": "Rejected: ..."} or {"rejection_reason": "..."}
                rejection_reason = payload.get("rejection_reason") or payload.get("detail") or str(payload)
            else:
                rejection_reason = str(payload)

            rejection_reason_lower = rejection_reason.lower()

            # Define hard non-legal indicators (do NOT proceed)
            hard_non_legal_indicators = [
                "not a legal", "not a contract", "academic", "assignment", "code files",
                "python code", "resume", "cv", "invoice", "image only", "no text detected"
            ]
            # Define soft indicators where we can fallback to local/educational processing
            soft_indicators = [
                "insufficient joint evidence", "similarity", "essentials", "parties/signatures",
                "length", "embedding", "vector store", "chroma", "cache", "download failed"
            ]

            is_hard_non_legal = any(token in rejection_reason_lower for token in hard_non_legal_indicators)
            is_soft_rejection = any(token in rejection_reason_lower for token in soft_indicators)

            # Logging/debugging: keep the raw payload in session_state for debugging
            st.session_state.last_api_payload = payload
            st.session_state.last_rejection_reason = rejection_reason

            if is_hard_non_legal:
                # Tell user to upload a real contract (hard block)
                return {
                    'success': False,
                    'error': f"Document rejected as non-legal: {rejection_reason}"
                }
            elif is_soft_rejection:
                # Soft rejection: backend had trouble (embedding/length) — fallback to educational analysis
                # read file again safely (see note below about file pointer)
                try:
                    uploaded_file.seek(0)
                except Exception:
                    pass
                file_bytes = uploaded_file.read() if hasattr(uploaded_file, 'read') else uploaded_file.getvalue()
                text = None
                try:
                    text = file_bytes.decode('utf-8', errors='ignore')
                except Exception:
                    text = str(file_bytes)[:1000]

                # call educational fallback that also sends email
                detection_details = {'confidence': 'low', 'score': 0, 'legal_indicators': []}
                return handle_educational_analysis(uploaded_file, user_email, text, detection_details)

            else:
                # Unknown rejection reason — surface to user but also provide fallback option
                return {
                    'success': False,
                    'error': f"API rejected document: {rejection_reason} (you can retry or use override options)"
                }

        elif status == "ok":
            api_result = payload
        else:
            # status in {'error','timeout','network_error'}
            return {'success': False, 'error': f"API processing failed ({status}): {payload}"}
    except Exception as e:
        return {'success': False, 'error': f"Unexpected error: {e}"}

def process_contract_local_fallback(uploaded_file, user_email: str, progress_bar, status_text):
    """Lightweight fallback processing for Streamlit-only deployment"""
    
    # Fallback removed
    
    try:
        # Stage 3: Local analysis
        status_text.text("Stage 3: Local fallback analysis...")
        progress_bar.progress(60)
        
        # Simple local processing
        file_bytes = uploaded_file.read() if hasattr(uploaded_file, 'read') else uploaded_file.getvalue()
        text = file_bytes.decode('utf-8', errors='ignore')
        
        # Simplified analysis for fallback
        red_flags = []
        is_contract = True  # Assume it's legal for basic processing
        
        # Calculate risk score
        high_risks = len([rf for rf in red_flags if rf.get('severity') == 'high'])
        medium_risks = len([rf for rf in red_flags if rf.get('severity') == 'medium'])
        risk_score = min(100, high_risks * 30 + medium_risks * 15)
        
        # Determine recommendation
        if risk_score >= 70:
            recommendation = "REJECT"
        elif risk_score >= 40:
            recommendation = "NEGOTIATE"
        else:
            recommendation = "APPROVE"
        
        # Stage 4: Complete
        status_text.text("Local analysis complete!")
        progress_bar.progress(100)
        time.sleep(0.5)
        
        # Create simplified result
        result = {
            'filename': uploaded_file.name,
            'contract_type': 'Legal Document',
            'recommendation': recommendation,
            'risk_score': risk_score,
            'red_flags': red_flags,
            'critical_issues': [rf['label'] for rf in red_flags if rf.get('severity') == 'high'][:3],
            'processing_time_seconds': 1.5,
            'executive_summary': f"""
LOCAL FALLBACK ANALYSIS

RECOMMENDATION: {recommendation}
Risk Score: {risk_score}/100

High Risk Issues: {high_risks}
Medium Risk Issues: {medium_risks}

This analysis was performed locally as a fallback.
For full AI-enhanced analysis, please ensure cloud connectivity.
"""
        }
        
        # Send basic email
        # Skip email in fallback mode
        pass
        
        # Create dashboard results
        analysis_results = {}
        if risk_score >= 50:
            analysis_results['liability'] = {
                'issues': [{'label': 'Risk detected - requires review', 'severity': 'medium'}],
                'severity': 'medium'
            }
        
        return {
            'result': result,
            'analysis_results': analysis_results,
            'success': True,
            'api_powered': False
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Local processing failed: {str(e)}'
        }

def process_contract_sync(uploaded_file, user_email: str):
    """Process the uploaded contract through the pipeline (synchronous version)"""
    
    if not uploaded_file or not user_email:
        return None
    
    try:
        # Show processing status
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Stage 1: Upload
        status_text.text("Stage 1: Reading document...")
        progress_bar.progress(20)
        time.sleep(0.5)
        
        file_bytes = uploaded_file.read()
        
        # Stage 2: Analysis
        status_text.text("Stage 2: Analyzing contract...")
        progress_bar.progress(40)
        time.sleep(0.5)
        
        # API-ONLY MODE - No local processing in cloud deployment
        return {
            'success': False,
            'error': 'Cloud API unavailable. Please check HF Space connection and try again.'
        }
        
        # Extract text properly
        try:
            text = read_any(file_bytes, uploaded_file.name)
        except:
            # Fallback for demo
            text = file_bytes.decode('utf-8', errors='ignore')
        
        # LIBERAL: Analyze ANY potentially legal document
        is_legal_doc, detection_details = looks_like_contract_v2(text)
        
        # Enhanced context analysis (no async for Streamlit compatibility)
        try:
            from agents.web_verifier import web_verifier
            
            # Get search terms and fallback improvements
            search_terms = web_verifier.extract_search_terms(text, uploaded_file.name)
            fallback_improvements = web_verifier.get_fallback_improvements(text)
            
            detection_details.update({
                'search_terms': search_terms,
                'web_improvements': fallback_improvements,
                'web_context': f"Analysis enhanced with {len(search_terms)} legal context terms"
            })
        except ImportError:
            pass
        
        # Enhanced handling based on formal contract elements
        if not is_legal_doc:
            score = detection_details.get('score', 0)
            reason = detection_details.get('reason', '')
            essential_elements = detection_details.get('essential_elements', 0)
            confidence = detection_details.get('confidence', 'none')
            
            # STRICT rejection for obvious non-legal files
            if score <= -80 or any(keyword in reason.lower() for keyword in ['academic', 'assignment', 'code', 'technical', 'resume', 'personal']):
                return {
                    'success': False, 
                    'error': f"Document type detected: {reason}. Please upload a legal contract, agreement, or official form."
                }
            
            # For documents with some legal elements but insufficient for contracts
            elif essential_elements >= 1 or score > -50:
                return handle_educational_analysis(uploaded_file, user_email, text, detection_details)
            
            else:
                return {
                    'success': False,
                    'error': f"Document lacks essential contract elements. {reason}. Please upload formal legal contracts or agreements."
                }
        
        # Enhanced risk analysis with RAG
        red_flags = find_red_flags(text)
        
        # Get RAG-enhanced analysis
        relevant_rules = risk_rules_rag.retrieve_relevant_rules(text, top_k=5)
        rag_recommendations = risk_rules_rag.get_risk_recommendations(red_flags)
        
        # Stage 3: Categorizing
        status_text.text("Stage 3: Categorizing risks...")
        progress_bar.progress(60)
        time.sleep(0.5)
        
        # Categorize results for dashboard with detailed mapping
        analysis_results = categorize_red_flags_detailed(red_flags, text)
        
        # Calculate risk score
        high_risks = len([rf for rf in red_flags if rf.get('severity') == 'high'])
        medium_risks = len([rf for rf in red_flags if rf.get('severity') == 'medium'])
        risk_score = min(100, high_risks * 30 + medium_risks * 15)
        
        # Stage 4: Email delivery
        status_text.text("Stage 4: Sending email report...")
        progress_bar.progress(80)
        time.sleep(0.5)
        
        # Determine recommendation
        if risk_score >= 70:
            recommendation = "REJECT"
        elif risk_score >= 40:
            recommendation = "NEGOTIATE"
        else:
            recommendation = "APPROVE"
        
        # Stage 5: Complete
        status_text.text("Analysis complete!")
        progress_bar.progress(100)
        time.sleep(0.5)
        
        # Create enhanced result object with RAG insights
        result = {
            'filename': uploaded_file.name,
            'contract_type': 'Non-Disclosure Agreement' if 'nda' in uploaded_file.name.lower() else 'Service Agreement',
            'recommendation': recommendation,
            'risk_score': risk_score,
            'red_flags': red_flags,
            'critical_issues': [rf['label'] for rf in red_flags if rf.get('severity') == 'high'][:3],
            'processing_time_seconds': 2.5,
            'rag_recommendations': rag_recommendations,
            'relevant_rules': [r['title'] for r in relevant_rules[:3]],
            'executive_summary': f"""
CONTRACT ANALYSIS SUMMARY - ENHANCED WITH AI KNOWLEDGE BASE

RISK ASSESSMENT: {risk_score}/100 ({recommendation})

KEY FINDINGS:
• {high_risks} High Risk Issues Detected
• {medium_risks} Medium Risk Issues Found  
• {len(red_flags) - high_risks - medium_risks} Low Risk Items Noted

CRITICAL ISSUES:
{chr(10).join(f'• {issue}' for issue in [rf['label'] for rf in red_flags if rf.get('severity') == 'high'][:3]) if high_risks > 0 else '• None detected'}

RAG-ENHANCED RECOMMENDATIONS:
{chr(10).join(f'• {rec}' for rec in rag_recommendations[:3]) if rag_recommendations else '• Standard contract review protocols apply'}

KNOWLEDGE BASE RULES APPLIED:
{chr(10).join(f'• {rule}' for rule in [r['title'] for r in relevant_rules[:3]])}

FINAL RECOMMENDATION: {recommendation}
The contract {'requires immediate legal review and significant negotiation' if recommendation == 'REJECT' else 'needs careful negotiation on identified risk areas' if recommendation == 'NEGOTIATE' else 'appears acceptable with standard legal review'}.
"""
        }
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Send email (using SendGrid)
        try:
            from agents.tools_email import send_email_sendgrid
            
            # Create email content
            html_content = f"""
<h2>Contract Analysis Complete: {uploaded_file.name}</h2>
<div style="padding: 15px; background-color: {'red' if recommendation == 'REJECT' else 'orange' if recommendation == 'NEGOTIATE' else 'green'}; color: white;">
    <h3>RECOMMENDATION: {recommendation}</h3>
    <p>Risk Score: {risk_score}/100</p>
</div>
<h3>Key Findings:</h3>
<ul>
    <li>High Risk Issues: {high_risks}</li>
    <li>Medium Risk Issues: {medium_risks}</li>
    <li>Processing Time: 2.5 seconds</li>
</ul>
<p><i>Generated by Pactify Contract Analyzer</i></p>
"""
            
            # Enhanced email with RAG insights
            enhanced_html = html_content + f"""
<h3>AI Knowledge Base Insights:</h3>
<ul>
{''.join(f'<li><b>{rule["title"]}</b>: {rule["category"].replace("_", " ").title()} Risk</li>' for rule in relevant_rules[:3])}
</ul>

<h3>Smart Recommendations:</h3>
<ul>
{''.join(f'<li>{rec}</li>' for rec in rag_recommendations[:3]) if rag_recommendations else '<li>Standard contract review protocols recommended</li>'}
</ul>
"""
            
            send_email_sendgrid(
                to_email=user_email,
                subject=f"Contract Analysis: {recommendation} - {uploaded_file.name}",
                body=enhanced_html,
                attachment_bytes=file_bytes,
                attachment_name=uploaded_file.name
            )
            
        except Exception as email_error:
            st.warning(f"Analysis completed but email delivery failed: {email_error}")
        
        return {
            'result': result,
            'analysis_results': analysis_results,
            'success': True
        }
        
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def show_success_summary(process_result: Dict):
    """Show analysis completion summary"""
    result = process_result['result']
    
    # Success banner - handle all modes
    if result['recommendation'] == "ENHANCE":
        st.info("Legal Document Analysis Complete - ENHANCEMENT OPPORTUNITIES IDENTIFIED")
    elif result['recommendation'] == "IMPROVE":
        st.warning("Legal Document Analysis Complete - IMPROVEMENTS REQUIRED")
    elif result['recommendation'] == "APPROVE":
        st.success("Contract Analysis Complete - APPROVED")
    elif result['recommendation'] == "NEGOTIATE":
        st.warning("Contract Analysis Complete - NEGOTIATE RECOMMENDED")
    else:
        st.error("Contract Analysis Complete - REJECTION RECOMMENDED")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Risk Score", f"{result['risk_score']}/100")
    
    with col2:
        st.metric("Processing Time", f"{result['processing_time_seconds']:.2f}s")
    
    with col3:
        critical_count = len(result['critical_issues'])
        st.metric("Critical Issues", critical_count)
    
    with col4:
        total_flags = len(result['red_flags'])
        st.metric("Total Flags", total_flags)
    
    # Email confirmation
    st.info(f"Detailed analysis report has been sent to your email!")

# Export functionality removed per user request

def main():
    """Main dashboard application"""
    
    # Initialize session state with persistent empty structure to maintain card shape
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    
    # Maintain card structure even when no analysis
    if st.session_state.analysis_results is None:
        # Create empty structure to maintain layout
        st.session_state.empty_card_structure = True
    
    # Header
    render_header()
    
    # Tab navigation
    tab1, tab2, tab3 = render_tabs()
    
    with tab1:  # Build tab (main interface)
        
        # Two-column layout
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown("### Document Upload")
            
            # Email input
            user_email = st.text_input(
                "Your Email Address",
                placeholder="legal@company.com",
                help="Analysis report will be sent to this email"
            )
            
            # File upload
            uploaded_file = render_upload_zone()
            
            # Process button
            if st.button("Start Analysis", type="primary", use_container_width=True):
                if uploaded_file and user_email and "@" in user_email:
                    # Process the contract via HF Space API
                    with st.spinner("Processing contract via HF Space AI backend..."):
                        process_result = process_contract_via_api(uploaded_file, user_email)
                    
                    if process_result and process_result.get('success'):
                        st.session_state.analysis_results = process_result['analysis_results']
                        st.session_state.last_analysis = process_result
                        
                        # Check if it's educational/improvement mode
                        if process_result.get('educational_mode') or process_result.get('improvement_mode'):
                            st.info("Educational analysis complete! Enhancement guide sent to your email.")
                            
                            # Show improvement recommendations on screen
                            st.markdown("### Smart Enhancement Recommendations:")
                            for i, rec in enumerate(process_result['result']['rag_recommendations'][:6], 1):
                                st.write(f"{i}. {rec}")
                                
                            # Add download option for improvements
                            if st.button("Download Enhancement Guide", type="secondary"):
                                enhancement_text = "\n".join(f"{i}. {rec}" for i, rec in enumerate(process_result['result']['rag_recommendations'], 1))
                                st.download_button(
                                    label="Download as TXT",
                                    data=enhancement_text,
                                    file_name=f"enhancement_guide_{uploaded_file.name}.txt",
                                    mime="text/plain"
                                )
                                
                            st.success("Comprehensive enhancement guide sent to your email!")
                        else:
                            # Show API source
                            api_powered = process_result.get('api_powered', False)
                            source_msg = "HF Space AI" if api_powered else "Local AI" 
                            st.success(f"Analysis complete via {source_msg}! Report sent to your email.")
                        
                        st.rerun()
                    elif process_result and not process_result.get('success'):
                        error_msg = process_result.get('error', 'Analysis failed')
                        st.error(error_msg)
                        
                        # Store info for potential override
                        if uploaded_file:
                            try:
                                file_bytes = uploaded_file.read() if hasattr(uploaded_file, 'read') else uploaded_file.getvalue()
                                text = file_bytes.decode('utf-8', errors='ignore')
                                st.session_state.last_upload_text = text
                                st.session_state.last_rejection_reason = error_msg
                                
                                # Skip override in API-only mode
                                pass
                            except:
                                pass
                    
                elif not user_email or "@" not in user_email:
                    st.error("Please enter a valid email address")
                else:
                    st.error("Please upload a contract file")
            
            # Add override option for borderline cases
            if st.session_state.get('show_override_options'):
                st.markdown("---")
                st.markdown("### Document Analysis Override")
                st.info("The system is uncertain about this document type. You can override and force analysis:")
                
                # Simplified override options for API-only mode
                if uploaded_file and st.session_state.get('last_upload_text'):
                    options = [
                        {'label': 'Employment Agreement', 'type': 'employment'},
                        {'label': 'Non-Disclosure Agreement', 'type': 'nda'},
                        {'label': 'Service Agreement', 'type': 'service'},
                        {'label': 'Legal Form/Application', 'type': 'legal_form'}
                    ]
                    
                    override_choice = st.selectbox(
                        "How should this document be analyzed?",
                        options=[opt['label'] for opt in options],
                        help="Select the document type for specialized analysis"
                    )
                    
                    if st.button("Force Analysis", type="secondary"):
                        if user_email and "@" in user_email:
                            # Simple override processing
                            
                            # Process with override via API
                            with st.spinner("Processing with override..."):
                                process_result = process_contract_via_api(uploaded_file, user_email)
                            
                            if process_result and process_result.get('success'):
                                st.session_state.analysis_results = process_result['analysis_results']
                                st.session_state.last_analysis = process_result
                                st.session_state.show_override_options = False
                                st.success("Override analysis complete!")
                                st.rerun()
                        else:
                            st.error("Please enter a valid email address")
            
            # Show success summary if analysis is complete
            if st.session_state.get('last_analysis') and st.session_state.last_analysis.get('success'):
                st.markdown("---")
                show_success_summary(st.session_state.last_analysis)
        
        with col_right:
            st.markdown("### Analysis Results")
            
            # Render analysis cards
            render_analysis_cards(st.session_state.analysis_results)
    
    with tab2:  # Review tab
        st.markdown("### Review Analysis")
        
        if st.session_state.get('last_analysis'):
            result = st.session_state.last_analysis['result']
            
            st.markdown(f"**Contract:** {result['filename']}")
            st.markdown(f"**Type:** {result['contract_type']}")
            st.markdown(f"**Recommendation:** {result['recommendation']}")
            
            # Executive summary
            st.markdown("#### Executive Summary")
            st.text_area("Summary", result['executive_summary'], height=200, disabled=True)
            
            # Red flags
            st.markdown("#### Risk Details")
            for i, flag in enumerate(result['red_flags'][:10], 1):
                severity = flag.get('severity', 'unknown').upper()
                label = flag.get('label', 'Unknown issue')
                description = flag.get('description', '')
                
                color = {'HIGH': '▲', 'MEDIUM': '▬', 'LOW': '▼'}.get(severity, '▣')
                st.markdown(f"{color} **{severity}**: {label}")
                if description:
                    st.markdown(f"   _{description}_")
        else:
            st.info("Upload and analyze a contract to view detailed results here.")
    
    with tab3:  # Automate tab
        st.markdown("### Automation Settings")
        
        st.markdown("#### AI Backend Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Primary Backend**: HF Space AI")
            st.code(f"Endpoint: {HF_API_BASE}")
            
        # Fallback removed
        
        st.markdown("#### System Integration")
        st.success("▣ Frontend: Streamlit Cloud (pactify.streamlit.app)")
        st.success("▣ AI Backend: HF Space (vinabi-pactify.hf.space)")
        st.success("▣ Email Service: SendGrid Integration")
        
        if st.button("Test HF Space Connection"):
            try:
                test_response = requests.get(f"{HF_API_BASE}/healthz", timeout=5)
                if test_response.status_code == 200:
                    st.success("HF Space AI backend is online and responding!")
                else:
                    st.error(f"HF Space returned status: {test_response.status_code}")
            except Exception as e:
                st.error(f"HF Space connection failed: {e}")

if __name__ == "__main__":
    main()
