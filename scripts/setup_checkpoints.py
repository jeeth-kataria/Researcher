"""Compatibility entrypoint: initializes the complete SQLite database."""
from rgi.db import initialize

initialize()
print("Local SQLite database and graph checkpoint schema ready")
