"""
Observability layer — traces every tool call, decision, and confidence score.
MLflow is used for experiment tracking. TrueFoundry swap-in: add TrueFoundry SDK calls alongside.
"""
import time
import uuid
import mlflow
from agent.memory import append_list, MemoryTier

EXPERIMENT_NAME = "compliance-agent"

_run_id = None


def start_run(batch_id: str):
    global _run_id
    mlflow.set_experiment(EXPERIMENT_NAME)
    run = mlflow.start_run(run_name=batch_id)
    _run_id = run.info.run_id
    return _run_id


def end_run():
    mlflow.end_run()


def log_decision(loan_id: str, decision: str, confidence: float, findings: list, escalated: bool):
    """Log a compliance decision to MLflow and session memory."""
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "loan_id": loan_id,
        "decision": decision,
        "confidence": confidence,
        "findings": findings,
        "escalated_to_hitl": escalated,
    }
    # MLflow metrics
    mlflow.log_metric(f"confidence_{loan_id}", confidence)
    mlflow.log_metric("escalation_rate", 1 if escalated else 0)

    # Session memory trace (Aerospike — hot path)
    append_list(MemoryTier.SESSION, "decision_log", event)

    # Durable audit trail (Ghost DB — survives restarts)
    try:
        from agent.ghost_store import write_decision
        write_decision(
            event_id=event["event_id"],
            loan_id=loan_id,
            decision=decision,
            confidence=confidence,
            findings=findings,
            escalated=escalated,
        )
    except Exception:
        pass  # Ghost write failure never blocks the hot path

    return event


def log_tool_call(tool_name: str, inputs: dict, outputs: dict, duration_ms: float):
    """Trace every tool call."""
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "tool": tool_name,
        "inputs": inputs,
        "outputs": outputs,
        "duration_ms": duration_ms,
    }
    append_list(MemoryTier.SESSION, "tool_call_log", event)
    mlflow.log_metric(f"tool_{tool_name}_ms", duration_ms)
    return event


def _safe_log_metric(key: str, value: float):
    """Log to MLflow only if a run is active."""
    try:
        if mlflow.active_run():
            mlflow.log_metric(key, value)
    except Exception:
        pass


def log_repair(failure_type: str, hypothesis: str, action_taken: str, resolution: str):
    """Log a self-repair event to longitudinal memory."""
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "failure_type": failure_type,
        "hypothesis": hypothesis,
        "action_taken": action_taken,
        "resolution": resolution,
    }
    append_list(MemoryTier.LONGITUDINAL, "repair_log", event)
    _safe_log_metric("self_repair_triggered", 1)
    return event


def log_graduation(case_fingerprint: str, pattern: str, n_consistent: int):
    """Log a HITL graduation event."""
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "case_fingerprint": case_fingerprint,
        "pattern": pattern,
        "n_consistent_decisions": n_consistent,
        "graduated_at": time.time(),
    }
    append_list(MemoryTier.LONGITUDINAL, "graduation_log", event)
    _safe_log_metric("hitl_graduations", 1)
    return event
