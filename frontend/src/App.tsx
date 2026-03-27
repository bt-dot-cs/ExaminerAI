import { useState, useEffect, useRef } from 'react'
import { api, LoanResult, HITLCase } from './api'
import MacroBar from './components/MacroBar'
import BatchTable from './components/BatchTable'
import LoanDetail from './components/LoanDetail'
import HITLPanel from './components/HITLPanel'
import ObservabilityPanel from './components/ObservabilityPanel'
import RiskMap from './components/RiskMap'

type Tab = 'batch' | 'hitl' | 'observability' | 'map'

export default function App() {
  const [tab, setTab] = useState<Tab>('batch')
  const [results, setResults] = useState<LoanResult[]>([])
  const [selected, setSelected] = useState<LoanResult | null>(null)
  const [hitlQueue, setHitlQueue] = useState<HITLCase[]>([])
  const [running, setRunning] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [runStatus, setRunStatus] = useState('')
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startTimer = () => {
    setElapsed(0)
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
  }
  const stopTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current)
  }

  const RUN_STEPS = [
    [0,  'Fetching live FRED mortgage rates…'],
    [3,  'Running compliance rule engine…'],
    [8,  'Claude reviewing loan applications…'],
    [18, 'Evaluating fair lending flags…'],
    [25, 'Writing decisions to memory…'],
    [30, 'Finalising HITL escalations…'],
  ]

  const loadQueue = async () => {
    const q = await api.getHITLQueue()
    setHitlQueue(q.queue)
  }

  const runBatch = async () => {
    setRunning(true)
    setSelected(null)
    setRunStatus('Starting batch…')
    startTimer()
    try {
      const res = await api.runBatch()
      setResults(res.results)
      await loadQueue()
      setRunStatus('')
    } catch (e) {
      setRunStatus('Error — check backend logs')
    } finally {
      setRunning(false)
      stopTimer()
    }
  }

  // Update status message based on elapsed time
  useEffect(() => {
    if (!running) return
    const step = [...RUN_STEPS].reverse().find(([t]) => elapsed >= (t as number))
    if (step) setRunStatus(step[1] as string)
  }, [elapsed, running])

  useEffect(() => {
    api.getResults().then(r => { if (r.results.length) setResults(r.results) })
    loadQueue()
  }, [])

  const pendingCount = hitlQueue.filter(c => c.status === 'pending').length

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        background: 'var(--surface)', borderBottom: '1px solid var(--border)',
        padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>Compliance Agent</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Community Bank · Fair Lending · QM · HMDA
          </div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          {running && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
              <div style={{ fontSize: 11, color: 'var(--blue)' }}>{runStatus}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                {elapsed}s elapsed
              </div>
            </div>
          )}
          <button className="primary" onClick={runBatch} disabled={running}>
            {running ? '⟳ Running…' : '▶ Run Compliance Batch'}
          </button>
        </div>
      </div>

      {/* Macro bar */}
      <MacroBar />

      {/* Tabs */}
      <div style={{
        background: 'var(--surface)', borderBottom: '1px solid var(--border)',
        padding: '0 24px', display: 'flex', gap: 0,
      }}>
        {([
          { id: 'batch', label: `Batch Results ${results.length ? `(${results.length})` : ''}` },
          { id: 'hitl', label: `HITL Queue ${pendingCount > 0 ? `(${pendingCount})` : ''}` },
          { id: 'observability', label: 'Observability' },
          { id: 'map', label: 'Risk Map' },
        ] as { id: Tab; label: string }[]).map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              border: 'none', borderBottom: tab === t.id ? '2px solid var(--blue)' : '2px solid transparent',
              borderRadius: 0, background: 'transparent', padding: '10px 16px',
              color: tab === t.id ? 'var(--blue)' : 'var(--text-muted)',
              fontWeight: tab === t.id ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: 24, display: 'flex', gap: 20 }}>
        {tab === 'batch' && (
          <>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="card" style={{ marginBottom: 16 }}>
                <div className="section-title">Loan Applications</div>
                <BatchTable results={results} onSelect={setSelected} selected={selected?.loan_id ?? null} />
              </div>
            </div>
            {selected && (
              <div style={{ width: 380, flexShrink: 0 }}>
                <div className="card">
                  <div className="section-title">Decision Detail</div>
                  <LoanDetail result={selected} />
                </div>
              </div>
            )}
          </>
        )}

        {tab === 'hitl' && (
          <div className="card" style={{ flex: 1 }}>
            <div className="section-title">Human-in-the-Loop Review</div>
            <HITLPanel queue={hitlQueue} onDecision={loadQueue} />
          </div>
        )}

        {tab === 'observability' && (
          <div style={{ flex: 1 }}>
            <ObservabilityPanel />
          </div>
        )}

        {tab === 'map' && (
          <div className="card" style={{ flex: 1 }}>
            <div className="section-title">Compliance Risk Map — Live Data</div>
            <RiskMap results={results} />
          </div>
        )}
      </div>
    </div>
  )
}
