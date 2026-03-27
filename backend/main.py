"""
FastAPI backend — Community Bank Compliance Agent
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

# Overmind — init before any LLM client is instantiated so auto-instrumentation captures all calls
from config import OVERMIND_API_KEY
if OVERMIND_API_KEY:
    from overmind_sdk import init as overmind_init, get_tracer, set_tag
    overmind_init(
        overmind_api_key=OVERMIND_API_KEY,
        service_name="compliance-agent",
        environment="hackathon",
        providers=["anthropic"],
    )

from data.live_data import fetch_macro_context, fetch_bls_unemployment, fetch_geo_risk_context
from data.synthetic_loans import LOAN_APPLICATIONS
from agent.compliance_agent import process_batch, process_loan, set_model
from agent.hitl import get_hitl_queue, submit_human_decision
from agent.self_repair import trigger_demo_failure
from agent.memory import read_list, read_longitudinal, MemoryTier, clear_session
from agent.observability import start_run, end_run, log_decision
from agent.synix_consolidation import consolidate, initial_build, get_synix_context, query_compliance_memory
from agent.ghost_store import init_schema as ghost_init, ping as ghost_ping
from agent.ghost_store import read_decisions as ghost_decisions, read_graduated_patterns as ghost_patterns
from agent.ghost_store import read_hitl_decisions as ghost_hitl

app = FastAPI(title="Compliance Agent API")


@app.on_event("startup")
async def startup_event():
    """On startup: init Ghost DB schema + Synix build."""
    try:
        ghost_init()
    except Exception:
        pass  # Don't block startup if Ghost is unreachable
    try:
        initial_build()
    except Exception:
        pass  # Don't block startup if Synix isn't installed yet

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── State ──────────────────────────────────────────────────────────────────────
_batch_results = []
_macro_cache = {}


# ── Models ────────────────────────────────────────────────────────────────────
class HITLDecision(BaseModel):
    loan_id: str
    decision: str  # APPROVE / DECLINE
    rationale: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/macro")
def get_macro():
    """Fetch live macro context from FRED + BLS."""
    global _macro_cache
    macro = fetch_macro_context()
    bls = fetch_bls_unemployment()
    _macro_cache = {**macro, "unemployment": bls}
    return _macro_cache


@app.get("/geo")
def get_geo():
    """
    Fetch state-level risk context from BLS, FDIC, and CFPB.
    Powers the compliance risk map on the frontend.
    """
    return fetch_geo_risk_context()


@app.post("/agent/model")
def set_agent_model(mode: str = "quality"):
    """Switch model: mode=fast (Haiku, ~1s/loan) or quality (Sonnet, ~3s/loan)."""
    set_model(mode)
    return {"mode": mode, "model": "claude-haiku-4-5-20251001" if mode == "fast" else "claude-sonnet-4-6"}


@app.post("/batch/run")
def run_batch():
    """Process all loan applications through the compliance agent."""
    global _batch_results, _macro_cache
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"

    # Tag this batch run in Overmind so traces are grouped correctly
    if OVERMIND_API_KEY:
        set_tag("batch_id", batch_id)
        set_tag("workflow", "compliance_batch")

    # Clear session memory so re-runs start clean
    clear_session()

    start_run(batch_id)

    if not _macro_cache:
        _macro_cache = fetch_macro_context()

    _batch_results = process_batch(LOAN_APPLICATIONS, _macro_cache)
    end_run()
    return {"batch_id": batch_id, "results": _batch_results}


@app.get("/batch/results")
def get_results():
    return {"results": _batch_results}


@app.get("/hitl/queue")
def hitl_queue():
    """Get pending HITL cases."""
    return {"queue": get_hitl_queue()}


@app.post("/hitl/decide")
def hitl_decide(body: HITLDecision):
    """Submit a human reviewer decision."""
    result = submit_human_decision(body.loan_id, body.decision, body.rationale)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/demo/reset-strategy")
def demo_reset_strategy():
    """
    Demo reset: wipe execution strategy from longitudinal memory.
    Call this before the demo to ensure the agent starts from naive sequential
    and the improvement loop plays out live in front of judges.
    """
    from agent.memory import delete, MemoryTier
    delete(MemoryTier.LONGITUDINAL, "execution_strategy")
    return {"reset": True, "message": "Execution strategy cleared — next batch starts from sequential baseline."}


@app.post("/demo/trigger-failure")
def demo_trigger_failure(loan_id: str = "LOAN-006"):
    """Demo endpoint: trigger a self-repair cycle."""
    repair = trigger_demo_failure(loan_id)
    return {"repair_event": repair}


@app.get("/observability/decisions")
def obs_decisions():
    return {"decisions": read_list(MemoryTier.SESSION, "decision_log")}


@app.get("/observability/tool-calls")
def obs_tool_calls():
    return {"tool_calls": read_list(MemoryTier.SESSION, "tool_call_log")}


@app.get("/observability/repairs")
def obs_repairs():
    return {"repairs": read_list(MemoryTier.LONGITUDINAL, "repair_log")}


@app.get("/observability/graduations")
def obs_graduations():
    return {"graduations": read_list(MemoryTier.LONGITUDINAL, "graduation_log")}


@app.get("/observability/graduated-patterns")
def obs_graduated_patterns():
    return {"patterns": read_longitudinal("graduated_patterns") or {}}


@app.post("/memory/consolidate")
def memory_consolidate():
    """
    Trigger Synix consolidation.
    Reads canonical HITL decisions from Ghost DB → Synix build → release → loads context to Aerospike.
    """
    return consolidate()


@app.get("/memory/context")
def memory_context():
    """Return the current Synix core compliance memory context."""
    ctx = get_synix_context()
    if not ctx:
        return {"context": None, "message": "No Synix release found. Run /memory/consolidate after the first batch."}
    return {"context": ctx, "chars": len(ctx)}


@app.get("/memory/search")
def memory_search(q: str, limit: int = 5):
    """Query the Synix compliance search index."""
    results = query_compliance_memory(q, limit=limit)
    return {"query": q, "results": results}


@app.get("/ghost/health")
def ghost_health():
    """Verify Ghost DB connectivity and record counts."""
    return ghost_ping()


@app.get("/ghost/audit")
def ghost_audit(limit: int = 100):
    """Durable decision audit log from Ghost DB — persists across restarts."""
    return {"decisions": ghost_decisions(limit=limit)}


@app.get("/ghost/graduated-patterns")
def ghost_graduated():
    """Graduated compliance patterns from Ghost DB."""
    return {"patterns": ghost_patterns()}


@app.get("/ghost/hitl-history")
def ghost_hitl_history():
    """Full HITL reviewer decision history from Ghost DB."""
    return {"decisions": ghost_hitl()}


@app.get("/observability/execution-strategy")
def obs_execution_strategy():
    """Return the agent's learned execution strategy and performance history."""
    from agent.memory import read_longitudinal
    strategy = read_longitudinal("execution_strategy") or {}
    return {"strategy": strategy}


@app.get("/observability/summary")
def obs_summary():
    decisions = read_list(MemoryTier.SESSION, "decision_log")
    repairs = read_list(MemoryTier.LONGITUDINAL, "repair_log")
    graduations = read_list(MemoryTier.LONGITUDINAL, "graduation_log")
    hitl = get_hitl_queue()

    total = len(decisions)
    escalated = sum(1 for d in decisions if d.get("escalated_to_hitl"))
    avg_confidence = (
        sum(d.get("confidence", 0) for d in decisions) / total if total else 0
    )

    return {
        "total_reviewed": total,
        "escalated_to_hitl": escalated,
        "auto_resolved": total - escalated,
        "avg_confidence": round(avg_confidence, 3),
        "self_repairs": len(repairs),
        "hitl_graduations": len(graduations),
        "pending_hitl": sum(1 for c in hitl if c.get("status") == "pending"),
    }
