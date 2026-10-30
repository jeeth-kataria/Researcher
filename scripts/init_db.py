"""Create/version the local SQLite schema and durable graph checkpoint tables."""
from rgi.db import initialize

initialize()
print("Local SQLite database, FTS5 index and graph checkpoint schema ready")
