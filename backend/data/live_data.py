"""
Live data ingestion from FRED, BLS, FDIC, and CFPB APIs.
Airbyte swap-in: replace fetch_* functions with Airbyte connector calls.
"""
import httpx
from config import FRED_API_KEY, BLS_API_KEY

FDIC_BASE = "https://banks.data.fdic.gov/api"
CFPB_BASE = "https://api.consumerfinance.gov/data-research/consumer-complaints"

# BLS state unemployment series IDs for the 7 states in our loan dataset
STATE_BLS_SERIES = {
    "CA": "LASST060000000000003",
    "TX": "LASST480000000000003",
    "NY": "LASST360000000000003",
    "IL": "LASST170000000000003",
    "OH": "LASST390000000000003",
    "FL": "LASST120000000000003",
    "WA": "LASST530000000000003",
}

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
BLS_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def fetch_fred_series(series_id: str) -> dict:
    """Fetch latest observation for a FRED series."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "limit": 1,
        "sort_order": "desc",
    }
    resp = httpx.get(FRED_BASE, params=params, timeout=10)
    resp.raise_for_status()
    obs = resp.json().get("observations", [])
    if obs:
        return {"series_id": series_id, "value": float(obs[0]["value"]), "date": obs[0]["date"]}
    return {"series_id": series_id, "value": None, "date": None}


def fetch_macro_context() -> dict:
    """Pull key macro indicators for compliance context."""
    mortgage_rate = fetch_fred_series("MORTGAGE30US")
    fed_funds = fetch_fred_series("FEDFUNDS")
    return {
        "mortgage_30yr": mortgage_rate["value"],
        "fed_funds_rate": fed_funds["value"],
        "mortgage_date": mortgage_rate["date"],
        "source": "FRED",
    }


def fetch_bls_unemployment(series_ids: list[str] = None) -> dict:
    """Fetch regional unemployment from BLS."""
    if series_ids is None:
        series_ids = ["LNS14000000"]  # national unemployment rate
    payload = {
        "seriesid": series_ids,
        "registrationkey": BLS_API_KEY,
        "latest": True,
    }
    try:
        resp = httpx.post(BLS_BASE, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = {}
        for series in data.get("Results", {}).get("series", []):
            sid = series["seriesID"]
            latest = series["data"][0] if series["data"] else {}
            results[sid] = {
                "value": float(latest.get("value", 0)),
                "period": latest.get("periodName", ""),
                "year": latest.get("year", ""),
            }
        return results
    except Exception as e:
        return {"error": str(e), "LNS14000000": {"value": 4.1, "period": "fallback"}}


def fetch_state_unemployment() -> dict:
    """Fetch state-level unemployment for all 7 states in the loan dataset."""
    series_ids = list(STATE_BLS_SERIES.values())
    payload = {
        "seriesid": series_ids,
        "registrationkey": BLS_API_KEY,
        "latest": True,
    }
    # Reverse map: series_id → state abbrev
    reverse = {v: k for k, v in STATE_BLS_SERIES.items()}
    try:
        resp = httpx.post(BLS_BASE, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = {}
        for series in data.get("Results", {}).get("series", []):
            sid = series["seriesID"]
            state = reverse.get(sid, sid)
            latest = series["data"][0] if series["data"] else {}
            results[state] = {
                "unemployment_rate": float(latest.get("value", 0)),
                "period": latest.get("periodName", ""),
                "year": latest.get("year", ""),
                "series_id": sid,
            }
        return results
    except Exception as e:
        # Fallback: approximate values so the map still renders
        return {
            state: {"unemployment_rate": 4.1, "period": "fallback", "year": "2026", "series_id": sid}
            for state, sid in STATE_BLS_SERIES.items()
        }


def fetch_fdic_enforcement_actions(states: list[str] = None) -> dict:
    """
    Fetch FDIC enforcement actions by state.
    Returns count of active enforcement actions per state.
    """
    if states is None:
        states = list(STATE_BLS_SERIES.keys())

    results = {}
    for state in states:
        try:
            resp = httpx.get(
                f"{FDIC_BASE}/enforcement",
                params={
                    "filters": f"STALP:{state}",
                    "fields": "STALP,CERT,INSTNAME,ENFTYP,EFFDATE",
                    "limit": 50,
                    "offset": 0,
                    "sort_by": "EFFDATE",
                    "sort_order": "DESC",
                    "output": "json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            actions = data.get("data", [])
            results[state] = {
                "enforcement_action_count": len(actions),
                "recent_actions": [
                    {
                        "institution": a.get("data", {}).get("INSTNAME", ""),
                        "type": a.get("data", {}).get("ENFTYP", ""),
                        "effective_date": a.get("data", {}).get("EFFDATE", ""),
                    }
                    for a in actions[:3]  # top 3 most recent for display
                ],
            }
        except Exception as e:
            results[state] = {"enforcement_action_count": 0, "recent_actions": [], "error": str(e)}

    return results


def fetch_cfpb_mortgage_complaints(states: list[str] = None) -> dict:
    """
    Fetch CFPB mortgage complaint counts by state.
    Uses the CFPB aggregation API with state filter.
    """
    if states is None:
        states = list(STATE_BLS_SERIES.keys())

    results = {}
    for state in states:
        try:
            resp = httpx.get(
                CFPB_BASE,
                params={
                    "state": state,
                    "product": "Mortgage",
                    "date_received_min": "2024-01-01",
                    "format": "json",
                    "size": 1,  # we only need total count, not records
                    "field": "all",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            # CFPB returns hits.total as int or {value, relation}
            total = data.get("hits", {}).get("total", 0)
            count = total.get("value", 0) if isinstance(total, dict) else int(total)
            results[state] = {
                "mortgage_complaint_count": count,
                "source": "CFPB",
                "period": "2024-present",
            }
        except Exception as e:
            results[state] = {"mortgage_complaint_count": 0, "source": "CFPB", "error": str(e)}

    return results


ALL_STATES = [
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY',
]

def fetch_geo_risk_context(states: list[str] = None) -> dict:
    """
    Aggregate all geo-level risk signals into a single map-ready payload.
    Covers all 50 states for choropleth; BLS detail only for the 7 loan states.
    """
    if states is None:
        states = ALL_STATES

    # BLS only for the 7 states we have series IDs for
    unemployment = fetch_state_unemployment()
    # FDIC and CFPB for all states
    enforcement = fetch_fdic_enforcement_actions(states)
    complaints = fetch_cfpb_mortgage_complaints(states)

    combined = {}
    for state in states:
        combined[state] = {
            "state": state,
            "unemployment_rate": unemployment.get(state, {}).get("unemployment_rate"),
            "unemployment_period": unemployment.get(state, {}).get("period"),
            "fdic_enforcement_actions": enforcement.get(state, {}).get("enforcement_action_count", 0),
            "fdic_recent_actions": enforcement.get(state, {}).get("recent_actions", []),
            "cfpb_mortgage_complaints": complaints.get(state, {}).get("mortgage_complaint_count", 0),
            "sources": ["BLS", "FDIC", "CFPB"],
        }

    return combined
