"""
Synix-inspired tiered memory layer backed by Aerospike.
Tiers: ephemeral, session, longitudinal, durable.
"""
import json
import time
import aerospike
from aerospike import exception as ex
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import AEROSPIKE_HOST, AEROSPIKE_PORT, AEROSPIKE_NAMESPACE, EPHEMERAL_TTL, SESSION_TTL

_client = None


def get_client():
    global _client
    if _client is None:
        config = {"hosts": [(AEROSPIKE_HOST, AEROSPIKE_PORT)]}
        _client = aerospike.client(config).connect()
    return _client


class MemoryTier:
    EPHEMERAL = "ephemeral"
    SESSION = "session"
    LONGITUDINAL = "longitudinal"
    DURABLE = "durable"


def _key(tier: str, name: str):
    return (AEROSPIKE_NAMESPACE, tier, name)


def write(tier: str, name: str, value: dict, ttl: int = 0):
    client = get_client()
    k = _key(tier, name)
    bins = {"value": json.dumps(value), "written_at": time.time()}
    meta = {"ttl": ttl}
    client.put(k, bins, meta=meta)


def read(tier: str, name: str) -> dict | None:
    client = get_client()
    try:
        _, _, bins = client.get(_key(tier, name))
        if bins and "value" in bins:
            return json.loads(bins["value"])
        return None
    except ex.RecordNotFound:
        return None


def append_list(tier: str, name: str, item: dict, max_len: int = 1000):
    """Append to a JSON-encoded list stored in a single record."""
    existing = read(tier, name) or []
    existing.insert(0, item)
    if len(existing) > max_len:
        existing = existing[:max_len]
    write(tier, name, existing)


def read_list(tier: str, name: str, limit: int = 100) -> list:
    data = read(tier, name)
    if data is None:
        return []
    if isinstance(data, list):
        return data[:limit]
    return []


def delete(tier: str, name: str):
    """Delete a record from Aerospike."""
    client = get_client()
    try:
        client.remove(_key(tier, name))
    except ex.RecordNotFound:
        pass


def clear_session():
    """Clear all session-tier keys used by a batch run."""
    for name in ("hitl_queue", "decision_log", "tool_call_log"):
        delete(MemoryTier.SESSION, name)
def write_ephemeral(name: str, value: dict):
    write(MemoryTier.EPHEMERAL, name, value, ttl=EPHEMERAL_TTL)

def write_session(name: str, value: dict):
    write(MemoryTier.SESSION, name, value, ttl=SESSION_TTL)

def write_longitudinal(name: str, value: dict):
    write(MemoryTier.LONGITUDINAL, name, value, ttl=0)

def write_durable(name: str, value: dict):
    write(MemoryTier.DURABLE, name, value, ttl=0)

def read_ephemeral(name: str) -> dict | None:
    return read(MemoryTier.EPHEMERAL, name)

def read_session(name: str) -> dict | None:
    return read(MemoryTier.SESSION, name)

def read_longitudinal(name: str) -> dict | None:
    return read(MemoryTier.LONGITUDINAL, name)

def read_durable(name: str) -> dict | None:
    return read(MemoryTier.DURABLE, name)
