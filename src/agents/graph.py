"""LangGraph: engine → hybrid retrieve → LLM memo (with provider fallbacks) → judge → human Approve/Reject."""

from __future__ import annotations

import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any, List, TypedDict

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from audit.engine import get_cloud_flags, get_saas_flags
from agents.redact import redact_saas_flags
from agents.rag import retrieve_rules
from db.connection import enable_langsmith

class AuditState(TypedDict, total=False):
    cloud_flags: List[dict]
    saas_flags: List[dict]
    retrieve_query: str
    policy_hits: List[dict]
    memo: str
    decision: str
    llm_used: bool
    llm_model: str
    judge_ok: bool
    judge_reason: str


def _query_from_flags(cloud: list, saas: list) -> str:
    parts = []
    if cloud:
        parts.append(
            "cloud budget variance more than 15 percent and dollar overrun over 5000 mitigation plan"
        )
    if saas:
        parts.append(
            "subscription zero logins 30 consecutive days audit evidence workpaper"
        )
    return " ".join(parts)


def load_flags(state: AuditState) -> dict:
    cloud = get_cloud_flags()
    saas = redact_saas_flags(get_saas_flags())
    return {
        "cloud_flags": cloud,
        "saas_flags": saas,
        "retrieve_query": _query_from_flags(cloud, saas),
        "decision": "",
        "memo": "",
        "policy_hits": [],
        "llm_used": False,
        "llm_model": "",
        "judge_ok": False,
        "judge_reason": "",
    }


def route_after_flags(state: AuditState) -> str:
    if not state.get("cloud_flags") and not state.get("saas_flags"):
        return "idle"
    return "retrieve"


def idle(state: AuditState) -> dict:
    return {
        "memo": "No audit flags. Skipped RAG and OpenAI.",
        "policy_hits": [],
        "llm_used": False,
        "judge_ok": True,
        "judge_reason": "skipped: idle",
    }


def retrieve(state: AuditState) -> dict:
    hits = retrieve_rules(state.get("retrieve_query") or "", n_results=3)
    return {"policy_hits": hits}


def _facts_block(cloud: list, saas: list) -> str:
    # Every engine flag goes to the writer — do not drop finance rows.
    cloud_s = sorted(cloud, key=lambda r: r.get("over_usd", 0), reverse=True)
    saas_s = sorted(saas, key=lambda r: r.get("arr_usd", 0), reverse=True)
    lines = ["FACTS FROM ENGINE (do not change these numbers):"]
    for row in cloud_s:
        lines.append(
            f"- Cloud {row['entity']} / {row['department']}: "
            f"actual={row['actual']} limit={row['limit']} "
            f"over_usd={row['over_usd']} over_pct={row['over_pct']:.0%} "
            f"rules={row['rules']}"
        )
    for row in saas_s:
        lines.append(
            f"- SaaS {row['entity']} / {row['name']}: arr={row['arr_usd']} "
            f"idle_days={row['last_active_days_ago']} "
            f"owner={row.get('owner_email')} rules={row['rules']}"
        )
    return "\n".join(lines)


def generate(state: AuditState) -> dict:
    facts = _facts_block(state.get("cloud_flags") or [], state.get("saas_flags") or [])
    hits = state.get("policy_hits") or []
    policy = "\n\n".join(
        f"{h.get('heading')}\n{h.get('text')}" for h in hits
    ) or "(no policy hits)"
    if not hits:
        memo = (
            facts
            + "\n\nPOLICY HITS:\n(no policy hits)\n"
            + "\n[Skipped LLM: RAG returned nothing.]"
        )
        return {"memo": memo, "llm_used": False, "llm_model": ""}

    from agents.llm import available_models, chat

    if not available_models():
        memo = (
            facts
            + "\n\nPOLICY HITS:\n"
            + policy
            + "\n\n[No LLM API keys in .env. Memo is facts + retrieved rules only.]"
        )
        return {"memo": memo, "llm_used": False, "llm_model": ""}

    messages = [
        {
            "role": "system",
            "content": (
                "Write a short FinOps executive memo (under 200 words). "
                "Only discuss entities, products, and numbers listed in FACTS. "
                "Copy dollar figures and idle days exactly. "
                "Do not mention other vendors or invent idle days. "
                "Cite retrieved rule headings. Do not invent metrics."
            ),
        },
        {
            "role": "user",
            "content": facts + "\n\nRETRIEVED POLICY:\n" + policy,
        },
    ]
    try:
        out = chat(messages, temperature=0)
    except Exception:
        memo = (
            facts
            + "\n\nPOLICY HITS:\n"
            + policy
            + "\n\n[All LLM providers failed. Memo is facts + retrieved rules only.]"
        )
        return {"memo": memo, "llm_used": False, "llm_model": ""}

    memo = facts + "\n\nMEMO:\n" + out["content"]
    return {"memo": memo, "llm_used": True, "llm_model": out["model"]}


def _parse_verdict(raw: str) -> bool:
    """True if the judge said PASS. Unreadable output counts as FAIL."""
    for line in (raw or "").splitlines():
        u = line.upper().strip()
        if u.startswith("VERDICT"):
            if "FAIL" in u:
                return False
            if "PASS" in u:
                return True
    upper = (raw or "").upper()
    if "FAIL" in upper:
        return False
    if "PASS" in upper:
        return True
    return False


def _langsmith_judge_feedback(ok: bool, reason: str, *, scored: bool) -> None:
    """Send judge result to LangSmith as feedback (score 1 = PASS, 0 = FAIL)."""
    try:
        from langsmith import Client
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is None:
            return
        client = Client()
        if scored:
            client.create_feedback(
                run.id,
                key="judge_pass",
                score=1.0 if ok else 0.0,
                comment=(reason or "")[:1000],
            )
        else:
            client.create_feedback(
                run.id,
                key="judge_pass",
                comment=f"skipped: {reason}"[:1000],
            )
    except Exception:
        pass


def judge(state: AuditState) -> dict:
    """Second LLM call: did the memo invent numbers not in FACTS or policy hits?"""
    if not state.get("llm_used"):
        out = {"judge_ok": True, "judge_reason": "skipped: no LLM memo"}
        _langsmith_judge_feedback(True, out["judge_reason"], scored=False)
        return out
    memo = state.get("memo") or ""
    if "\nMEMO:\n" not in memo:
        out = {"judge_ok": True, "judge_reason": "skipped: no MEMO section"}
        _langsmith_judge_feedback(True, out["judge_reason"], scored=False)
        return out

    from agents.llm import available_models, chat

    if not available_models():
        out = {"judge_ok": True, "judge_reason": "skipped: no API key"}
        _langsmith_judge_feedback(True, out["judge_reason"], scored=False)
        return out

    facts, _, prose = memo.partition("\nMEMO:\n")
    hits = state.get("policy_hits") or []
    policy = "\n\n".join(
        f"{h.get('heading')}\n{h.get('text')}" for h in hits
    ) or "(no policy hits)"

    try:
        out_chat = chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a faithfulness judge, not a writer. "
                        "Compare MEMO numbers (dollars, percents, idle days) to FACTS and POLICY. "
                        "PASS if every such number appears in FACTS or POLICY. "
                        "FAIL if the memo invents, rounds, or swaps a number. "
                        "Reply with exactly two lines:\n"
                        "VERDICT: PASS\n"
                        "or\n"
                        "VERDICT: FAIL\n"
                        "REASON: one short sentence."
                    ),
                },
                {
                    "role": "user",
                    "content": facts
                    + "\n\nPOLICY:\n"
                    + policy
                    + "\n\nMEMO:\n"
                    + prose,
                },
            ],
            temperature=0,
        )
    except Exception:
        out = {"judge_ok": True, "judge_reason": "skipped: all LLM providers failed"}
        _langsmith_judge_feedback(True, out["judge_reason"], scored=False)
        return out

    raw = out_chat["content"]
    ok = _parse_verdict(raw)
    if not ok:
        out = {
            "judge_ok": False,
            "judge_reason": raw,
            "memo": facts + "\n\nJUDGE FAIL:\n" + raw + "\n\nMEMO:\n" + prose,
        }
        _langsmith_judge_feedback(False, raw, scored=True)
        return out
    out = {"judge_ok": True, "judge_reason": raw}
    _langsmith_judge_feedback(True, raw, scored=True)
    return out


def apply_decision(state: AuditState) -> dict:
    if (state.get("decision") or "").lower() == "reject":
        return {"memo": "Rejected. This memo is not official."}
    return {}


_GRAPH = None
_SAVER = None


def get_graph():
    enable_langsmith()
    global _GRAPH, _SAVER
    if _GRAPH is not None:
        return _GRAPH
    builder = StateGraph(AuditState)
    builder.add_node("load_flags", load_flags)
    builder.add_node("retrieve", retrieve)
    builder.add_node("generate", generate)
    builder.add_node("judge", judge)
    builder.add_node("idle", idle)
    builder.add_node("apply_decision", apply_decision)
    builder.add_edge(START, "load_flags")
    builder.add_conditional_edges(
        "load_flags",
        route_after_flags,
        {"idle": "idle", "retrieve": "retrieve"},
    )
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "judge")
    builder.add_edge("judge", "apply_decision")
    builder.add_edge("idle", END)
    builder.add_edge("apply_decision", END)

    ckpt_path = ROOT / "data" / "graph_checkpoints.sqlite"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ckpt_path), check_same_thread=False)
    _SAVER = SqliteSaver(conn)
    _SAVER.setup()

    _GRAPH = builder.compile(
        checkpointer=_SAVER,
        interrupt_before=["apply_decision"],
    )
    return _GRAPH


def start_audit(thread_id: str) -> dict[str, Any]:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke({}, config)
    snap = graph.get_state(config)
    return {"values": dict(snap.values), "next": list(snap.next), "thread_id": thread_id}


def resume_audit(thread_id: str, decision: str) -> dict[str, Any]:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, {"decision": decision})
    graph.invoke(None, config)
    snap = graph.get_state(config)
    return {"values": dict(snap.values), "next": list(snap.next), "thread_id": thread_id}


def get_audit(thread_id: str) -> dict[str, Any]:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snap = graph.get_state(config)
    return {"values": dict(snap.values), "next": list(snap.next), "thread_id": thread_id}


def new_thread_id() -> str:
    return uuid.uuid4().hex[:10]


def main() -> None:
    tid = new_thread_id()
    paused = start_audit(tid)
    vals = paused["values"]
    print("paused next=", paused["next"])
    print(
        "llm_used=",
        vals.get("llm_used"),
        "llm_model=",
        vals.get("llm_model"),
        "judge_ok=",
        vals.get("judge_ok"),
    )
    print((vals.get("memo") or "")[:800])
    print("--- auto-approve ---")
    done = resume_audit(tid, "approve")
    print("next=", done["next"])
    print((done["values"].get("memo") or "")[:400])


if __name__ == "__main__":
    main()
