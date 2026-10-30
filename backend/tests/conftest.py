import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    from rgi.config import settings

    monkeypatch.setenv("RGI_EMBEDDER", "fixture")
    monkeypatch.setenv("RGI_PARSER", "pypdf")
    monkeypatch.setenv("RGI_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("RGI_DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("RGI_GROQ_API_KEY", "")
    monkeypatch.setenv("RGI_GEMINI_API_KEY", "")
    monkeypatch.setenv("RGI_FREE_TIER_ACK", "false")
    monkeypatch.setenv("RGI_READ_ONLY", "false")
    monkeypatch.setenv("RGI_OWNER_TOKEN", "")
    settings.cache_clear()
    yield settings()
    settings.cache_clear()
