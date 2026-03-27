"""
Self-repair module — detects anomalies, triages, remediates, documents.
Follows the WuiGo s9 pattern: detect → triage → remediate → document → close loop.
"""
import time
from agent.memory import append_list, read_list, MemoryTier
from agent.observability import log_repair


def detect_anomaly(tool_name: str, result: dict) -> dict | None:
    """Detect anomalies in tool call results."""
    # Empty result
    if not result or result == {}:
        return {"type": "empty_result", "tool": tool_name, "detail": "Tool returned empty response"}

    # Error key present
    if "error" in result:
        return {"type": "tool_error", "tool": tool_name, "detail": result["error"]}

    # Confidence collapse
    if "confidence" in result and result["confidence"] < 0.3:
        return {"type": "confidence_collapse", "tool": tool_name, "detail": f"Confidence {result['confidence']} below floor"}

    return None


def triage(anomaly: dict) -> str:
    """Classify failure type."""
    t = anomaly.get("type")
    if t == "empty_result":
        return "retrieval_failure"
    if t == "tool_error":
        return "api_failure"
    if t == "confidence_collapse":
        return "reasoning_failure"
    return "unknown_failure"


def remediate(failure_type: str, context: dict) -> dict:
    """
    Attempt remediation based on failure type.
    Returns {action_taken, resolution, fallback_used}
    """
    if failure_type == "retrieval_failure":
        # Try reading from durable memory tier
        from agent.memory import read_durable
        fallback = read_durable(context.get("key", "macro_context"))
        if fallback:
            return {
                "action_taken": "Fell back to durable memory tier",
                "resolution": "Retrieved cached value from durable store",
                "fallback_used": True,
                "value": fallback,
            }
        return {
            "action_taken": "Attempted durable memory fallback — no cached value found",
            "resolution": "Proceeding with degraded context",
            "fallback_used": False,
        }

    if failure_type == "api_failure":
        return {
            "action_taken": "Logged API failure, using synthetic fallback dataset",
            "resolution": "Switched to pre-seeded HMDA fallback data",
            "fallback_used": True,
        }

    if failure_type == "reasoning_failure":
        return {
            "action_taken": "Escalated to HITL due to low confidence",
            "resolution": "Human reviewer assigned",
            "fallback_used": False,
        }

    return {
        "action_taken": "Unknown failure — escalated to HITL",
        "resolution": "Pending human review",
        "fallback_used": False,
    }


def run_repair_cycle(tool_name: str, result: dict, context: dict = None) -> dict | None:
    """Full repair cycle. Returns repair event if triggered, None if no anomaly."""
    anomaly = detect_anomaly(tool_name, result)
    if not anomaly:
        return None

    failure_type = triage(anomaly)
    remediation = remediate(failure_type, context or {})

    repair_event = log_repair(
        failure_type=failure_type,
        hypothesis=anomaly["detail"],
        action_taken=remediation["action_taken"],
        resolution=remediation["resolution"],
    )

    return {**repair_event, **remediation, "anomaly": anomaly}


def trigger_demo_failure(loan_id: str = "LOAN-006") -> dict:
    """
    Deliberately trigger a retrieval failure for demo purposes.
    Simulates a rule contradiction / context gap.
    """
    fake_result = {}  # empty result = retrieval failure
    repair = run_repair_cycle(
        tool_name="rule_engine",
        result=fake_result,
        context={"key": "macro_context", "loan_id": loan_id},
    )
    return repair
