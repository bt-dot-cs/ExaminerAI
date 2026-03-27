/**
 * Compliance Risk Map — react-simple-maps choropleth
 * Mapbox port: replace ComposableMap with a mapboxgl Map,
 * use a FillLayer with the same stateData as the data source.
 */
import { useEffect, useState } from 'react'
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps'
import { scaleLinear } from 'd3-scale'
import { api, GeoState, LoanResult } from '../api'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json'

// State name → abbreviation — full 50 states so choropleth colors everything
const STATE_ABBREV: Record<string, string> = {
  Alabama: 'AL', Alaska: 'AK', Arizona: 'AZ', Arkansas: 'AR', California: 'CA',
  Colorado: 'CO', Connecticut: 'CT', Delaware: 'DE', Florida: 'FL', Georgia: 'GA',
  Hawaii: 'HI', Idaho: 'ID', Illinois: 'IL', Indiana: 'IN', Iowa: 'IA',
  Kansas: 'KS', Kentucky: 'KY', Louisiana: 'LA', Maine: 'ME', Maryland: 'MD',
  Massachusetts: 'MA', Michigan: 'MI', Minnesota: 'MN', Mississippi: 'MS',
  Missouri: 'MO', Montana: 'MT', Nebraska: 'NE', Nevada: 'NV', 'New Hampshire': 'NH',
  'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
  'North Dakota': 'ND', Ohio: 'OH', Oklahoma: 'OK', Oregon: 'OR', Pennsylvania: 'PA',
  'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', Tennessee: 'TN',
  Texas: 'TX', Utah: 'UT', Vermont: 'VT', Virginia: 'VA', Washington: 'WA',
  'West Virginia': 'WV', Wisconsin: 'WI', Wyoming: 'WY',
}

// Approximate centroids for loan markers
const STATE_COORDS: Record<string, [number, number]> = {
  CA: [-119.4, 36.7], TX: [-99.3, 31.5], NY: [-75.5, 42.9],
  IL: [-89.2, 40.0], OH: [-82.9, 40.4], FL: [-81.5, 27.7], WA: [-120.5, 47.4],
}

type MapMetric = 'cfpb_mortgage_complaints' | 'fdic_enforcement_actions' | 'unemployment_rate'

interface Props { results: LoanResult[] }

export default function RiskMap({ results }: Props) {
  const [geoData, setGeoData] = useState<Record<string, GeoState>>({})
  const [metric, setMetric] = useState<MapMetric>('cfpb_mortgage_complaints')
  const [loading, setLoading] = useState(false)
  const [tooltip, setTooltip] = useState<{ state: string; x: number; y: number } | null>(null)

  const load = async () => {
    setLoading(true)
    try { setGeoData(await api.getGeo()) } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const values = Object.values(geoData).map(d => (d[metric] as number) ?? 0)
  const maxVal = Math.max(...values, 1)

  const colorScale = scaleLinear<string>()
    .domain([0, maxVal])
    .range(['#1a2332', '#f85149'])

  const metricLabel: Record<MapMetric, string> = {
    cfpb_mortgage_complaints: 'CFPB Mortgage Complaints',
    fdic_enforcement_actions: 'FDIC Enforcement Actions',
    unemployment_rate: 'Unemployment Rate (%)',
  }

  // Group loan results by state
  const loansByState: Record<string, LoanResult[]> = {}
  results.forEach(r => {
    // We don't have state on result directly — use loan_id to infer from synthetic data
    // The synthetic data has states embedded; for demo we map loan IDs to states
    const stateMap: Record<string, string> = {
      'LOAN-001': 'CA', 'LOAN-002': 'CA', 'LOAN-003': 'TX', 'LOAN-004': 'TX',
      'LOAN-005': 'NY', 'LOAN-006': 'IL', 'LOAN-007': 'OH', 'LOAN-008': 'FL',
      'LOAN-009': 'WA', 'LOAN-010': 'WA',
    }
    const st = stateMap[r.loan_id]
    if (st) { loansByState[st] = [...(loansByState[st] || []), r] }
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Controls */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Color by:</span>
        {(Object.keys(metricLabel) as MapMetric[]).map(m => (
          <button key={m} onClick={() => setMetric(m)}
            style={{ background: metric === m ? 'var(--blue)' : undefined, color: metric === m ? '#000' : undefined }}>
            {metricLabel[m]}
          </button>
        ))}
        <button onClick={load} disabled={loading} style={{ marginLeft: 'auto' }}>
          {loading ? '…' : 'Refresh'}
        </button>
      </div>

      {/* Map */}
      <div style={{ position: 'relative', background: 'var(--surface2)', borderRadius: 8, overflow: 'hidden' }}>
        <ComposableMap projection="geoAlbersUsa" style={{ width: '100%', height: 340 }}>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => {
                const stateName = geo.properties.name as string
                const abbrev = STATE_ABBREV[stateName]
                const data = abbrev ? geoData[abbrev] : undefined
                const val = data ? ((data[metric] as number) ?? 0) : 0
                const isActive = !!abbrev && !!data

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={isActive ? colorScale(val) : '#1a2332'}
                    stroke="#30363d"
                    strokeWidth={0.5}
                    onMouseEnter={(e) => {
                      if (abbrev) setTooltip({ state: abbrev, x: e.clientX, y: e.clientY })
                    }}
                    onMouseLeave={() => setTooltip(null)}
                    style={{ default: { outline: 'none' }, hover: { outline: 'none', opacity: 0.85 }, pressed: { outline: 'none' } }}
                  />
                )
              })
            }
          </Geographies>

          {/* Loan markers */}
          {Object.entries(loansByState).map(([state, loans]) => {
            const coords = STATE_COORDS[state]
            if (!coords) return null
            const hasEscalation = loans.some(l => l.escalated)
            const hasViolation = loans.some(l => l.violations > 0)
            const color = hasViolation ? 'var(--red)' : hasEscalation ? 'var(--yellow)' : 'var(--green)'
            return (
              <Marker key={state} coordinates={coords}>
                <circle r={8} fill={color} fillOpacity={0.85} stroke="#fff" strokeWidth={1.5} />
                <text textAnchor="middle" y={-12} style={{ fontSize: 10, fill: '#fff', fontWeight: 700 }}>
                  {loans.length}
                </text>
              </Marker>
            )
          })}
        </ComposableMap>

        {/* Tooltip */}
        {tooltip && geoData[tooltip.state] && (
          <div style={{
            position: 'fixed', left: tooltip.x + 12, top: tooltip.y - 10,
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 6, padding: '8px 12px', fontSize: 12, pointerEvents: 'none', zIndex: 100,
          }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>{tooltip.state}</div>
            <div style={{ color: 'var(--text-muted)' }}>
              CFPB complaints: <span style={{ color: 'var(--red)' }}>{geoData[tooltip.state].cfpb_mortgage_complaints?.toLocaleString()}</span>
            </div>
            <div style={{ color: 'var(--text-muted)' }}>
              FDIC actions: <span style={{ color: 'var(--orange)' }}>{geoData[tooltip.state].fdic_enforcement_actions}</span>
            </div>
            <div style={{ color: 'var(--text-muted)' }}>
              Unemployment: <span style={{ color: 'var(--yellow)' }}>{geoData[tooltip.state].unemployment_rate}%</span>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--text-muted)' }}>
        <span>Low</span>
        <div style={{ width: 120, height: 8, borderRadius: 4, background: 'linear-gradient(to right, #1a2332, #f85149)' }} />
        <span>High</span>
        <span style={{ marginLeft: 16 }}>● Loans: </span>
        <span style={{ color: 'var(--green)' }}>● approved</span>
        <span style={{ color: 'var(--yellow)' }}>● escalated</span>
        <span style={{ color: 'var(--red)' }}>● violation</span>
        <span style={{ marginLeft: 8, color: 'var(--text-muted)' }}>Sources: BLS · FDIC · CFPB</span>
      </div>
    </div>
  )
}
