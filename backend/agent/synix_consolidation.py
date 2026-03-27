"""
Synix consolidation module.

Responsibilities:
  1. Export HITL decisions to Synix source files after each batch
  2. Trigger `synix build` + `synix release local` (incremental — only changed layers rebuild)
  3. Load the released context.md into the Aerospike durable tier
  4. Provide query interface over the Synix search index

Living memory flow:
  batch run → HITL decisions reviewed → consolidate() → Synix rebuilds hitl_patterns +
  core_memory → new context.md → loaded to Aerospike durable → next agent run reads enriched context
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agent.memory import write_durable, read_durable

MEMORY_DIR = Path(__file__).parent.parent / "memory"
HITL_SOURCES_DIR = MEMORY_DIR / "sources" / "hitl_decisions"
RELEASE_DIR = MEMORY_DIR / ".synix" / "releases" / "local"
CONTEXT_FILE = RELEASE_DIR / "context.md"


# ── Export ─────────────────────────────────────────────────────────────────────

def export_hitl_decisions(decisions: list) -> Path:
    """
    Write a list of reviewed HITL decisions as a Synix source markdown file.
    Synix picks this up on the next build and folds it into hitl_patterns.
    """
    HITL_SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = HITL_SOURCES_DIR / f"session_{timestamp}.md"

    lines = [f"# HITL Decision Batch — {timestamp}\n"]
    lines.append(f"**Session decision count:** {len(decisions)}\n")

    for d in decisions:
        lines.append(f"## Case {d.get('loan_id', 'unknown')}")
        lines.append(f"- **Fingerprint:** `{d.get('fingerprint', 'N/A')}`")
        lines.append(f"- **Human Decision:** {d.get('human_decision', 'N/A')}")
        lines.append(f"- **Rationale:** {d.get('human_rationale', 'N/A')}")
        lines.append(f"- **Agent Confidence at Escalation:** {d.get('confidence', 'N/A')}")

        loan = d.get("loan", {})
        if loan:
            lines.append(f"- **DTI:** {loan.get('dti', 'N/A'):.0%}" if isinstance(loan.get('dti'), float) else f"- **DTI:** {loan.get('dti', 'N/A')}")
            lines.append(f"- **Credit Score:** {loan.get('credit_score', 'N/A')}")
            lines.append(f"- **Loan Type:** {loan.get('loan_type', 'N/A')}")
            lines.append(f"- **Purpose:** {loan.get('purpose', 'N/A')}")
            lines.append(f"- **Race:** {loan.get('race', 'N/A')}")

        findings = d.get("findings", [])
        if findings:
            lines.append("- **Findings:**")
            for f in findings:
                lines.append(f"  - [{f.get('severity','').upper()}] {f.get('rule','')}: {f.get('finding','')}")

        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


# ── Build ──────────────────────────────────────────────────────────────────────

def _run_synix_command(args: list, timeout: int = 120) -> dict:
    """Run a synix CLI command from the memory directory."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "synix"] + args,
            cwd=str(MEMORY_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr or result.stdout}
        return {"success": True, "output": result.stdout}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"synix {args[0]} timed out after {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "error": "synix not found — run: pip install synix"}


def run_synix_build() -> dict:
    """Trigger incremental Synix build. Only layers downstream of changed sources rebuild."""
    return _run_synix_command(["build"], timeout=180)


def run_synix_release() -> dict:
    """Release the current build as 'local'. Materializes context.md and search.db."""
    return _run_synix_command(["release", "local"], timeout=60)


# ── Load ───────────────────────────────────────────────────────────────────────

def load_context_to_durable() -> str | None:
    """
    Read context.md from the Synix release and write it to the Aerospike durable tier.
    The compliance agent reads from this tier when building Claude prompts.
    """
    if not CONTEXT_FILE.exists():
        return None

    content = CONTEXT_FILE.read_text(encoding="utf-8")
    write_durable("synix_compliance_context", {
        "content": content,
        "loaded_at": time.time(),
        "source": str(CONTEXT_FILE),
        "char_count": len(content),
    })
    return content


def get_synix_context() -> str | None:
    """
    Return the current Synix compliance context for injection into Claude prompts.
    Reads from Aerospike durable tier (fast path) or falls back to disk.
    Returns None if no release exists yet (first run before any consolidation).
    """
    cached = read_durable("synix_compliance_context")
    if cached and cached.get("content"):
        return cached["content"]
    # Cold start: try loading from disk directly
    return load_context_to_durable()


# ── Search ─────────────────────────────────────────────────────────────────────

def query_compliance_memory(query: str, limit: int = 5) -> list[dict]:
    """
    Query the Synix search index for relevant compliance context.
    Uses the released search.db (SQLite FTS5 + semantic index).
    Returns list of {label, content, score} dicts.
    """
    search_db = RELEASE_DIR / "search.db"
    if not search_db.exists():
        return []

    try:
        from synix.sdk import Project
        project = Project(str(MEMORY_DIR))
        release = project.release("local")
        results = release.search("compliance_search", query, limit=limit)
        return [
            {"label": r.label, "content": r.content, "score": getattr(r, "score", None)}
            for r in results
        ]
    except Exception:
        # Synix SDK not available or release not found — return empty
        return []


# ── Main consolidation entry point ─────────────────────────────────────────────

def consolidate(hitl_decisions: list = None) -> dict:
    """
    Full consolidation pipeline:
      1. Read canonical HITL decisions from Ghost DB (source of truth)
      2. Export to Synix source files
      3. Run synix build (incremental)
      4. Run synix release local
      5. Load context.md into Aerospike durable tier

    Ghost DB is the source of record per architecture spec.
    hitl_decisions param is ignored — Ghost DB is always authoritative.
    """
    # Step 1: read from Ghost DB canonical log
    try:
        from agent.ghost_store import read_hitl_decisions
        ghost_decisions = read_hitl_decisions()
    except Exception as e:
        return {"success": False, "error": f"Ghost DB read failed: {e}"}

    if not ghost_decisions:
        return {"success": False, "error": "No HITL decisions in Ghost DB. Submit reviewer decisions first."}

    # Normalise Ghost DB rows to the format export_hitl_decisions expects
    normalised = [
        {
            "loan_id": d.get("loan_id"),
            "fingerprint": d.get("fingerprint"),
            "human_decision": d.get("decision"),
            "human_rationale": d.get("rationale"),
            "confidence": None,
            "loan": {},
            "findings": [],
        }
        for d in ghost_decisions
    ]

    # Step 2: export
    exported_file = export_hitl_decisions(normalised)

    # Step 2: build
    build_result = run_synix_build()
    if not build_result["success"]:
        return {
            "success": False,
            "stage": "build",
            "error": build_result["error"],
            "exported_file": str(exported_file),
        }

    # Step 3: release
    release_result = run_synix_release()
    if not release_result["success"]:
        return {
            "success": False,
            "stage": "release",
            "error": release_result["error"],
            "exported_file": str(exported_file),
        }

    # Step 4: load context into durable tier
    context = load_context_to_durable()

    return {
        "success": True,
        "exported_file": str(exported_file),
        "n_decisions": len(hitl_decisions),
        "context_loaded": context is not None,
        "context_chars": len(context) if context else 0,
        "build_output": build_result.get("output", "")[:500],  # truncate for API response
    }


def initial_build() -> dict:
    """
    Run the first-ever Synix build (no HITL decisions yet — rules corpus only).
    Call this during server startup if no release exists.
    """
    if CONTEXT_FILE.exists():
        # Already have a release — load it and return
        context = load_context_to_durable()
        return {"success": True, "skipped": True, "context_loaded": context is not None}

    build_result = run_synix_build()
    if not build_result["success"]:
        return build_result

    release_result = run_synix_release()
    if not release_result["success"]:
        return release_result

    context = load_context_to_durable()
    return {
        "success": True,
        "skipped": False,
        "context_loaded": context is not None,
        "context_chars": len(context) if context else 0,
    }
