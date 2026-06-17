# ExaminerAI

Autonomous compliance agent for community banks that reviews mortgage loan applications against Fair Lending, QM, and HMDA regulations in real time.

Live macro data from the FRED and BLS APIs dynamically calibrates risk thresholds so every decision reflects current market conditions. All decisions are fully traced and auditable.

---

## What It Does

- Evaluates loan applications against five compliance rule sets: QM DTI, LTV, Fair Lending, HMDA, and Rate Spread
- Ingests live mortgage rate, federal funds rate, and unemployment data to set dynamic thresholds
- Escalates low-confidence or Fair Lending-flagged decisions to a human reviewer (HITL queue)
- Graduates recurring HITL patterns into auto-resolution rules stored in Aerospike
- Compiles institutional compliance memory via Synix, injected into each Claude prompt as structured context
- Logs every decision to Ghost DB for audit-grade traceability
- Self-repairs on empty returns, contradictions, and low-confidence signals

---

## Architecture

```
External APIs (FRED, BLS)
        |
        v
FastAPI backend (main.py)
        |
        v
compliance_agent.py
  1. Auto-resolve: graduated patterns (Aerospike LONGITUDINAL, sub-ms)
  2. Rule engine: QM / LTV / Fair Lending / HMDA / Rate Spread
  3. Synix context injection: compliance memory -> Claude prompt
  4. Claude decision: claude-haiku-4-5 (fast) or claude-sonnet-4-6 (quality)
  5. Escalation: confidence < 0.70 or Fair Lending flag -> HITL queue
  6. Decision log: Aerospike SESSION + Ghost DB audit trail
        |
   +----+-----+
   v          v
hitl.py   self_repair.py
HITL      Detect -> Triage -> Remediate -> Document
queue
```

Full system diagram: [architecture.md](architecture.md)

---

## Stack

| Layer | Technology |
|-------|-----------|
| LLM | Anthropic Claude (Haiku 4.5 / Sonnet 4.6) |
| Backend | FastAPI + Python 3.11+ |
| Frontend | React + TypeScript + Vite |
| Hot memory | Aerospike (EPHEMERAL / SESSION / LONGITUDINAL tiers) |
| Durable audit store | Ghost DB |
| Memory compiler | Synix |
| Observability | Overmind SDK + MLflow |
| Live data | FRED API (rates), BLS API (unemployment) |

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Aerospike running locally (default: `localhost:3000`, namespace `test`) — see [aerospike.conf](aerospike.conf)
- Ghost DB instance (optional; startup skips gracefully if unreachable)

### 1. Clone

```bash
git clone https://github.com/bt-dot-cs/ExaminerAI.git
cd ExaminerAI
```

### 2. Environment variables

```bash
cp .env.example backend/.env
# fill in your keys
```

### 3. Backend

```bash
cd backend
bash start.sh        # installs deps + starts uvicorn on :8000
```

Or manually:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev          # Vite dev server on :5173
```

---

## Environment Variables

See [.env.example](.env.example) for the full list.

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `FRED_API_KEY` | Yes | FRED (Federal Reserve) API key — [register free](https://fred.stlouisfed.org/docs/api/api_key.html) |
| `BLS_API_KEY` | No | BLS unemployment data — public endpoint works without a key; registration raises rate limits |
| `GHOST_DB_URL` | No | Ghost DB connection URL — audit log skipped gracefully if unset |
| `OVERMIND_API_KEY` | No | Overmind observability — tracing skipped if unset |
| `AEROSPIKE_HOST` | No | Default: `localhost` |
| `AEROSPIKE_PORT` | No | Default: `3000` |
| `AEROSPIKE_NAMESPACE` | No | Default: `test` |

---

## Project Structure

```
ExaminerAI/
├── backend/
│   ├── agent/
│   │   ├── compliance_agent.py     # core pipeline
│   │   ├── ghost_store.py          # Ghost DB read/write
│   │   ├── hitl.py                 # human-in-the-loop queue
│   │   ├── memory.py               # Aerospike memory tiers
│   │   ├── observability.py        # run tracking
│   │   ├── self_repair.py          # failure detection + remediation
│   │   └── synix_consolidation.py  # compliance memory compilation
│   ├── data/
│   │   ├── live_data.py            # FRED + BLS + geo risk
│   │   └── synthetic_loans.py      # demo loan applications
│   ├── rules/                      # compliance rule definitions
│   ├── config.py                   # env var loading
│   ├── main.py                     # FastAPI app + routes
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       └── components/
├── architecture.md                 # full system diagram
└── aerospike.conf                  # local Aerospike config
```

---

## Built At

Deep Agents Hackathon — March 2026

Sponsor integrations: Aerospike · Ghost DB · Overmind · Anthropic Claude · Synix
