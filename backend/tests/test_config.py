"""Project configuration remains stable when a CLI is launched from scripts/."""

from rgi.config import PROJECT_ROOT, Settings


def test_env_and_relative_data_paths_do_not_depend_on_terminal_folder(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "RGI_GROQ_API_KEY=fake-test-key\nRGI_FREE_TIER_ACK=true\nRGI_DATABASE_PATH=.data/test.sqlite3\nRGI_STORAGE_DIR=.data/test-storage\n"
    )
    monkeypatch.setitem(Settings.model_config, "env_file", env)
    for key in ("RGI_GROQ_API_KEY", "RGI_FREE_TIER_ACK", "RGI_DATABASE_PATH", "RGI_STORAGE_DIR"):
        monkeypatch.delenv(key, raising=False)
    root = Settings()
    elsewhere = tmp_path / "scripts"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    nested = Settings()
    assert nested.groq_api_key == root.groq_api_key == "fake-test-key"
    assert nested.free_tier_ack is True
    assert nested.database_path == root.database_path == PROJECT_ROOT / ".data/test.sqlite3"
    assert nested.storage_dir == root.storage_dir == PROJECT_ROOT / ".data/test-storage"


def test_environment_overrides_dotenv(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("RGI_GROQ_API_KEY=fake-file-key\n")
    monkeypatch.setenv("RGI_GROQ_API_KEY", "fake-environment-key")
    assert Settings(_env_file=env).groq_api_key == "fake-environment-key"
