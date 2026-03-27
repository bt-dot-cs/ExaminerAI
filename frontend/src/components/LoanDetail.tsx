import { LoanResult } from '../api'

interface Props { result: LoanResult }

export default function LoanDetail({ result }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontFamily: 'monospace', color: 'var(--blue)', fontSize: 15, fontWeight: 700 }}>
          {result.loan_id}
        </span>
        {result.auto_resolved && (
          <span className="badge auto">⚡ Auto-resolved via graduated pattern</span>
        )}
      </div>

      {result.auto_resolved && result.graduated_pattern && (
        <div style={{ background: 'rgba(188,140,255,0.08)', border: '1px solid rgba(188,140,255,0.3)', borderRadius: 6, padding: 10, fontSize: 12 }}>
          <span style={{ color: 'var(--purple)' }}>Graduated pattern: </span>
          <span style={{ color: 'var(--text-muted)' }}>{result.graduated_pattern}</span>
        </div>
      )}

      <div style={{ background: 'var(--surface2)', borderRadius: 6, padding: 12, fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
        {result.summary || 'No summary available.'}
      </div>

      {result.findings.length > 0 && (
        <div>
          <div className="section-title">Findings</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {result.findings.map((f, i) => (
              <div key={i} style={{
                display: 'flex', gap: 10, alignItems: 'flex-start',
                padding: '8px 10px', background: 'var(--surface2)', borderRadius: 6,
              }}>
                <span className={`badge ${f.severity}`}>{f.severity}</span>
                <div>
                  <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--blue)', marginBottom: 2 }}>{f.rule}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{f.finding}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
