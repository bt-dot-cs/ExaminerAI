"""
Core compliance agent loop.
Uses Anthropic Claude for reasoning over rule results.
AWS Bedrock swap-in: replace anthropic.Anthropic() with boto3 bedrock-runtime client.
"""
import time
import asyncio
import anthropic
from concurrent.futures import ThreadPoolExecutor
from config import ANTHROPIC_API_KEY
from rules.compliance_rules import run_all_rules, RuleResult
from agent.memory import write_ephemeral, write_session, read_longitudinal, write_longitudinal, MemoryTier
from agent.observability import log_decision, log_tool_call, log_repair
from agent.hitl import escalate_to_hitl, check_auto_resolve
from agent.synix_consolidation import get_synix_context

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CONFIDENCE_ESCALATION_THRESHOLD = 0.70  # escalate if confidence below this

MODEL_FAST = "claude-haiku-4-5-20251001"   # ~1s/loan — use for full batch runs
MODEL_QUALITY = "claude-sonnet-4-6"         # ~3s/loan — use for individual reviews / demo moments
_active_model = MODEL_QUALITY               # default


def set_model(mode: str):
    """Set active model. mode = 'fast' | 'quality'"""
    global _active_model
    _active_model = MODEL_FAST if mode == "fast" else MODEL_QUALITY


def _results_to_text(results: list[RuleResult]) -> str:
    lines = []
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        lines.append(f"[{r.severity.upper()}] {r.rule}: {status} — {r.finding}")
        if r.recommendation:
            lines.append(f"  → {r.recommendation}")
    return "\n".join(lines)


def _call_claude(loan: dict, rule_results: list[RuleResult], macro: dict) -> dict:
    """Ask Claude to reason over rule results and produce a compliance decision."""
    t0 = time.time()
    rule_text = _results_to_text(rule_results)
    violations = [r for r in rule_results if not r.passed]
    warnings = [r for r in rule_results if r.passed and r.severity == "warning"]

    # Inject Synix core memory if available — learned patterns from prior HITL decisions
    synix_context = get_synix_context()
    synix_section = ""
    if synix_context:
        # Trim to avoid context overflow; core_memory is the most relevant section
        trimmed = synix_context[:3000] if len(synix_context) > 3000 else synix_context
        synix_section = f"""
COMPLIANCE MEMORY (learned from prior human reviewer decisions):
{trimmed}

"""

    prompt = f"""You are a compliance officer reviewing a mortgage loan application.
{synix_section}

MACRO CONTEXT (live data):
- 30-year mortgage rate: {macro.get('mortgage_30yr')}% (as of {macro.get('mortgage_date')})
- Fed funds rate: {macro.get('fed_funds_rate')}%

LOAN APPLICATION:
- ID: {loan['id']}
- Income: ${loan['income']:,}
- Loan Amount: ${loan['loan_amount']:,}
- DTI: {loan['dti']:.0%}
- Credit Score: {loan['credit_score']}
- Loan Type: {loan['loan_type']}
- Purpose: {loan['purpose']}
- State: {loan['property_state']}

RULE ENGINE RESULTS:
{rule_text}

Based on these results, provide:
1. DECISION: APPROVE / DECLINE / ESCALATE_TO_HUMAN
2. CONFIDENCE: 0.0-1.0
3. SUMMARY: 1-2 sentence plain-English summary of the compliance posture
4. KEY_RISK: The single most important risk factor

Respond in this exact format:
DECISION: <value>
CONFIDENCE: <value>
SUMMARY: <text>
KEY_RISK: <text>"""

    response = client.messages.create(
        model=_active_model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    duration_ms = (time.time() - t0) * 1000
    text = response.content[0].text

    # Parse response
    result = {}
    for line in text.strip().split("\n"):
        if ": " in line:
            k, v = line.split(": ", 1)
            result[k.strip()] = v.strip()

    log_tool_call("claude_compliance_review", {"loan_id": loan["id"]}, result, duration_ms)
    return result


def process_loan(loan: dict, macro: dict) -> dict:
    """Full compliance review pipeline for a single loan."""
    # Check if this pattern has been graduated (auto-resolve)
    auto = check_auto_resolve(loan)
    if auto:
        return {
            "loan_id": loan["id"],
            "decision": auto["decision"],
            "confidence": 1.0,
            "auto_resolved": True,
            "graduated_pattern": auto["pattern"],
            "escalated": False,
        }

    # Run rule engine
    t0 = time.time()
    rule_results = run_all_rules(loan, macro)
    log_tool_call("rule_engine", {"loan_id": loan["id"]}, {"n_rules": len(rule_results)}, (time.time() - t0) * 1000)

    # Store in ephemeral memory
    write_ephemeral(f"loan_{loan['id']}_rules", [
        {"rule": r.rule, "passed": r.passed, "severity": r.severity, "finding": r.finding}
        for r in rule_results
    ])

    # LLM reasoning
    try:
        llm_result = _call_claude(loan, rule_results, macro)
        decision = llm_result.get("DECISION", "ESCALATE_TO_HUMAN")
        confidence = float(llm_result.get("CONFIDENCE", 0.5))
        summary = llm_result.get("SUMMARY", "")
        key_risk = llm_result.get("KEY_RISK", "")
    except Exception as e:
        # Self-repair: LLM call failed
        repair = log_repair(
            failure_type="llm_call_failure",
            hypothesis=f"Claude API error: {str(e)}",
            action_taken="Fallback to rule-engine-only decision",
            resolution="Used rule violations to determine outcome without LLM",
        )
        violations = [r for r in rule_results if not r.passed]
        decision = "DECLINE" if violations else "APPROVE"
        confidence = 0.55
        summary = f"LLM unavailable — rule-engine fallback. {len(violations)} violation(s) found."
        key_risk = violations[0].finding if violations else "None"

    # Determine escalation
    violations = [r for r in rule_results if not r.passed]
    warnings = [r for r in rule_results if r.passed and r.severity == "warning"]
    escalate = (
        decision == "ESCALATE_TO_HUMAN"
        or confidence < CONFIDENCE_ESCALATION_THRESHOLD
        or any(r.rule == "FAIR_LENDING_DISPARATE_TREATMENT" and r.severity == "warning" for r in rule_results)
    )

    findings = [
        {"rule": r.rule, "severity": r.severity, "finding": r.finding}
        for r in rule_results if r.severity in ("violation", "warning")
    ]

    if escalate:
        escalate_to_hitl(loan, findings, confidence)

    # Log decision
    log_decision(loan["id"], decision, confidence, findings, escalate)

    # Store in session memory
    result = {
        "loan_id": loan["id"],
        "decision": decision,
        "confidence": confidence,
        "summary": summary,
        "key_risk": key_risk,
        "violations": len(violations),
        "warnings": len(warnings),
        "findings": findings,
        "escalated": escalate,
        "auto_resolved": False,
    }
    write_session(f"loan_{loan['id']}_result", result)
    return result


def process_batch(loans: list, macro: dict) -> list:
    """
    Process a full batch of loan applications.
    On first run: sequential execution, measures wall time.
    On subsequent runs: reads execution strategy from longitudinal memory.
    If prior run was slow, hypothesizes parallelization, runs experiment, confirms.
    """
    strategy = read_longitudinal("execution_strategy") or {"mode": "sequential", "runs": 0}
    run_number = strategy.get("runs", 0) + 1

    t0 = time.time()

    if strategy.get("mode") == "parallel":
        results = _process_batch_parallel(loans, macro)
    else:
        results = _process_batch_sequential(loans, macro)

    wall_time = time.time() - t0
    per_loan_ms = (wall_time / len(loans)) * 1000

    # Record this run's performance
    perf = {
        "run_number": run_number,
        "mode": strategy.get("mode", "sequential"),
        "wall_time_s": round(wall_time, 2),
        "per_loan_ms": round(per_loan_ms, 1),
        "n_loans": len(loans),
        "timestamp": time.time(),
    }

    # Self-improvement: analyse and propose next strategy
    experiment = _analyse_performance(strategy, perf)
    perf["experiment"] = experiment

    # Persist updated strategy to longitudinal memory
    new_strategy = {
        "mode": experiment.get("next_mode", strategy.get("mode", "sequential")),
        "runs": run_number,
        "last_wall_time_s": wall_time,
        "last_per_loan_ms": per_loan_ms,
        "history": (strategy.get("history") or []) + [perf],
    }
    write_longitudinal("execution_strategy", new_strategy)

    # Log as a repair/optimisation event so it shows in observability
    if experiment.get("action"):
        log_repair(
            failure_type="performance_optimisation",
            hypothesis=experiment["hypothesis"],
            action_taken=experiment["action"],
            resolution=experiment["resolution"],
        )

    return results


def _process_batch_sequential(loans: list, macro: dict) -> list:
    """Original sequential execution — one loan at a time."""
    return [process_loan(loan, macro) for loan in loans]


def _process_batch_parallel(loans: list, macro: dict) -> list:
    """Parallel execution — all loans concurrently via thread pool."""
    with ThreadPoolExecutor(max_workers=min(len(loans), 10)) as executor:
        futures = [executor.submit(process_loan, loan, macro) for loan in loans]
        # Preserve original order
        return [f.result() for f in futures]


def _analyse_performance(strategy: dict, perf: dict) -> dict:
    """
    Hypothesis engine: analyse batch performance and propose next execution strategy.
    Returns experiment dict with hypothesis, action, resolution, next_mode.
    """
    wall_time = perf["wall_time_s"]
    current_mode = strategy.get("mode", "sequential")
    run_number = perf["run_number"]

    # First run — establish baseline, propose parallelization if slow
    if run_number == 1:
        if wall_time > 20:
            return {
                "hypothesis": f"Baseline: {wall_time:.1f}s sequential for {perf['n_loans']} loans ({perf['per_loan_ms']:.0f}ms/loan). Claude API calls are I/O-bound — parallelizing should reduce wall time by ~{int((1 - 1/perf['n_loans']) * 100)}%.",
                "action": "Switching to parallel execution on next run.",
                "resolution": f"Next batch will run all {perf['n_loans']} loans concurrently. Expected time: ~{perf['per_loan_ms']/1000:.1f}s.",
                "next_mode": "parallel",
            }
        return {
            "hypothesis": f"Baseline established: {wall_time:.1f}s sequential. Within acceptable range.",
            "action": "No optimisation needed.",
            "resolution": "Maintaining sequential mode.",
            "next_mode": "sequential",
        }

    # Sequential and slow — propose parallel
    if current_mode == "sequential" and wall_time > 20:
        return {
            "hypothesis": f"Sequential execution took {wall_time:.1f}s. Claude API calls are I/O-bound — parallelizing {perf['n_loans']} concurrent calls should reduce wall time by ~{int((1 - 1/perf['n_loans']) * 100)}%.",
            "action": "Switching to parallel execution mode using ThreadPoolExecutor.",
            "resolution": f"Next batch will run all {perf['n_loans']} loans concurrently. Expected time: ~{perf['per_loan_ms']/1000:.1f}s.",
            "next_mode": "parallel",
        }

    # Parallel — confirm improvement
    if current_mode == "parallel":
        prior_time = strategy.get("last_wall_time_s", wall_time)
        improvement = ((prior_time - wall_time) / prior_time * 100) if prior_time > wall_time else 0
        return {
            "hypothesis": f"Parallel execution hypothesis confirmed." if improvement > 10 else f"Parallel execution running. Wall time: {wall_time:.1f}s.",
            "action": "Maintaining parallel execution mode.",
            "resolution": f"Wall time: {wall_time:.1f}s ({improvement:.0f}% improvement over sequential baseline)." if improvement > 10 else f"Wall time: {wall_time:.1f}s.",
            "next_mode": "parallel",
        }

    # Sequential and fast — no change needed
    return {
        "hypothesis": f"Execution time {wall_time:.1f}s is within acceptable range.",
        "action": "No optimisation needed.",
        "resolution": "Maintaining current strategy.",
        "next_mode": current_mode,
    }
