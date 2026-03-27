"""
Ghost DB integration — durable PostgreSQL layer for compliance audit trail.

Architecture split:
  Aerospike  → hot path: ephemeral/session memory, sub-ms reads during active runs
  Ghost DB   → cold/durable path: decision audit log, graduated patterns, HITL history

Ghost DB persists across restarts; Aerospike is the speed layer.
"""
import json
import time
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import GHOST_DB_URL

_conn = None


def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(GHOST_DB_URL)
        _conn.autocommit = True
    return _conn


def init_schema():
    """Create tables if they don't exist. Safe to call on every startup."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS decision_audit (
                event_id    TEXT PRIMARY KEY,
                loan_id     TEXT NOT NULL,
                decision    TEXT NOT NULL,
                confidence  REAL NOT NULL,
                findings    JSONB NOT NULL,
                escalated   BOOLEAN NOT NULL,
                batch_id    TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS graduated_patterns (
                fingerprint TEXT PRIMARY KEY,
                decision    TEXT NOT NULL,
                pattern     TEXT NOT NULL,
                n_decisions INTEGER NOT NULL,
                graduated_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hitl_decisions (
                id          SERIAL PRIMARY KEY,
                loan_id     TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                decision    TEXT NOT NULL,
                rationale   TEXT,
                reviewed_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)


# ── Decision audit ─────────────────────────────────────────────────────────────

def write_decision(event_id: str, loan_id: str, decision: str, confidence: float,
                   findings: list, escalated: bool, batch_id: str = None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO decision_audit (event_id, loan_id, decision, confidence, findings, escalated, batch_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
        """, (event_id, loan_id, decision, confidence, json.dumps(findings), escalated, batch_id))


def read_decisions(limit: int = 100) -> list:
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM decision_audit ORDER BY created_at DESC LIMIT %s", (limit,)
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ── Graduated patterns ─────────────────────────────────────────────────────────

def upsert_graduated_pattern(fingerprint: str, decision: str, pattern: str, n_decisions: int):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO graduated_patterns (fingerprint, decision, pattern, n_decisions, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (fingerprint) DO UPDATE
              SET decision = EXCLUDED.decision,
                  pattern = EXCLUDED.pattern,
                  n_decisions = EXCLUDED.n_decisions,
                  updated_at = NOW()
        """, (fingerprint, decision, pattern, n_decisions))


def read_graduated_patterns() -> dict:
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM graduated_patterns ORDER BY graduated_at DESC")
        rows = cur.fetchall()
        return {r["fingerprint"]: dict(r) for r in rows}


# ── HITL decisions ─────────────────────────────────────────────────────────────

def write_hitl_decision(loan_id: str, fingerprint: str, decision: str, rationale: str):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO hitl_decisions (loan_id, fingerprint, decision, rationale)
            VALUES (%s, %s, %s, %s)
        """, (loan_id, fingerprint, decision, rationale))


def read_hitl_decisions(fingerprint: str = None) -> list:
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if fingerprint:
            cur.execute(
                "SELECT * FROM hitl_decisions WHERE fingerprint = %s ORDER BY reviewed_at DESC",
                (fingerprint,)
            )
        else:
            cur.execute("SELECT * FROM hitl_decisions ORDER BY reviewed_at DESC LIMIT 200")
        return [dict(r) for r in cur.fetchall()]


# ── Health check ───────────────────────────────────────────────────────────────

def ping() -> dict:
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM decision_audit")
            audit_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM graduated_patterns")
            pattern_count = cur.fetchone()[0]
        return {"status": "ok", "audit_records": audit_count, "graduated_patterns": pattern_count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
