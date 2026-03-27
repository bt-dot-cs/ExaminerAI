"""
Synix memory pipeline for the compliance agent.

Architecture:
  Source: rules/         → 5 regulatory source documents
  Source: hitl_decisions/ → HITL decision exports (written after each batch)

  MapSynthesis:  rule_summaries    — each rule doc → structured agent-queryable summary
  FoldSynthesis: hitl_patterns     — HITL decision files, accumulated sequentially
  ReduceSynthesis: core_memory     — rule summaries + learned patterns → single context doc

  SearchSurface: compliance_search — FTS + semantic search over rule summaries + core memory
  FlatFile: context                — context.md loaded into Aerospike durable tier at runtime

Run from this directory:
    synix build
    synix release local

The released context.md is loaded into Aerospike by agent/synix_consolidation.py.
"""
from pathlib import Path

from synix import Pipeline, Source, SearchSurface, FlatFile
from synix.ext.map_synthesis import MapSynthesis
from synix.ext.fold_synthesis import FoldSynthesis
from synix.ext.reduce_synthesis import ReduceSynthesis

HERE = Path(__file__).parent

# ── Prompts ───────────────────────────────────────────────────────────────────

RULE_SUMMARY_PROMPT = """\
You are a compliance AI assistant. Given this regulatory source document, extract a \
structured compliance summary that an autonomous agent can query at decision time.

Output the following sections:
1. REGULATION: Name and governing statute
2. KEY_THRESHOLDS: All numeric limits, rates, and cutoffs (exact values, not ranges)
3. TRIGGER_CONDITIONS: The precise conditions under which the agent must flag this rule
4. AGENT_DECISION_LOGIC: If/then logic the agent should apply (use exact field names: \
   dti, credit_score, loan_amount, ltv, race, loan_type, purpose)
5. ESCALATE_CONDITIONS: When the agent must escalate to a human reviewer (cannot auto-decide)
6. DOCUMENTATION_REQUIRED: What must be present in the loan file for compliance

Source document:
{content}
"""

HITL_FOLD_PROMPT = """\
You are accumulating learned compliance decision patterns from human reviewer decisions. \
Each input is a batch of HITL decisions from one session.

Current accumulated patterns:
{accumulated}

New HITL decision batch:
{content}

Update the accumulated patterns to reflect this new batch. Maintain this structure:

## LEARNED PATTERNS
For each distinct case fingerprint, record:
- Case type (DTI bucket, credit bucket, loan type, protected class flag, purpose)
- Human decision (APPROVE / DECLINE)
- Consistent rationale theme (if present)
- Decision count
- Status: APPROACHING_GRADUATION (2 consistent) | GRADUATED (3+ consistent) | INCONSISTENT

## GRADUATION CANDIDATES
List fingerprints with 3+ consistent decisions that are ready for automated resolution.

## OPEN QUESTIONS
Fingerprints where human rationale has been inconsistent — these must remain HITL permanently.

## LAST UPDATED
Timestamp and session count.
"""

CORE_MEMORY_PROMPT = """\
You are synthesizing a CORE COMPLIANCE MEMORY document for an autonomous compliance agent. \
This document is injected into the agent's reasoning at decision time.

Inputs provided:
- Rule summaries: structured knowledge for each regulation
- Learned HITL patterns: what human reviewers have taught the agent

Produce the CORE COMPLIANCE MEMORY document with these sections:

## ACTIVE RULES SUMMARY
For each rule: threshold, trigger, escalation condition — one line each.

## GRADUATED PATTERNS (agent may auto-resolve)
List each graduated case type with its decision and the rationale basis. \
Include fingerprint key (dti_bucket, credit_bucket, loan_type, protected_class, purpose).

## APPROACHING GRADUATION (2 consistent decisions — watch list)
These cases are nearly automated. Agent should note when a new case matches.

## STICKY HITL (never auto-resolve)
Case types where human reviewers have been inconsistent or where novel fact patterns appear.

## DECISION GUIDANCE FOR BORDERLINE CASES
Synthesize the reviewer behavior patterns into practical guidance for the agent:
- What compensating factors do reviewers consistently accept?
- What rationale recurs in APPROVE decisions for borderline DTI?
- What triggers a DECLINE even within the QM threshold?

## MEMORY VERSION
Build number and count of HITL decisions incorporated.
"""

# ── Pipeline definition ────────────────────────────────────────────────────────

pipeline = Pipeline(
    name="compliance-memory",
    source_dir=str(HERE / "sources"),
    build_dir=str(HERE / ".synix"),
    llm_config={
        "model": "claude-3-5-haiku-20241022",
        "temperature": 0.1,
        "max_tokens": 1500,
    },
    concurrency=3,
    layers=[
        Source(
            name="rules",
            source_dir=str(HERE / "sources" / "rules"),
        ),
        Source(
            name="hitl_decisions",
            source_dir=str(HERE / "sources" / "hitl_decisions"),
        ),
        MapSynthesis(
            name="rule_summaries",
            depends_on=["rules"],
            prompt=RULE_SUMMARY_PROMPT,
        ),
        FoldSynthesis(
            name="hitl_patterns",
            depends_on=["hitl_decisions"],
            prompt=HITL_FOLD_PROMPT,
        ),
        ReduceSynthesis(
            name="core_memory",
            depends_on=["rule_summaries", "hitl_patterns"],
            prompt=CORE_MEMORY_PROMPT,
        ),
    ],
    surfaces=[
        SearchSurface(
            name="compliance_search",
            depends_on=["rule_summaries", "core_memory"],
        ),
    ],
    projections=[
        FlatFile(
            name="context",
            depends_on=["core_memory"],
        ),
    ],
)
