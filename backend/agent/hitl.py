"""
HITL Gateway + Graduation Engine.
Manages escalation queue, human decisions, and pattern-based graduation.
"""
import time
import hashlib
import json
from agent.memory import (
    append_list, read_list, write_longitudinal, read_longitudinal, MemoryTier
)
from agent.observability import log_graduation

GRADUATION_THRESHOLD = 3  # N consistent decisions to graduate a pattern


def _fingerprint(loan: dict) -> str:
    """Create a case fingerprint for clustering similar cases."""
    key = {
        "dti_bucket": round(loan["dti"] * 10) / 10,  # round to nearest 0.1
        "credit_bucket": (loan["credit_score"] // 20) * 20,  # round to nearest 20
        "loan_type": loan["loan_type"],
        "race_protected": loan["race"] not in {"White", "Not Provided"},
        "purpose": loan["purpose"],
    }
    return hashlib.md5(json.dumps(key, sort_keys=True).encode()).hexdigest()[:8]


def escalate_to_hitl(loan: dict, findings: list, confidence: float) -> dict:
    """Add a case to the HITL queue — deduplicates by loan_id."""
    fingerprint = _fingerprint(loan)

    # Deduplicate: if this loan_id is already in the queue, update in place
    existing = get_hitl_queue()
    for case in existing:
        if case["loan_id"] == loan["id"]:
            return case  # already queued, don't add again

    item = {
        "loan_id": loan["id"],
        "loan": loan,
        "findings": findings,
        "confidence": confidence,
        "fingerprint": fingerprint,
        "escalated_at": time.time(),
        "status": "pending",
        "human_decision": None,
        "human_rationale": None,
    }
    append_list(MemoryTier.SESSION, "hitl_queue", item)
    return item


def get_hitl_queue() -> list:
    return read_list(MemoryTier.SESSION, "hitl_queue")


def submit_human_decision(loan_id: str, decision: str, rationale: str) -> dict:
    """Record a human reviewer's decision and check for graduation."""
    queue = get_hitl_queue()
    case = next((c for c in queue if c["loan_id"] == loan_id), None)
    if not case:
        return {"error": "Case not found"}

    case["human_decision"] = decision
    case["human_rationale"] = rationale
    case["reviewed_at"] = time.time()
    case["status"] = "reviewed"

    # Store in longitudinal memory for graduation analysis (Aerospike)
    append_list(MemoryTier.LONGITUDINAL, "hitl_decisions", {
        "fingerprint": case["fingerprint"],
        "decision": decision,
        "rationale": rationale,
        "loan_id": loan_id,
        "timestamp": time.time(),
    })

    # Durable HITL record (Ghost DB)
    try:
        from agent.ghost_store import write_hitl_decision
        write_hitl_decision(loan_id, case["fingerprint"], decision, rationale)
    except Exception:
        pass

    # Check graduation
    graduation = _check_graduation(case["fingerprint"])
    return {"case": case, "graduation": graduation}


def _check_graduation(fingerprint: str) -> dict | None:
    """Check if a fingerprint has enough consistent decisions to graduate."""
    all_decisions = read_list(MemoryTier.LONGITUDINAL, "hitl_decisions", limit=500)
    matching = [d for d in all_decisions if d["fingerprint"] == fingerprint]

    if len(matching) < GRADUATION_THRESHOLD:
        return None

    # Check consistency — all same decision
    decisions = [d["decision"] for d in matching[-GRADUATION_THRESHOLD:]]
    if len(set(decisions)) == 1:
        pattern = f"fingerprint:{fingerprint} → always '{decisions[0]}'"
        event = log_graduation(fingerprint, pattern, len(matching))

        # Write to longitudinal as an automated rule (Aerospike — fast lookup)
        graduated = read_longitudinal("graduated_patterns") or {}
        graduated[fingerprint] = {
            "decision": decisions[0],
            "pattern": pattern,
            "n_decisions": len(matching),
            "graduated_at": time.time(),
        }
        write_longitudinal("graduated_patterns", graduated)

        # Persist graduation to Ghost DB (survives Aerospike restart)
        try:
            from agent.ghost_store import upsert_graduated_pattern
            upsert_graduated_pattern(fingerprint, decisions[0], pattern, len(matching))
        except Exception:
            pass

        return event

    return None


def check_auto_resolve(loan: dict) -> dict | None:
    """Check if this loan matches a graduated pattern — auto-resolve without HITL."""
    fingerprint = _fingerprint(loan)
    graduated = read_longitudinal("graduated_patterns") or {}
    if fingerprint in graduated:
        return graduated[fingerprint]
    return None
