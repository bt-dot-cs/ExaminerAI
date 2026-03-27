# Compliance Agent — Architecture & Workflow

---

## Full System Map

```
╔══════════════════════════════════════════════════════════════════════════╗
║                       EXTERNAL DATA SOURCES                              ║
║   FRED API        BLS API         FDIC API         CFPB API             ║
║  (rates/fed)   (unemployment)   (institutions)   (complaints)           ║
╚══════╤══════════════╤══════════════╤══════════════╤═══════════════════╝
       └──────────────┴──────────────┴──────────────┘
                              │ data/live_data.py
                              │
               ┌──────────────┴──────────────┐
               │  macro_context               │  geo_risk
               │  mortgage rate, fed funds    │  → frontend
               │  unemployment by state       │    RiskMap
               └──────────────┬──────────────┘
                              │
╔═════════════════════════════╪════════════════════════════════════════╗
║                      FastAPI (main.py)                                ║
║   /batch/run   /macro   /geo   /hitl/decide   /memory/consolidate    ║
║   /ghost/audit   /memory/context   /observability/summary            ║
╚═════════════════════════════╪════════════════════════════════════════╝
                              │
                 ┌────────────┘
                 │
        ┌────────▼────────────────────────────────────────────────┐
        │                compliance_agent.py                       │
        │                                                          │
        │  ① check_auto_resolve(loan)                             │
        │    └─ Aerospike LONGITUDINAL: graduated_patterns  ──────►─── if match → auto-decision
        │       sub-ms, runs on every loan                         │
        │                                                          │
        │  ② run_all_rules(loan, macro)  [compliance_rules.py]    │
        │    QM_DTI / LTV / FAIR_LENDING / HMDA / RATE_SPREAD     │
        │    └─ write results → Aerospike EPHEMERAL (1hr TTL)     │
        │                                                          │
        │  ③ get_synix_context()                                  │
        │    └─ Aerospike DURABLE: synix_compliance_context        │
        │       → injected into Claude prompt as COMPLIANCE MEMORY │
        │                                                          │
        │  ④ _call_claude(loan, rules, macro, synix_ctx)          │
        │    ├─ MODEL_FAST:    claude-haiku-4-5    ~1s/loan        │
        │    └─ MODEL_QUALITY: claude-sonnet-4-6   ~3s/loan        │
        │       → DECISION / CONFIDENCE / SUMMARY / KEY_RISK       │
        │                                                          │
        │  ⑤ escalation check                                     │
        │    confidence < 0.70 OR FAIR_LENDING warning             │
        │    └─ escalate_to_hitl() → Aerospike SESSION            │
        │                                                          │
        │  ⑥ log_decision() → Aerospike SESSION + MLflow          │
        └──────────────────────────────────────────────────────────┘
                 │                             │
        ┌────────┘                    ┌────────┘
        │                             │
        ▼                             ▼
┌────────────────┐          ┌──────────────────────────────┐
│ self_repair.py │          │          hitl.py              │
│                │          │                              │
│  Detect:       │          │  pending cases surface to    │
│  empty returns │          │  human reviewer via frontend │
│  contradictions│          │                              │
│  low confidence│          │  reviewer submits decision   │
│                │          │  + rationale                 │
│  Triage:       │          │         │                    │
│  retrieval /   │          │         ▼                    │
│  rule /        │          │  ┌─ Ghost DB ─────────────┐ │
│  data quality  │          │  │  hitl_decisions (canon)│ │
│                │          │  └───────────────────────┘ │
│  Remediate:    │          │  ┌─ Aerospike LONG ───────┐ │
│  retry /       │          │  │  hitl_decisions        │ │
│  fallback /    │          │  └───────────────────────┘ │
│  escalate      │          │         │                    │
│                │          │  _check_graduation()         │
│  Document:     │          │  fingerprint: N=3 consistent?│
│  Aerospike LONG│          │  ├── YES → GRADUATED         │
│  repair_log    │          │  │   ├── Aerospike LONG      │
└────────────────┘          │  │   └── Ghost DB            │
                            │  └── NO  → stays HITL        │
                            └──────────────────────────────┘
```

---

## Memory Architecture

```
        PIPELINE DIRECTION:  Ghost DB → Synix → Aerospike → Agent

╔══════════════════════════╦══════════════════════════╦══════════════════════╗
║         AEROSPIKE         ║         GHOST DB          ║        SYNIX          ║
║    hot path · sub-ms      ║   durable · audit-grade   ║   memory compiler     ║
╠══════════════════════════╬══════════════════════════╬══════════════════════╣
║                           ║                          ║                      ║
║  EPHEMERAL  (1hr TTL)     ║  decision_audit          ║  SOURCES             ║
║  └─ loan_{id}_rules       ║  every loan decision,    ║  rules/ (5 regs)     ║
║     current loan context  ║  confidence, findings,   ║  hitl_decisions/     ║
║     cleared per loan      ║  batch_id                ║  (written per batch) ║
║                           ║  ← survives restarts     ║                      ║
║  SESSION  (24hr TTL)      ║                          ║  PIPELINE            ║
║  ├─ decision_log          ║  hitl_decisions          ║  MapSynthesis        ║
║  ├─ tool_call_log         ║  ← canonical log         ║  1:1 per rule doc    ║
║  └─ hitl_queue            ║  ← feeds Synix           ║                      ║
║     active batch          ║    on consolidation       ║  FoldSynthesis       ║
║                           ║                          ║  sequential N:1      ║
║  LONGITUDINAL  (no TTL)   ║  graduated_patterns      ║  HITL sessions       ║
║  ├─ hitl_decisions        ║  ← upserted on N=3       ║  accumulated over    ║
║  ├─ repair_log            ║  ← cross-restart memory  ║  time                ║
║  ├─ graduation_log        ║    of what agent learned  ║                      ║
║  └─ graduated_patterns    ║                          ║  ReduceSynthesis     ║
║     ← auto-resolve reads  ║                          ║  N:1 rules+patterns  ║
║       here first (sub-ms) ║                          ║  → core_memory       ║
║                           ║                          ║                      ║
║  DURABLE  (no TTL)        ║                          ║  RELEASE             ║
║  └─ synix_compliance_ctx  ║                          ║  context.md          ║
║     ← Synix output        ║                          ║  → Aerospike DURABLE ║
║     ← injected into Claude║                          ║  search.db           ║
║       prompt every run    ║                          ║  → /memory/search    ║
╚══════════════════════════╩══════════════════════════╩══════════════════════╝
```

---

## Living Memory Loop (between runs)

```
  BATCH COMPLETES
       │
       ▼
  Human reviewer submits decisions  →  /hitl/decide
       │
       ├──► Ghost DB: hitl_decisions  (canonical, survives restarts)
       └──► Aerospike LONG: hitl_decisions  (fast in-session reads)
                    │
             _check_graduation()
             same fingerprint, N=3 consistent decisions?
                    │
         ┌──────────┴──────────┐
         │ YES                 │ NO
         ▼                     ▼
   GRADUATED              INCONSISTENT
   ├─ Aerospike LONG      sticky HITL
   └─ Ghost DB            never graduates
         │
         ▼
  POST /memory/consolidate
         │
  ① read_hitl_decisions() ← Ghost DB (source of truth)
         │
  ② export_hitl_decisions()
     → writes session_{ts}.md to memory/sources/hitl_decisions/
         │
  ③ synix build  (incremental)
     ├─ rule_summaries:  CACHED    (no LLM calls, rules unchanged)
     ├─ hitl_patterns:   REBUILD   (new session file)
     └─ core_memory:     REBUILD   (downstream of hitl_patterns)
         │
  ④ synix release local
     → .synix/releases/local/context.md
     → .synix/releases/local/search.db
         │
  ⑤ load_context_to_durable()
     → Aerospike DURABLE: synix_compliance_context
         │
         ▼
  NEXT BATCH RUN
  get_synix_context() reads Aerospike DURABLE (sub-ms)
  Claude prompt now contains:
    - graduated patterns (agent can auto-resolve these)
    - reviewer guidance (what rationale recurs in APPROVE/DECLINE)
    - approaching graduation watch list
```

---

## Synix Pipeline

```
  memory/sources/rules/                memory/sources/hitl_decisions/
  ├─ fair_lending.md                   ├─ session_20260327_1400.md
  ├─ qualified_mortgage.md             ├─ session_20260327_1600.md
  ├─ hmda.md                           └─ session_20260328_0900.md
  ├─ ltv_limits.md
  └─ hoepa.md
           │  (1:1)                              │  (sequential)
           ▼                                     ▼
  ┌─────────────────┐                  ┌──────────────────────┐
  │  MapSynthesis   │                  │   FoldSynthesis       │
  │  rule_summaries │                  │   hitl_patterns       │
  │                 │                  │                      │
  │  Each rule doc  │                  │   s1 → state_1       │
  │  → thresholds,  │                  │   state_1 + s2        │
  │    triggers,    │                  │     → state_2         │
  │    agent logic, │                  │   state_2 + s3        │
  │    escalation   │                  │     → state_3 ← NOW  │
  │                 │                  │                      │
  │  5 artifacts    │                  │  GRADUATED /         │
  │  (cached after  │                  │  APPROACHING /       │
  │   first build)  │                  │  INCONSISTENT        │
  └────────┬────────┘                  └──────────┬───────────┘
           └──────────────┬────────────────────────┘
                          │  (N:1)
                          ▼
               ┌────────────────────┐
               │   ReduceSynthesis  │
               │   core_memory      │
               │                    │
               │   Active Rules     │
               │   Graduated (auto) │
               │   Approaching grad │
               │   Sticky HITL      │
               │   Decision Guidance│
               └─────────┬──────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
  ┌──────────────────┐     ┌────────────────────┐
  │  context.md      │     │  search.db          │
  │  → Aerospike     │     │  FTS5 + semantic     │
  │    DURABLE       │     │  → /memory/search    │
  │  → Claude prompt │     │  → LoanDetail panel  │
  └──────────────────┘     └────────────────────┘
```

---

## Frontend Surface

```
  React / TypeScript
  ├─ MacroBar          GET /macro                  live rates (FRED + BLS)
  ├─ RiskMap           GET /geo                    state-level risk map
  ├─ BatchTable        POST /batch/run             trigger agent run
  │                    GET  /batch/results          loan decisions
  ├─ HITLPanel         GET  /hitl/queue             pending escalations
  │                    POST /hitl/decide            submit reviewer decision
  │                    POST /memory/consolidate     trigger Synix rebuild
  ├─ ObservabilityPanel GET /observability/summary
  │                    GET  /ghost/audit            durable decision log
  │                    GET  /ghost/graduated-patterns
  │                    GET  /memory/context         Synix core memory (before/after)
  └─ LoanDetail        GET  /memory/search?q=       rule lookup from Synix index
```

---

## Sponsor Tool Map

```
  External APIs ──► Airbyte ──────────────────────────────► macro_context
  Claude (Anthropic / AWS Bedrock) ◄───── compliance_agent (every loan)
  MLflow ◄──────────────────────────────── log_decision, log_tool_call
  Overmind ◄────────────────────────────── Claude prompt (continuous optimization)
  TrueFoundry ──────────────────────────── deployment + guardrails
  Auth0 ────────────────────────────────── HITL reviewer interface + API security
  Bland AI (stretch) ◄──────────────────── batch summary → Norm voice output
```
