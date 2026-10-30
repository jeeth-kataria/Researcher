from pathlib import Path
from typing import Literal
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RGI_", env_file=".env", extra="ignore")
    database_url: str = "postgresql://rgi:rgi@127.0.0.1:5433/rgi"
    storage_dir: Path = Path(".data")
    read_only: bool = False
    owner_token: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    parser: Literal["docling", "pypdf"] = "docling"
    embedder: Literal["bge", "fixture"] = "bge"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    free_tier_ack: bool = False
    max_upload_mb: int = 20
    max_papers: int = 50
    lease_seconds: int = 120
    max_attempts: int = 3


@lru_cache
def settings() -> Settings:
    return Settings()


def configure_model_cache():
    """Keep first-use model caches local; respect explicitly configured cache paths."""
    import os

    root = settings().storage_dir.resolve() / "models"
    os.environ.setdefault("HF_HOME", str(root / "huggingface"))
    os.environ.setdefault("TORCH_HOME", str(root / "torch"))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    return root
