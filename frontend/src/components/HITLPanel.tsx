import { useState } from 'react'
import { api, HITLCase } from '../api'

interface Props {
  queue: HITLCase[]
  onDecision: () => void
}

export default function HITLPanel({ queue, onDecision }: Props) {
  const [selected, setSelected] = useState<HITLCase | null>(null)
  const [decision, setDecision] = useState<'APPROVE' | 'DECLINE'>('APPROVE')
  const [rationale, setRationale] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [lastGraduation, setLastGraduation] = useState<string | null>(null)

  const pending = queue.filter(c => c.status === 'pending')

  const submit = async () => {
    if (!selected || !rationale.trim()) return
    setSubmitting(true)
    try {
      const res = await api.submitDecision(selected.loan_id, decision, rationale) as any
      if (res.graduation) {
        setLastGraduation(res.graduation.pattern)
      }
      setSelected(null)
      setRationale('')
      onDecision()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* Queue list */}
      <div style={{ width: 220, flexShrink: 0 }}>
        <div className="section-title">Pending ({pending.length})</div>
        {pending.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No pending cases</div>
        )}
        {pending.map(c => (
          <div
            key={c.loan_id}
            onClick={() => setSelected(c)}
            style={{
              padding: '8px 10px', borderRadius: 6, cursor: 'pointer', marginBottom: 4,
              background: selected?.loan_id === c.loan_id ? 'var(--surface2)' : 'transparent',
              border: `1px solid ${selected?.loan_id === c.loan_id ? 'var(--blue)' : 'var(--border)'}`,
            }}
          >
            <div style={{ fontFamily: 'monospace', color: 'var(--blue)', fontSize: 12 }}>{c.loan_id}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
              conf: {(c.confidence * 100).toFixed(0)}% · fp: {c.fingerprint}
            </div>
          </div>
        ))}
      </div>

      {/* Review panel */}
      <div style={{ flex: 1 }}>
        {lastGraduation && (
          <div style={{
            background: 'rgba(188,140,255,0.1)', border: '1px solid rgba(188,140,255,0.4)',
            borderRadius: 6, padding: 10, marginBottom: 12, fontSize: 12,
          }}>
            <span style={{ color: 'var(--purple)', fontWeight: 600 }}>⚡ Pattern graduated to automated: </span>
            <span style={{ color: 'var(--text-muted)' }}>{lastGraduation}</span>
          </div>
        )}

        {selected ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="section-title">Reviewing {selected.loan_id}</div>

            {/* Loan snapshot */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                ['Income', `$${(selected.loan as any).income?.toLocaleString()}`],
                ['Loan Amount', `$${(selected.loan as any).loan_amount?.toLocaleString()}`],
                ['DTI', `${((selected.loan as any).dti * 100).toFixed(0)}%`],
                ['Credit Score', (selected.loan as any).credit_score],
                ['Race', (selected.loan as any).race],
                ['State', (selected.loan as any).property_state],
              ].map(([k, v]) => (
                <div key={k as string} style={{ background: 'var(--surface2)', borderRadius: 4, padding: '6px 10px' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{k}</div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{v as string}</div>
                </div>
              ))}
            </div>

            {/* Findings */}
            <div>
              {selected.findings.map((f, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 4, fontSize: 12 }}>
                  <span className={`badge ${f.severity}`}>{f.severity}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{f.finding}</span>
                </div>
              ))}
            </div>

            {/* Decision input */}
            <div style={{ display: 'flex', gap: 8 }}>
              {(['APPROVE', 'DECLINE'] as const).map(d => (
                <button
                  key={d}
                  onClick={() => setDecision(d)}
                  className={decision === d ? (d === 'APPROVE' ? 'primary' : 'danger') : ''}
                >
                  {d}
                </button>
              ))}
            </div>

            <textarea
              rows={3}
              placeholder="Enter rationale for this decision…"
              value={rationale}
              onChange={e => setRationale(e.target.value)}
            />

            <button className="primary" onClick={submit} disabled={submitting || !rationale.trim()}>
              {submitting ? 'Submitting…' : 'Submit Decision'}
            </button>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: 12, paddingTop: 8 }}>
            Select a case from the queue to review.
          </div>
        )}
      </div>
    </div>
  )
}
