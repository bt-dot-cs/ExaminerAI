That's partially right but worth sharpening — the two tools play different roles and connect to Synix at different points in the pipeline. Here's the precise picture:

The Flow

Ghost DB                    Synix                    Aerospike
────────────────────        ──────────────────────   ──────────────────────
Loan application queue  →   (sources it reads)       (artifact it writes to)
HITL decision log       →   hitl_decisions/  ──────► durable: synix_context
Session state               rules/           ──────► durable: rule_summaries
                                    ↓
                            core_memory.md ─────────► durable tier (fast reads)
                                                            ↓
                                                      Agent inference
                                                      (every loan, sub-ms)
Aerospike's role: the memory substrate during inference
Aerospike is what makes Synix's compiled output usable in real time. The problem with Synix alone is that it produces static release artifacts — a context.md and search.db on disk. If you served those from Postgres or even Redis under load, you'd get latency variance that disrupts the per-loan decision loop.

Aerospike's specific contribution:

Sub-ms reads on every loan — the graduated patterns check in check_auto_resolve() runs for every single loan application. At 10 loans/batch that's fine; at 10,000 it has to be fast
Four tiers with different TTL physics — Aerospike enforces the TTL at the storage level, not in application code. Ephemeral memory actually expires. This isn't Redis — it's a proper distributed KV with predictable latency under write pressure
The durable tier is where Synix writes — context.md from each Synix release is loaded into AEROSPIKE_NAMESPACE/durable/synix_compliance_context. The agent reads from there on every Claude call, not from disk
So Aerospike isn't just a cache — it's the serving layer for everything Synix produces.

Ghost DB's role: the operational queue that feeds Synix
Ghost DB is described as a database built for agents, not humans — CLI/MCP only, no UI, forkable. In the current codebase it's not wired in yet. Here's where it actually belongs:

1. Loan application queue
Currently LOAN_APPLICATIONS is a static Python list in synthetic_loans.py. Ghost DB should own this. The agent pulls applications from Ghost DB via MCP tool call, processes them, and marks them processed. This is forkable state — you can snapshot the queue before a batch run and roll back if the run fails mid-way.

2. HITL decision log (source for Synix)
Currently HITL decisions live in Aerospike's SESSION tier. This is actually wrong placement — session tier has a 24hr TTL, and the HITL decisions are exactly what Synix needs to persist and accumulate across runs. Ghost DB should store the canonical HITL decision log. Then export_hitl_decisions() in synix_consolidation.py reads from Ghost DB, not Aerospike, when building the source files for Synix.

3. The fork capability is architecturally meaningful here
Before each Synix consolidation run, you fork the Ghost DB HITL log. If the Synix build fails or produces bad output, you roll back the fork rather than corrupting the source. This is the kind of thing that makes judges from Aerospike and Overmind take notice — you're treating memory consolidation as a transaction.

The corrected tool relationships
Tool	Role	Connects to Synix how
Ghost DB	Upstream source of truth — loan queue, HITL decisions	Its HITL log is exported to memory/sources/hitl_decisions/ before each build
Synix	Memory compiler — transforms raw sources into structured artifacts	Reads from Ghost DB exports; writes context.md
Aerospike	Serving layer — all four memory tiers during inference	Receives Synix's compiled context in durable tier; serves it sub-ms on every loan
The pipeline is linear: Ghost DB → Synix → Aerospike → Agent.

Ghost DB is the source of record. Synix is the compiler. Aerospike is the runtime.

What needs to be built to complete this
hitl.py currently writes to Aerospike SESSION tier for the HITL queue. That needs to either:

Write to Ghost DB via its MCP interface instead (correct), or
At minimum, be promoted to LONGITUDINAL tier so it survives across sessions
And synix_consolidation.py's export_hitl_decisions() should read from Ghost DB's canonical log rather than the Aerospike SESSION queue — which would currently lose decisions older than 24 hours.