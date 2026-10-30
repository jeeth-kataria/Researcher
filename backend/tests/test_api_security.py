from fastapi.testclient import TestClient
from rgi.config import settings


def test_read_only_writes_and_owner_auth(isolated_settings, monkeypatch):
    monkeypatch.setenv("RGI_READ_ONLY", "true")
    settings.cache_clear()
    from rgi.api import app

    with TestClient(app) as client:
        assert client.post("/api/collections", json={"name": "unsafe"}).status_code == 403
        assert client.post("/api/runs", json={}).status_code == 403
        assert client.post("/api/runs/00000000-0000-0000-0000-000000000001/resume").status_code == 403
        monkeypatch.setenv("RGI_OWNER_TOKEN", "test-owner-secret")
        settings.cache_clear()
        assert client.get("/api/collections").status_code == 401
        assert (
            client.post(
                "/api/collections", headers={"Authorization": "Bearer wrong"}, json={"name": "x"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/collections", headers={"Authorization": "Bearer test-owner-secret"}, json={"name": "x"}
            ).status_code
            == 403
        )


def test_health_does_not_fabricate_worker_or_expose_secrets(isolated_settings, monkeypatch):
    from rgi import api

    def offline(*args):
        raise RuntimeError("database password=do-not-expose")

    monkeypatch.setattr(api, "one", offline)
    with TestClient(api.app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["database"] == "unavailable"
        assert not response.json()["worker"]["online"]
        assert "do-not-expose" not in response.text


def test_provider_never_falls_back(isolated_settings):
    from rgi.provider import provider, ConfigurationPause
    import pytest

    with pytest.raises(ConfigurationPause):
        provider("gemini")
    with pytest.raises(ConfigurationPause):
        provider("some-paid-service")
