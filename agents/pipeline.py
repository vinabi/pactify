# agents/pipeline.py
import os
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
from .tools_vector import get_chroma, retrieve_precedents

from api.models import AnalyzeRequest, AnalyzeResponse, Clause
from api.utils import JsonRepair
from api.settings import settings


# ------------ LLM factory (Groq primary) ------------
def make_llm():
    api_key = settings.groq_api_key
    model = settings.groq_model
    temperature = float(settings.groq_temperature)
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. See .env")
    return ChatGroq(groq_api_key=api_key, model_name=model, temperature=temperature)


# ------------ Helper to call LLM with JSON contract + tracing labels ------------
def call_json(
    llm,
    system_prompt: str,
    user_text: str,
    schema_cls,
    *,
    run_name: str,
    base_cfg: Optional[RunnableConfig] = None,
    extra_meta: Optional[Dict[str, Any]] = None,
):
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
        # One strict retry
        retry_msgs = [
            SystemMessage(content=system_prompt + "\nReturn STRICT JSON ONLY."),
            HumanMessage(content=user_text),
        ]
        res2 = llm.invoke(retry_msgs, config={**cfg, "run_name": f"{run_name}__retry"})
        data2 = JsonRepair.extract_json(res2.content)
        return schema_cls.model_validate(data2)


# ------------ Main pipeline (traced) ------------
@traceable(run_type="chain", name="analyze_contract")
def analyze_contract(req: AnalyzeRequest, raw: bytes, filename: str) -> AnalyzeResponse:
    # base run config for LangSmith
    base_cfg: RunnableConfig = {
        "metadata": {
            "file_name": filename,
            "jurisdiction": req.jurisdiction,
            "strict_mode": req.strict_mode,
            "top_k_precedents": req.top_k_precedents,
        },
        "run_name": "ContractAnalyzer",
        # "tags": ["contract", "mvp", "groq"],  # optional
    }

    llm = make_llm()
    text = read_any(raw, filename)
    blocks = rough_clauses(text)

    chroma_dir = settings.chroma_dir
    vect_client = get_chroma(chroma_dir)

    clauses: List[Clause] = []
    high = med = low = 0

    for i, (heading, clause_text) in enumerate(blocks, start=1):
        cid = f"C{i:03d}"

        # -------- Classifier --------
        classify_in = (
            f"Clause heading: {heading}\n\n"
            f"Clause text:\n{clause_text[:5000]}"
        )
        cls: ClassifyOut = call_json(
            llm,
            CLASSIFY_PROMPT,
            classify_in,
            ClassifyOut,
            run_name="Classifier",
            base_cfg=base_cfg,
            extra_meta={"clause_id": cid, "heading": heading[:120]},
        )

        # -------- Policy check --------
        pol: PolicyOut = call_json(
            llm,
            POLICY_PROMPT,
            clause_text[:5000],
            PolicyOut,
            run_name="PolicyCheck",
            base_cfg=base_cfg,
            extra_meta={"clause_id": cid},
        )

        # -------- Redline (only for Medium/High or policy violations) --------
        proposed_text = explanation = note = None
        do_redline = cls.risk.lower() in {"medium", "high"} or len(pol.violations) > 0
        if do_redline:
            precedent_snippets: List[str] = []
            if req.top_k_precedents > 0:
                for title, snippet in retrieve_precedents(
                    vect_client, clause_text, k=req.top_k_precedents
                ):
                    precedent_snippets.append(f"### {title}\n{snippet}")

            precedents_block = (
                "\n\nPrecedents (optional):\n" + "\n\n".join(precedent_snippets)
                if precedent_snippets
                else ""
            )

            redline_in = (
                f"Clause heading: {heading}\n\n"
                f"Clause text:\n{clause_text[:5000]}\n"
                f"{precedents_block}"
            )
            red: RedlineOut = call_json(
                llm,
                REDLINE_PROMPT,
                redline_in,
                RedlineOut,
                run_name="RedlineSuggestor",
                base_cfg=base_cfg,
                extra_meta={"clause_id": cid, "risk": cls.risk},
            )
            proposed_text, explanation, note = (
                red.proposed_text,
                red.explanation,
                red.negotiation_note,
            )

        # tally
        risk_norm = cls.risk.lower()
        if risk_norm == "high":
            high += 1
        elif risk_norm == "medium":
            med += 1
        else:
            low += 1

        clauses.append(
            Clause(
                id=cid,
                heading=heading,
                text=clause_text,
                category=cls.category,
                risk=cls.risk,
                rationale=cls.rationale,
                policy_violations=pol.violations,
                proposed_text=proposed_text,
                explanation=explanation,
                negotiation_note=note,
            )
        )

    # -------- Report summary --------
    summary_in = (
        f"High={high}, Medium={med}, Low={low}. "
        f"Provide 3-5 bullets with top issues and next steps."
    )
    res = llm.invoke(
        [SystemMessage(content=REPORT_SUMMARY_PROMPT), HumanMessage(content=summary_in)],
        config={**base_cfg, "run_name": "ReportSynthesizer"},
    )
    summary = res.content.strip()

    logger.info(
        f"[Tracing] Project={os.environ.get('LANGCHAIN_PROJECT')} "
        f"File={filename} Risks(H/M/L)=({high}/{med}/{low})"
    )

    return AnalyzeResponse(
        summary=summary,
        high_risk_count=high,
        medium_risk_count=med,
        low_risk_count=low,
        clauses=clauses,
    )
# ------------ End of pipeline ------------