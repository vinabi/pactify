# agents/pipeline.py
import os, re
from typing import List, Dict, Any, Optional
from loguru import logger
from pydantic import ValidationError

from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from langsmith import traceable
from langchain_core.runnables import RunnableConfig

from .schemas import ClassifyOut, PolicyOut, RedlineOut
from .prompts import CLASSIFY_PROMPT, POLICY_PROMPT, REDLINE_PROMPT, REPORT_SUMMARY_PROMPT
from .tools_parser import read_any, rough_clauses
from .tools_vector import get_chroma, retrieve_precedents, retrieve_snippets
from .contract_detector import find_red_flags, compare_to_templates, identify_contract_type

from api.models import AnalyzeRequest, AnalyzeResponse, Clause
from api.utils import JsonRepair
from api.settings import settings

RISK_KB = "risk_knowledge"

def make_llm():
    api_key = settings.groq_api_key
    model = settings.groq_model
    temperature = float(settings.groq_temperature)
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. See .env")
    return ChatGroq(groq_api_key=api_key, model_name=model, temperature=temperature)

def call_json(llm, system_prompt: str, user_text: str, schema_cls, *, run_name: str,
              base_cfg: Optional[RunnableConfig] = None, extra_meta: Optional[Dict[str, Any]] = None):
    cfg: RunnableConfig = dict(base_cfg or {})
    meta = dict(cfg.get("metadata", {}))
    if extra_meta:
        meta.update(extra_meta)
    cfg["metadata"] = meta
    cfg["run_name"] = run_name
    msgs = [SystemMessage(content=system_prompt), HumanMessage(content=user_text)]
    res = llm.invoke(msgs, config=cfg)
    data = JsonRepair.extract_json(res.content)
    try:
        return schema_cls(**data)
    except ValidationError:
        retry_msgs = [SystemMessage(content=system_prompt + "\nReturn STRICT JSON ONLY."),
                      HumanMessage(content=user_text)]
        res2 = llm.invoke(retry_msgs, config={**cfg, "run_name": f"{run_name}__retry"})
        data2 = JsonRepair.extract_json(res2.content)
        return schema_cls.model_validate(data2)

@traceable(run_type="chain", name="analyze_contract")
def analyze_contract(req: AnalyzeRequest, raw: bytes, filename: str) -> AnalyzeResponse:
    base_cfg: RunnableConfig = {
        "metadata": {
            "file_name": filename,
            "jurisdiction": req.jurisdiction,
            "strict_mode": req.strict_mode,
            "top_k_precedents": req.top_k_precedents,
        },
        "run_name": "ContractAnalyzer",
    }

    llm = make_llm()
    text = read_any(raw, filename)
    blocks = rough_clauses(text)

    vect_client = get_chroma(settings.chroma_dir)

    # NEW: Contract type identification and template comparison
    contract_type, type_confidence = identify_contract_type(text)
    template_analysis = compare_to_templates(text, vect_client)
    
    # doc-level deterministic red flags (always surfaced)
    doc_flags = find_red_flags(text)

    clauses: List[Clause] = []
    high = med = low = 0

    for i, (heading, clause_text) in enumerate(blocks, start=1):
        cid = f"C{i:03d}"

        # RAG: pull risk rubric snippets
        risk_snips = []
        try:
            for meta, doc in retrieve_snippets(vect_client, RISK_KB, clause_text, k=3):
                src = meta.get("source", "risk_knowledge")
                risk_snips.append(f"— {src} :: {doc[:800]}")
        except Exception:
            pass
        risk_block = ("\n\nRisk rubric context:\n" + "\n".join(risk_snips) + "\n") if risk_snips else ""

        # NEW: Template comparison context for this clause
        template_context = ""
        if template_analysis.get("template_matches"):
            relevant_templates = [t for t in template_analysis["template_matches"] if t.get("similarity_score", 0) > 0.3]
            if relevant_templates:
                template_context = "\n\nTemplate comparison context:\n"
                for template in relevant_templates[:2]:  # Top 2 relevant templates
                    template_context += f"— {template['template_type']} ({template['clause_type']}): {template['template_text'][:300]}...\n"

        # Contract type context
        type_context = f"\n\nContract type: {contract_type} (confidence: {type_confidence:.2f})\n"
        
        # Template deviations specific to this clause
        deviation_context = ""
        if template_analysis.get("deviations"):
            relevant_deviations = [d for d in template_analysis["deviations"] if d["severity"] in ["high", "medium"]]
            if relevant_deviations:
                deviation_context = "\n\nTemplate deviations detected:\n" + "\n".join([
                    f"— {d['description']}" for d in relevant_deviations[:3]
                ]) + "\n"

        # deterministic flags that directly match this clause's text
        flags_for_clause = []
        for rf in doc_flags:
            pat = rf.get("pattern")
            if pat and re.search(pat, clause_text, re.I | re.S):
                flags_for_clause.append({
                    "label": rf["label"], 
                    "category": rf.get("category", "unknown"),
                    "description": rf.get("description", "")
                })
        
        red_flag_context = ""
        if flags_for_clause:
            red_flag_context = "\n\nRed flags detected:\n" + "\n".join([
                f"— {flag['label']} ({flag['category']}): {flag['description']}" 
                for flag in flags_for_clause
            ]) + "\n"

        # -------- Classifier --------
        classify_input = f"""
{risk_block}
{template_context}
{type_context}
{deviation_context}
{red_flag_context}

Clause heading: {heading}

Clause text:
{clause_text[:5000]}
        """.strip()
        
        cls: ClassifyOut = call_json(
            llm, CLASSIFY_PROMPT, classify_input, ClassifyOut,
            run_name="Classifier", base_cfg=base_cfg,
            extra_meta={"clause_id": cid, "heading": heading[:120], "contract_type": contract_type},
        )

        # -------- Policy check --------
        policy_input = f"""
{risk_block}
{template_context}
{red_flag_context}

Clause text:
{clause_text[:5000]}
        """.strip()
        
        pol: PolicyOut = call_json(
            llm, POLICY_PROMPT, policy_input, PolicyOut,
            run_name="PolicyCheck", base_cfg=base_cfg, 
            extra_meta={"clause_id": cid, "contract_type": contract_type},
        )

        # merge deterministic flags
        merged_violations = list(pol.violations or [])
        for flag in flags_for_clause:
            flag_label = flag["label"]
            if flag_label not in merged_violations:
                merged_violations.append(flag_label)

        # -------- Redline (Medium/High or violations) --------
        proposed_text = explanation = note = None
        do_redline = (cls.risk.lower() in {"medium", "high"}) or (len(merged_violations) > 0)
        if do_redline:
            # Get precedents for redlining
            precedent_snips: List[str] = []
            if req.top_k_precedents > 0:
                for title, snippet in retrieve_precedents(vect_client, clause_text, k=req.top_k_precedents):
                    precedent_snips.append(f"### {title}\n{snippet}")
            precedents_block = ("\n\nPrecedents (optional):\n" + "\n\n".join(precedent_snips)) if precedent_snips else ""
            
            # Enhanced redline input with all context
            redline_input = f"""
{risk_block}
{template_context}
{type_context}
{deviation_context}
{red_flag_context}

Clause heading: {heading}

Original clause text:
{clause_text[:5000]}

{precedents_block}
            """.strip()
            
            red: RedlineOut = call_json(
                llm, REDLINE_PROMPT, redline_input, RedlineOut,
                run_name="RedlineSuggestor", base_cfg=base_cfg,
                extra_meta={"clause_id": cid, "risk": cls.risk, "contract_type": contract_type},
            )
            proposed_text, explanation, note = red.proposed_text, red.explanation, red.negotiation_note

        # tally
        rn = cls.risk.lower()
        if rn == "high":   high += 1
        elif rn == "medium": med += 1
        else:              low += 1

        clauses.append(Clause(
            id=cid, heading=heading, text=clause_text,
            category=cls.category, risk=cls.risk, rationale=cls.rationale,
            policy_violations=merged_violations,
            proposed_text=proposed_text, explanation=explanation, negotiation_note=note,
        ))

    # Enhanced summary with template analysis
    flags_str = ", ".join({f["label"] for f in doc_flags}) if doc_flags else "none"
    template_summary = f"Contract type: {contract_type} (confidence: {type_confidence:.1%})"
    
    if template_analysis.get("deviations"):
        deviation_count = len([d for d in template_analysis["deviations"] if d["severity"] in ["high", "medium"]])
        template_summary += f", {deviation_count} template deviations"
    
    coverage_score = template_analysis.get("coverage_score", 0.0)
    template_summary += f", template coverage: {coverage_score:.1%}"
    
    summary_input = f"""
Risk Analysis Results:
- High Risk Clauses: {high}
- Medium Risk Clauses: {med}  
- Low Risk Clauses: {low}
- Document-level red flags: {flags_str}

Template Analysis:
- {template_summary}

Instructions: Provide a concise executive summary (3-5 bullets) focusing on:
1. Most critical risks requiring immediate attention
2. Template compliance issues
3. Financial/legal exposure
4. Recommended next steps with priorities
    """.strip()
    
    res = llm.invoke([SystemMessage(content=REPORT_SUMMARY_PROMPT), HumanMessage(content=summary_input)],
                     config={**base_cfg, "run_name": "ReportSynthesizer"})
    summary = res.content.strip()

    logger.info(f"File={filename} Type={contract_type} Risks(H/M/L)=({high}/{med}/{low}) Coverage={coverage_score:.1%}")
    return AnalyzeResponse(
        summary=summary, 
        high_risk_count=high, 
        medium_risk_count=med, 
        low_risk_count=low, 
        clauses=clauses,
        # Add template analysis to response (if supported by your model)
        metadata={
            "contract_type": contract_type,
            "type_confidence": type_confidence,
            "template_coverage": coverage_score,
            "template_deviations": len(template_analysis.get("deviations", []))
        } if hasattr(AnalyzeResponse, 'metadata') else None
    )
