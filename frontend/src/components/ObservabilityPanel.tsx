import { useEffect, useState } from 'react'
import { api, DecisionEvent, ToolCallEvent, RepairEvent, GraduationEvent, ObsSummary } from '../api'

interface ExecutionRun {
  run_number: number
  mode: string
  wall_time_s: number
  per_loan_ms: number
  n_loans: number
  timestamp: number
  experiment?: { hypothesis: string; action: string; resolution: string; next_mode: string }
}

interface ExecutionStrategy {
  mode: string
  runs: number
  last_wall_time_s: number
  last_per_loan_ms: number
  history: ExecutionRun[]
}

export default function ObservabilityPanel() {
  const [summary, setSummary] = useState<ObsSummary | null>(null)
  const [toolCalls, setToolCalls] = useState<ToolCallEvent[]>([])
  const [repairs, setRepairs] = useState<RepairEvent[]>([])
  const [graduations, setGraduations] = useState<GraduationEvent[]>([])
  const [strategy, setStrategy] = useState<ExecutionStrategy | null>(null)
  const [repairing, setRepairing] = useState(false)
  const [lastRepair, setLastRepair] = useState<RepairEvent | null>(null)

  const refresh = async () => {
    const [s, tc, r, g, strat] = await Promise.all([
      api.getSummary(), api.getToolCalls(), api.getRepairs(), api.getGraduations(),
      fetch('/api/observability/execution-strategy').then(r => r.json()),
    ])
    setSummary(s)
    setToolCalls(tc.tool_calls)
    setRepairs(r.repairs)
    setGraduations(g.graduations)
    setStrategy(strat.strategy?.runs ? strat.strategy : null)
  }

  useEffect(() => { refresh() }, [])

  const triggerRepair = async () => {
    setRepairing(true)
    try {
      const res = await api.triggerFailure()
      setLastRepair(res.repair_event)
      await refresh()
    } finally { setRepairing(false) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Summary stats */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          {[
            { label: 'Reviewed', value: summary.total_reviewed, color: 'var(--blue)' },
            { label: 'Avg Confidence', value: `${(summary.avg_confidence * 100).toFixed(1)}%`, color: 'var(--green)' },
            { label: 'HITL Escalations', value: summary.escalated_to_hitl, color: 'var(--yellow)' },
            { label: 'Auto-Resolved', value: summary.auto_resolved, color: 'var(--purple)' },
            { label: 'Self-Repairs', value: summary.self_repairs, color: 'var(--orange)' },
            { label: 'Graduations', value: summary.hitl_graduations, color: 'var(--purple)' },
            { label: 'Pending HITL', value: summary.pending_hitl, color: 'var(--yellow)' },
          ].map(s => (
            <div key={s.label} className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Execution strategy / performance learning */}
      {strategy && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
            <div className="section-title" style={{ marginBottom: 0 }}>Execution Strategy — Self-Optimising</div>
            <button
              style={{ marginLeft: 'auto', fontSize: 11 }}
              onClick={async () => {
                await fetch('/api/demo/reset-strategy', { method: 'POST' })
                await refresh()
              }}
            >
              ↺ Reset for Demo
            </button>
          </div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
            <div style={{ background: 'var(--surface2)', borderRadius: 6, padding: '8px 14px', textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: strategy.mode === 'parallel' ? 'var(--green)' : 'var(--blue)' }}>
                {strategy.mode.toUpperCase()}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>current mode</div>
            </div>
            <div style={{ background: 'var(--surface2)', borderRadius: 6, padding: '8px 14px', textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--orange)' }}>{strategy.last_wall_time_s}s</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>last batch time</div>
            </div>
            <div style={{ background: 'var(--surface2)', borderRadius: 6, padding: '8px 14px', textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--purple)' }}>{strategy.runs}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>batches run</div>
            </div>
          </div>
          {/* Run history */}
          <div className="scrollable" style={{ maxHeight: 200 }}>
            {[...(strategy.history || [])].reverse().map((run, i) => (
              <div key={i} style={{
                padding: '8px 10px', borderRadius: 6, marginBottom: 4,
                background: run.mode === 'parallel' ? 'rgba(63,185,80,0.06)' : 'rgba(88,166,255,0.06)',
                border: `1px solid ${run.mode === 'parallel' ? 'rgba(63,185,80,0.2)' : 'rgba(88,166,255,0.2)'}`,
              }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>Run #{run.run_number}</span>
                  <span className={`badge ${run.mode === 'parallel' ? 'approve' : 'info'}`}>{run.mode}</span>
                  <span style={{ marginLeft: 'auto', fontFamily: 'monospace', color: run.wall_time_s > 30 ? 'var(--red)' : 'var(--green)' }}>
                    {run.wall_time_s}s
                  </span>
                </div>
                {run.experiment && (
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    <span style={{ color: 'var(--text)' }}>Hypothesis: </span>{run.experiment.hypothesis}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Self-repair demo trigger */}
      <div className="card">
        <div className="section-title">Self-Repair Engine</div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <button onClick={triggerRepair} disabled={repairing} className="danger">
            {repairing ? 'Triggering…' : '⚡ Trigger Demo Failure'}
          </button>
          {lastRepair && (
            <div style={{ flex: 1, background: 'var(--surface2)', borderRadius: 6, padding: 10, fontSize: 12 }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                <span className="badge violation">{lastRepair.failure_type}</span>
              </div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>
                <span style={{ color: 'var(--text)' }}>Hypothesis: </span>{lastRepair.hypothesis}
              </div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>
                <span style={{ color: 'var(--text)' }}>Action: </span>{lastRepair.action_taken}
              </div>
              <div style={{ color: 'var(--green)' }}>
                <span style={{ color: 'var(--text)' }}>Resolution: </span>{lastRepair.resolution}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Graduation log */}
      {graduations.length > 0 && (
        <div className="card">
          <div className="section-title">HITL Graduation Log</div>
          <div className="scrollable" style={{ maxHeight: 180 }}>
            {graduations.map(g => (
              <div key={g.event_id} style={{
                padding: '8px 10px', borderRadius: 6, marginBottom: 4,
                background: 'rgba(188,140,255,0.08)', border: '1px solid rgba(188,140,255,0.2)',
              }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ color: 'var(--purple)', fontWeight: 600 }}>⚡ Graduated</span>
                  <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>
                    fp:{g.case_fingerprint}
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
                    {new Date(g.graduated_at * 1000).toLocaleTimeString()}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{g.pattern}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  {g.n_consistent_decisions} consistent decisions
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tool call trace */}
      <div className="card">
        <div className="section-title">Tool Call Trace</div>
        <div className="scrollable">
          <table>
            <thead>
              <tr>
                <th>Tool</th>
                <th>Latency</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {toolCalls.map(t => (
                <tr key={t.event_id}>
                  <td style={{ fontFamily: 'monospace', color: 'var(--blue)' }}>{t.tool}</td>
                  <td style={{ color: t.duration_ms > 2000 ? 'var(--red)' : t.duration_ms > 500 ? 'var(--yellow)' : 'var(--green)' }}>
                    {t.duration_ms.toFixed(0)}ms
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>
                    {new Date(t.timestamp * 1000).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
              {toolCalls.length === 0 && (
                <tr><td colSpan={3} style={{ color: 'var(--text-muted)', textAlign: 'center' }}>No tool calls yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ textAlign: 'right' }}>
        <button onClick={refresh}>Refresh</button>
      </div>
    </div>
  )
}
