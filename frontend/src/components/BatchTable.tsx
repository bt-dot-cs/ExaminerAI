import { LoanResult } from '../api'

interface Props {
  results: LoanResult[]
  onSelect: (r: LoanResult) => void
  selected: string | null
}

const decisionColor: Record<string, string> = {
  APPROVE: 'approve',
  DECLINE: 'decline',
  ESCALATE_TO_HUMAN: 'escalate',
}

function confidenceColor(c: number) {
  if (c >= 0.75) return 'var(--green)'
  if (c >= 0.55) return 'var(--yellow)'
  return 'var(--red)'
}

export default function BatchTable({ results, onSelect, selected }: Props) {
  if (!results.length) return (
    <div style={{ color: 'var(--text-muted)', padding: 24, textAlign: 'center' }}>
      No results yet — run the batch to begin.
    </div>
  )

  return (
    <div className="scrollable">
      <table>
        <thead>
          <tr>
            <th>Loan ID</th>
            <th>Decision</th>
            <th>Confidence</th>
            <th>Violations</th>
            <th>Warnings</th>
            <th>Escalated</th>
            <th>Key Risk</th>
          </tr>
        </thead>
        <tbody>
          {results.map(r => (
            <tr
              key={r.loan_id}
              onClick={() => onSelect(r)}
              style={{
                cursor: 'pointer',
                background: selected === r.loan_id ? 'var(--surface2)' : undefined,
                borderLeft: selected === r.loan_id ? '2px solid var(--blue)' : '2px solid transparent',
              }}
            >
              <td style={{ fontFamily: 'monospace', color: 'var(--blue)' }}>{r.loan_id}</td>
              <td>
                <span className={`badge ${r.auto_resolved ? 'auto' : decisionColor[r.decision] ?? 'info'}`}>
                  {r.auto_resolved ? '⚡ AUTO' : r.decision}
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="confidence-bar" style={{ width: 60 }}>
                    <div
                      className="confidence-bar-fill"
                      style={{ width: `${r.confidence * 100}%`, background: confidenceColor(r.confidence) }}
                    />
                  </div>
                  <span style={{ color: confidenceColor(r.confidence), fontFamily: 'monospace' }}>
                    {(r.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </td>
              <td style={{ color: r.violations > 0 ? 'var(--red)' : 'var(--text-muted)' }}>
                {r.violations}
              </td>
              <td style={{ color: r.warnings > 0 ? 'var(--yellow)' : 'var(--text-muted)' }}>
                {r.warnings}
              </td>
              <td>{r.escalated ? <span style={{ color: 'var(--yellow)' }}>↑ HITL</span> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
              <td style={{ color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {r.key_risk || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
