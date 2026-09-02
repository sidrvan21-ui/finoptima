"""HTTP door + website. Same LangGraph. JSON routes stay for other programs."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

TEMPLATES = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES))

app = FastAPI(title="FinOptima", version="0.1.0")


@app.get("/health")
def health():
    from agents.llm import available_models
    from db.connection import probe_money_db

    return {
        "ok": True,
        "money_db": probe_money_db(),
        "llm_providers": available_models(),
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"audit": None, "waiting": False, "error": None},
    )


@app.post("/ui/run", response_class=HTMLResponse)
def ui_run(request: Request):
    from agents.graph import new_thread_id, start_audit

    try:
        audit = start_audit(new_thread_id())
        waiting = bool(audit.get("next"))
        return templates.TemplateResponse(
            request,
            "index.html",
            {"audit": audit, "waiting": waiting, "error": None},
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "audit": None,
                "waiting": False,
                "error": f"{type(exc).__name__}: {exc}",
            },
            status_code=500,
        )


@app.post("/ui/approve/{thread_id}", response_class=HTMLResponse)
def ui_approve(request: Request, thread_id: str):
    from agents.graph import resume_audit

    try:
        audit = resume_audit(thread_id, "approve")
        return templates.TemplateResponse(
            request,
            "index.html",
            {"audit": audit, "waiting": bool(audit.get("next")), "error": None},
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "audit": None,
                "waiting": False,
                "error": f"{type(exc).__name__}: {exc}",
            },
            status_code=500,
        )


@app.post("/ui/reject/{thread_id}", response_class=HTMLResponse)
def ui_reject(request: Request, thread_id: str):
    from agents.graph import resume_audit

    try:
        audit = resume_audit(thread_id, "reject")
        return templates.TemplateResponse(
            request,
            "index.html",
            {"audit": audit, "waiting": bool(audit.get("next")), "error": None},
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "audit": None,
                "waiting": False,
                "error": f"{type(exc).__name__}: {exc}",
            },
            status_code=500,
        )


@app.post("/audit")
def run_audit():
    from agents.graph import new_thread_id, start_audit

    return start_audit(new_thread_id())


@app.get("/audit/{thread_id}")
def read_audit(thread_id: str):
    from agents.graph import get_audit

    out = get_audit(thread_id)
    if not out["values"] and not out["next"]:
        raise HTTPException(status_code=404, detail="unknown thread_id")
    return out


@app.post("/audit/{thread_id}/approve")
def approve(thread_id: str):
    from agents.graph import resume_audit

    return resume_audit(thread_id, "approve")


@app.post("/audit/{thread_id}/reject")
def reject(thread_id: str):
    from agents.graph import resume_audit

    return resume_audit(thread_id, "reject")
