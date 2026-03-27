# Deep Agents Hackathon — Project Plan
**Project:** Community Bank Compliance Agent with Observability, Self-Repair, and HITL Graduation
**Solo builder | Time budget: 4 hours**

---

## Elevator Pitch

An autonomous compliance agent for community banks that reviews loan applications against Fair Lending, QM, and HMDA rules — in real time, against live data. The agent doesn't just flag violations: it traces every decision, repairs its own errors, learns from human reviewer rationale, and graduates recurring HITL decisions to automated ones. The WOW moment is watching a compliance decision move from "requires human" to "automated" with a full audit trail of why.

---

## The Demo Arc (design this first, build backward)

1. **Live data pull** — Agent ingests current 30yr mortgage rates from FRED API and regional unemployment from BLS, contextualizing today's lending risk environment
2. **Batch review** — Agent processes 10 loan applications, flagging compliance issues with full reasoning traces
3. **HITL escalation** — 2-3 borderline fair lending cases surface for human review. Reviewer provides rationale and decision
4. **Agent learns** — Agent updates its confidence model based on rationale. Similar future cases now auto-resolve
5. **Self-repair moment** — Deliberately trigger a retrieval failure or rule contradiction. Agent detects it, logs root cause, remediates, documents what changed
6. **Observability dashboard** — Show the full trace: every tool call, decision, confidence score, memory tier, HITL graduation log

**The line for judges:** *"This agent didn't just run — it got smarter while it ran, and it can prove it."*

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│                                                          │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ Data Ingest │   │  Compliance  │   │ Observability│ │
│  │   Agent     │──▶│    Agent     │──▶│    Layer     │ │
│  │ (FRED/BLS)  │   │ (rule engine)│   │  (MLflow)    │ │
│  └─────────────┘   └──────┬───────┘   └──────────────┘ │
│                           │                              │
│                    ┌──────▼───────┐                      │
│                    │ Memory Layer │                      │
│                    │  (Synix-     │                      │
│                    │  inspired)   │                      │
│                    │  Aerospike   │                      │
│                    └──────┬───────┘                      │
│                           │                              │
│                    ┌──────▼───────┐                      │
│                    │ HITL Gateway │                      │
│                    │ + Graduation │                      │
│                    │    Engine    │                      │
│                    └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
         │                                      │
         ▼                                      ▼
  React/TS Frontend                      Ghost DB (agent state)
  Observability Dashboard                Airbyte (data pipelines)
```

---

## Memory Layer — Synix-Inspired Tiers

| Tier | Contents | Physics |
|------|----------|---------|
| **Ephemeral** | Current loan application context, active tool calls | Cleared per session |
| **Session** | All decisions made this run, rationale trail | Persists per batch |
| **Longitudinal** | HITL graduation log, learned decision patterns, officer behavior trends | Persists across runs |
| **Durable** | Compliance rules, regulatory thresholds, FRED macro context | Versioned, auditable |

Each tier has its own promotion, decay, and compression rules. Longitudinal memory is the self-improvement proof point — it's what lets you show the agent getting smarter.

---

## HITL Graduation Engine

The core intellectual differentiator. Logic:

1. Every HITL escalation is logged with: `{case_fingerprint, human_decision, human_rationale, confidence_at_escalation}`
2. Cases are clustered by fingerprint similarity (DTI range, race flag, officer, loan type)
3. When a cluster accumulates N consistent human decisions with similar rationale → case type is **graduated** to automated
4. Graduated cases still get logged and are periodically audited (never fully dark)
5. Dashboard shows: cases pending graduation, cases recently graduated, cases demoted back to HITL

**Sticky HITL** (never graduates): Novel fact patterns, regulatory ambiguity, cases where human rationale was inconsistent across reviewers

**Replaceable HITL** (graduates): Borderline DTI with consistent officer rationale, standard incomplete application resolutions

---

## Self-Repair Loop

Follows the WuiGo s9 pattern:

1. **Detect** — Agent monitors its own tool call results for anomalies (empty returns, contradictory rule matches, confidence below threshold)
2. **Triage** — Classify failure: retrieval failure / rule contradiction / data quality / context overflow
3. **Remediate** — Retry with adjusted context, fallback to durable memory tier, or escalate to HITL
4. **Document** — Write a structured repair log: `{failure_type, hypothesis, action_taken, resolution, added_to_memory}`
5. **Close loop** — Repair log feeds longitudinal memory so the same failure type is handled faster next time

---

## Sponsor Tool Integration

| Tool | Role in Project |
|------|----------------|
| **AWS (Bedrock)** | Primary LLM inference for compliance agent |
| **Kiro** | Use for spec-mode planning during build hour |
| **Aerospike** | Longitudinal memory store — sub-ms reads for HITL graduation lookups |
| **Ghost DB** | Agent session state, application queue |
| **Airbyte** | Pipeline from FRED/BLS API → compliance agent context |
| **TrueFoundry** | Deploy and observe agent in production, guardrails |
| **Overmind** | Continuous prompt optimization as agent runs |
| **Macroscope** | Code review during build (meta: use the sponsor's tool on your own code) |
| **Auth0** | Secure the HITL reviewer interface |
| **Bland AI** | Stretch: voice summary of compliance batch results |

---

## Live Data Sources

| Source | Data | API |
|--------|------|-----|
| **FRED** | 30yr mortgage rate (MORTGAGE30US), Fed Funds Rate (FEDFUNDS) | `api.stlouisfed.org/fred` — free, no auth for demo key |
| **FDIC** | Bank institution data, enforcement actions | `banks.data.fdic.gov` — fully open |
| **CFPB** | Consumer complaint database | `api.consumerfinance.gov` — fully open |
| **BLS** | Regional unemployment rates | `api.bls.gov` — free registration key |

**Get API keys before hackathon:** FRED (free at fred.stlouisfed.org), BLS (free registration)

### Fallback
Pre-seeded synthetic HMDA dataset (300 applications, engineered edge cases) if any live API fails during demo. Agent should prefer live data but degrade gracefully — narrate this as a feature.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python + FastAPI |
| Agent framework | Claude Agent SDK (direct, no LangChain) |
| Frontend | React + TypeScript |
| Observability | MLflow (open source, self-hosted) |
| Real-time DB | Aerospike |
| Session state | Ghost DB |
| Data pipeline | Airbyte |
| Auth | Auth0 |
| Deployment | TrueFoundry |
| LLM | AWS Bedrock (Claude) |

---

## Time Budget

| Phase | Time | What gets built |
|-------|------|----------------|
| **Plan** | 0:00 – 1:00 | Finalize architecture, set up repos, get API keys, Kiro spec mode for scaffolding |
| **Build** | 1:00 – 2:45 | Core agent loop → compliance rules → memory tiers → HITL gateway → observability hooks → frontend skeleton |
| **Test** | 2:45 – 3:20 | Run full demo arc end-to-end, fix critical breaks only |
| **Demo + Submit** | 3:20 – 4:00 | Record demo video, write Devpost, push to GitHub |

### Build Priority Order (if time runs short, cut from the bottom)
1. ✅ Compliance agent with rule engine + live FRED data pull
2. ✅ Observability trace on every decision
3. ✅ HITL escalation UI (2-3 cases, human inputs rationale)
4. ✅ HITL graduation engine (show one case graduating)
5. ✅ Self-repair demo (trigger one failure, show recovery)
6. ✅ Synix memory tier visualization on dashboard
7. ⚡ Aerospike integration (can substitute Redis if tight)
8. ⚡ Airbyte pipeline (can do direct API call if tight)
9. ⚡ Bland AI voice summary (pure stretch)

---

## The Pitch Structure (3 minutes — strict)

1. **(0:00–0:20)** Hook — "Community banks have the same compliance burden as JP Morgan with 2% of the staff. This agent is their compliance team."
2. **(0:20–1:00)** Live demo — agent pulls real FRED mortgage rate data, processes loan applications, flags violations with full reasoning trace visible
3. **(1:00–1:40)** HITL + graduation — surface a fair lending flag, reviewer inputs rationale, show a previously-learned case auto-resolve without human
4. **(1:40–2:20)** Self-repair — trigger a failure, show detect → remediate → document in real time
5. **(2:20–2:50)** Observability dashboard — longitudinal memory log, graduation history, confidence trend
6. **(2:50–3:00)** Close — "This agent didn't just run. It got smarter while it ran. And it can prove it."

> ⚠️ 3 minutes is unforgiving. Every screen transition must be pre-loaded. No typing during demo. Pre-seed the HITL queue with 2 ready cases.

---

## What Makes This Win

- **Real data** — live FRED/FDIC API calls during demo
- **Self-improvement is demonstrable** — graduation log is visual, timestamped, auditable
- **Observability is the feature** — not bolted on, it IS the product
- **Sponsor integration is genuine** — Aerospike for memory speed, Airbyte for pipelines, TrueFoundry for deployment, Overmind for optimization
- **The HITL graduation concept is novel** — judges from Overmind and TrueFoundry will recognize this is architecturally serious
- **Solo build signals** — one person shipping this is itself impressive

---

## Pre-Hackathon Checklist

- [ ] Register for FRED API key (fred.stlouisfed.org)
- [ ] Register for BLS API key (bls.gov/developers)
- [ ] Set up GitHub repo with basic FastAPI skeleton
- [ ] Install: `anthropic`, `mlflow`, `fastapi`, `pandas`, `requests`, `aerospike-client`
- [ ] Sign up for Ghost DB, TrueFoundry, Overmind free tiers
- [ ] Download synthetic HMDA fallback dataset (generated in this session)
- [ ] Have Auth0 tenant ready
- [ ] Read Aerospike Python client quickstart
- [ ] Kiro: install and run spec mode on architecture doc

---

## Key Concepts to Reference in Pitch

- **Synix LENS framework** — layered memory with distinct physics per tier
- **WuiGo s9 self-healing pattern** — production failure → sandboxed reproduction → remediation → dataset integration
- **HITL graduation** — sticky vs. replaceable human-in-the-loop classification
- **Jevons capture** — agent efficiency gains accrue to the institution, not get competed away (relevant if asked about business model)
- **Context engineering** — the challenge brief's own language, use it back at them
