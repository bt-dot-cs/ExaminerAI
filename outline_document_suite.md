# wuigo ai observability & agent operations — outline

Each section document follows this structure:
- Problem Statement
- Architecture & Patterns
- WuiGo Implementation Notes
- Metrics & Signals
- Timing & Dependencies

---

**s1 — eval dataset construction & automated scoring**
*The foundation. Nothing else in the suite functions without this.*
Covers: EvalCase schema, five case categories, three-method scoring funnel (rule-based → LLM-as-judge → human review), pass@k and pass^k formalisms, golden traces, dataset construction and lifecycle management, hard deployment gate on critical failures.

**s1 corollary — tiered judge architecture & constraint-forward cost scaling**
*How to keep eval costs sub-linear as WuiGo scales to 50+ jurisdictions.*
Covers: per-dimension model tier routing, hardware routing for non-LLM pipeline components, per-tier calibration sets as a hard process requirement, cost estimates at 50-jurisdiction scale.

**s2 — regression detection & CI/CD**
*How every meaningful change is automatically tested and gated before production.*
Covers: three-tier trigger system, baseline management and promotion, regression classification (critical / significant / marginal / none), bootstrap confidence intervals, override mechanism as audit artifact, alert routing by severity, avoiding alert fatigue.

**s2 corollary — jurisdiction baseline architecture & GTM coordination**
*How baseline management scales across jurisdictions, and where product architecture and GTM strategy must coordinate.*
Covers: four-option baseline architecture, continuous promotion from cluster to per-jurisdiction baselines, jurisdiction taxonomy built from domain validity, pre-emptive analysis as a sales preparation tool (not a demo asset), freemium resident product strategy, GTM coordination principles.

**s3 — non-determinism in agent evals**
*How to reason about and measure the stochastic nature of LLM outputs systematically.*
Covers: NonDeterminismProfile schema, stability classification (stable / variable / unstable), four sources of variance (temperature, retrieval, context window sensitivity, prompt sensitivity), pass@k vs pass^k design principles, stability-calibrated k selection, stochastic test design, temperature strategy by query category.

**s4 — context window management**
*How to control what goes into and out of the model at every step — for cost, quality, and multi-agent readiness.*
Covers: three-tier context preparation, handle-based references for large payloads, jq/grep-style query tools, hard output limits via max_tokens, structured session state, context budget tracking.

**s5 — cost, latency & RAG metrics**
*The operational health layer: is the system fast enough, cheap enough, and actually using its own data?*
Covers: cost structure and four levers (semantic caching, query routing, context management, prompt caching), latency SLAs and per-step tracing, TTFT as a primary metric, RAGAS framework (faithfulness, answer relevancy, context precision, context recall), four RAG failure modes, chunking strategy evaluation, observability dashboard.

**s6 — root cause analysis on distributed traces**
*How to go from "something failed" to "here is exactly why and what to fix" systematically.*
Covers: QueryTrace and TraceStep schemas, trace indexing and search, five-step RCA workflow, root cause classification table, failure context correlation, structured RCA finding format, trace chaining across requests, session-level state drift detection, infrastructure log correlation, runbook schema with escalation paths.

**s7 — multi-agent tracing & cascading failures**
*How observability changes when the system becomes an orchestrated network of agents.*
Covers: coordination layer as the primary failure surface, distributed trace propagation via TraceContext, coordination event instrumentation (including simulation version match checks), cascading failure detection and amplification factor, supervisor agent evaluation, system-level vs. agent-level eval, MLflow tracing integration.

**s8 — agent security & prompt injection**
*How to make adversarial manipulation detectable, contained, and recoverable.*
Covers: WuiGo threat model (direct injection, indirect injection via retrieved content, scope boundary exploitation, skill and tool abuse, multi-agent propagation), five defense layers (input validation, prompt architecture hardening, retrieved content scanning, output validation, scope boundary enforcement), tool security via SecureToolDefinition schema, multi-agent trust levels and injection containment.

**s8 corollary — prompt refinement interface**
*A user-facing layer that improves input quality for users with varying AI and domain fluency.*
Covers: position in the pipeline (pre-validation), planner refinement mode (confidence-triggered clarification), resident refinement mode (structured guided flow), skippability and progressive disclosure, InputOrigin tagging for eval dataset, secondary security benefit of input normalization, resident aggregate query data as community preparedness signal for planners.

**s9 — self-healing & feedback loop architectures**
*How the system learns from its own failures and reduces the human burden of resolving them.*
Covers: ProductionFailure schema, four-stage feedback loop (triage, sandboxed reproduction, remediation, dataset integration), automated triage and AUTOMATABLE_FAILURE_TYPES, sandboxed reproduction as mandatory gate, prompt remediation brief with LLM-generated hypothesis, escalation brief structure, self-healing agent architecture (Factory.ai Droid pattern), human approval gate for all production changes, dataset integration as loop closure.

**master_architectural_decision_register**
*35 architectural decisions across all sections. The design logic of the system in one place.*
Covers: one decision per schema entry (what was decided, why it matters, what it enables, what it forecloses, estimated timeline), organized by section in dependency order, dependency graph, full document index.
