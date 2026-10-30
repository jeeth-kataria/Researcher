"""Isolated real SQLite/API/worker/Vite stack for the opt-in browser smoke test.

Every document/provider response is explicitly synthetic. No model download or LLM
credential is used. Services and state are independent of an owner's .env.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
state = ROOT / ".data" / "e2e" / str(uuid4())
state.mkdir(parents=True)
os.environ.update(
    RGI_DATABASE_PATH=str(state / "researcher.sqlite3"),
    RGI_STORAGE_DIR=str(state),
    RGI_PARSER="pypdf",
    RGI_EMBEDDER="fixture",
    RGI_READ_ONLY="false",
    RGI_OWNER_TOKEN="",
    RGI_GROQ_API_KEY="",
    RGI_GEMINI_API_KEY="",
    RGI_FREE_TIER_ACK="false",
)
sys.path.insert(0, str(ROOT / "backend"))
from rgi.db import initialize  # noqa: E402

initialize()
processes = []
stopping = False


def shutdown(*_):
    global stopping
    stopping = True
    for child in reversed(processes):
        if child.poll() is None:
            child.terminate()


signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)
try:
    for command, cwd in [
        ([sys.executable, "-m", "uvicorn", "rgi.api:app", "--host", "127.0.0.1", "--port", "8000"], ROOT),
        ([sys.executable, "-m", "rgi.worker"], ROOT),
        (["npm", "run", "dev", "--", "--port", "5173", "--strictPort"], ROOT / "frontend"),
    ]:
        processes.append(subprocess.Popen(command, cwd=cwd))
    while not stopping:
        if any(child.poll() is not None for child in processes):
            raise RuntimeError("An isolated test service exited unexpectedly")
        time.sleep(0.2)
finally:
    shutdown()
    for child in processes:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
