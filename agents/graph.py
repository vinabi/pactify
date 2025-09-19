# agents/graph.py
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

# ---- State ----
class State(TypedDict):
    clauses: List[Dict[str, Any]]   # list of processed clauses
    summary: str
    strict_mode: bool
    jurisdiction: str
    top_k_precedents: int
    raw_text: str

# ---- Node functions ----
def chunker(state: State) -> State:
    from .tools_parser import rough_clauses
    blocks = rough_clauses(state["raw_text"])
    return {**state, "clauses": [{"heading": h, "text": t} for h, t in blocks]}

def classifier(state: State) -> State:
    from .pipeline import make_llm, call_json
    from .schemas import ClassifyOut
    from .prompts import CLASSIFY_PROMPT
    llm = make_llm()
    updated = []
    for c in state["clauses"]:
        classify_in = f"Clause heading: {c['heading']}\n\nClause text:\n{c['text'][:5000]}"
        cls: ClassifyOut = call_json(llm, CLASSIFY_PROMPT, classify_in, ClassifyOut,
                                     run_name="Classifier",
                                     base_cfg={"metadata": {"heading": c['heading']}})
        c.update(dict(category=cls.category, risk=cls.risk, rationale=cls.rationale))
        updated.append(c)
    return {**state, "clauses": updated}

def policy_check(state: State) -> State:
    from .pipeline import make_llm, call_json
    from .schemas import PolicyOut
    from .prompts import POLICY_PROMPT
    llm = make_llm()
    updated = []
    for c in state["clauses"]:
        pol: PolicyOut = call_json(llm, POLICY_PROMPT, c["text"][:5000], PolicyOut,
                                   run_name="PolicyCheck",
                                   base_cfg={"metadata": {"heading": c['heading']}})
        c["policy_violations"] = pol.violations
        updated.append(c)
    return {**state, "clauses": updated}

def redliner(state: State) -> State:
    from .pipeline import make_llm, call_json
    from .schemas import RedlineOut
    from .prompts import REDLINE_PROMPT
    llm = make_llm()
    updated = []
    for c in state["clauses"]:
        if c.get("risk","").lower() in {"medium","high"} or c.get("policy_violations"):
            red: RedlineOut = call_json(llm, REDLINE_PROMPT, c["text"][:5000], RedlineOut,
                                        run_name="RedlineSuggestor",
                                        base_cfg={"metadata": {"heading": c['heading']}})
            c.update(dict(
                proposed_text=red.proposed_text,
                explanation=red.explanation,
                negotiation_note=red.negotiation_note
            ))
        updated.append(c)
    return {**state, "clauses": updated}

def summarizer(state: State) -> State:
    from .pipeline import make_llm
    from .prompts import REPORT_SUMMARY_PROMPT
    from langchain.schema import SystemMessage, HumanMessage
    llm = make_llm()
    hi = sum(1 for c in state["clauses"] if c.get("risk","").lower()=="high")
    me = sum(1 for c in state["clauses"] if c.get("risk","").lower()=="medium")
    lo = sum(1 for c in state["clauses"] if c.get("risk","").lower()=="low")
    summary_in = f"High={hi}, Medium={me}, Low={lo}. Provide 3-5 bullets with top issues and next steps."
    res = llm.invoke([SystemMessage(content=REPORT_SUMMARY_PROMPT), HumanMessage(content=summary_in)])
    return {**state, "summary": res.content.strip()}

# ---- Graph assembly ----
def build_graph():
    g = StateGraph(State)
    g.add_node("Chunker", chunker)
    g.add_node("Classifier", classifier)
    g.add_node("PolicyCheck", policy_check)
    g.add_node("Redliner", redliner)
    g.add_node("Summarizer", summarizer)

    g.set_entry_point("Chunker")
    g.add_edge("Chunker", "Classifier")
    g.add_edge("Classifier", "PolicyCheck")
    g.add_edge("PolicyCheck", "Redliner")
    g.add_edge("Redliner", "Summarizer")
    g.add_edge("Summarizer", END)

    return g.compile()

graph = build_graph()
