import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
BLS_API_KEY = os.getenv("BLS_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GHOST_DB_URL = os.getenv("GHOST_DB_URL")
OVERMIND_API_KEY = os.getenv("OVERMIND_API_KEY")

# Aerospike
AEROSPIKE_HOST = os.getenv("AEROSPIKE_HOST", "localhost")
AEROSPIKE_PORT = int(os.getenv("AEROSPIKE_PORT", "3000"))
AEROSPIKE_NAMESPACE = os.getenv("AEROSPIKE_NAMESPACE", "test")

# Memory tier TTLs — set to 0 (never expire) for single-node dev/demo setup
# Aerospike requires nsup-period > 0 in the namespace config to use TTLs
EPHEMERAL_TTL = 0
SESSION_TTL = 0
