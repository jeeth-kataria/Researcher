"""Consistent SQLite online backup. Copy source files separately while worker is stopped."""
import argparse
import sqlite3
from pathlib import Path
from rgi.config import settings

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
source = settings().database_path.resolve()
destination = args.destination.resolve()
if not source.is_file():
    raise SystemExit("Initialize the database first")
if source == destination or destination.exists():
    raise SystemExit("Choose a new backup destination; existing files are never overwritten")
destination.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as reader:
    with sqlite3.connect(destination) as writer:
        reader.backup(writer)
print("Consistent SQLite backup created; preserve local PDF/artifact files separately")
