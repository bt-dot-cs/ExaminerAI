const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`)
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`)
  return r.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`POST ${path} → ${r.status}`)
  return r.json()
}

export const api = {
  getMacro: () => get<MacroContext>('/macro'),
  getGeo: () => get<Record<string, GeoState>>('/geo'),
  runBatch: () => post<BatchResult>('/batch/run'),
  getResults: () => get<BatchResult>('/batch/results'),
  getHITLQueue: () => get<{ queue: HITLCase[] }>('/hitl/queue'),
  submitDecision: (loan_id: string, decision: string, rationale: string) =>
    post('/hitl/decide', { loan_id, decision, rationale }),
  triggerFailure: () => post<{ repair_event: RepairEvent }>('/demo/trigger-failure'),
  getDecisions: () => get<{ decisions: DecisionEvent[] }>('/observability/decisions'),
  getToolCalls: () => get<{ tool_calls: ToolCallEvent[] }>('/observability/tool-calls'),
  getRepairs: () => get<{ repairs: RepairEvent[] }>('/observability/repairs'),
  getGraduations: () => get<{ graduations: GraduationEvent[] }>('/observability/graduations'),
  getSummary: () => get<ObsSummary>('/observability/summary'),
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface MacroContext {
  mortgage_30yr: number
  fed_funds_rate: number
  mortgage_date: string
  source: string
}

export interface GeoState {
  state: string
  unemployment_rate: number | null
  unemployment_period: string
  fdic_enforcement_actions: number
  fdic_recent_actions: { institution: string; type: string; effective_date: string }[]
  cfpb_mortgage_complaints: number
  sources: string[]
}

export interface LoanResult {
  loan_id: string
  decision: string
  confidence: number
  summary: string
  key_risk: string
  violations: number
  warnings: number
  findings: { rule: string; severity: string; finding: string }[]
  escalated: boolean
  auto_resolved: boolean
  graduated_pattern?: string
}

export interface BatchResult {
  batch_id?: string
  results: LoanResult[]
}

export interface HITLCase {
  loan_id: string
  loan: Record<string, unknown>
  findings: { rule: string; severity: string; finding: string }[]
  confidence: number
  fingerprint: string
  escalated_at: number
  status: string
  human_decision: string | null
  human_rationale: string | null
}

export interface DecisionEvent {
  event_id: string
  timestamp: number
  loan_id: string
  decision: string
  confidence: number
  findings: unknown[]
  escalated_to_hitl: boolean
}

export interface ToolCallEvent {
  event_id: string
  timestamp: number
  tool: string
  inputs: Record<string, unknown>
  outputs: Record<string, unknown>
  duration_ms: number
}

export interface RepairEvent {
  event_id: string
  timestamp: number
  failure_type: string
  hypothesis: string
  action_taken: string
  resolution: string
}

export interface GraduationEvent {
  event_id: string
  timestamp: number
  case_fingerprint: string
  pattern: string
  n_consistent_decisions: number
  graduated_at: number
}

export interface ObsSummary {
  total_reviewed: number
  escalated_to_hitl: number
  auto_resolved: number
  avg_confidence: number
  self_repairs: number
  hitl_graduations: number
  pending_hitl: number
}
