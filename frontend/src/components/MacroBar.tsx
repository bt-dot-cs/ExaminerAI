import { useEffect, useState } from 'react'
import { api, MacroContext } from '../api'

export default function MacroBar() {
  const [macro, setMacro] = useState<MacroContext | null>(null)
  const [loading, setLoading] = useState(false)

  const fetch = async () => {
    setLoading(true)
    try { setMacro(await api.getMacro()) } finally { setLoading(false) }
  }

  useEffect(() => { fetch() }, [])

  return (
    <div style={{
      background: 'var(--surface)', borderBottom: '1px solid var(--border)',
      padding: '10px 24px', display: 'flex', alignItems: 'center', gap: 32,
    }}>
      <span style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Live Market Context
      </span>
      {macro ? (
        <>
          <Stat label="30yr Mortgage" value={`${macro.mortgage_30yr}%`} color="var(--blue)" />
          <Stat label="Fed Funds" value={`${macro.fed_funds_rate}%`} color="var(--orange)" />
          <Stat label="As of" value={macro.mortgage_date} color="var(--text-muted)" />
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>source: FRED</span>
        </>
      ) : (
        <span style={{ color: 'var(--text-muted)' }}>{loading ? 'Fetching live rates…' : '—'}</span>
      )}
      <button onClick={fetch} style={{ marginLeft: 'auto' }} disabled={loading}>
        {loading ? '…' : 'Refresh'}
      </button>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontSize: 15, fontWeight: 700, color }}>{value}</span>
    </div>
  )
}
