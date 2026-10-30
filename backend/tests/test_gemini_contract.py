"""Official SDK HTTP contract tests with a mock transport. No provider quota consumed."""

import json
import httpx
from rgi.config import settings
from rgi.provider import Gemini, QuotaPause
import pytest


def make_client(monkeypatch):
    pytest.importorskip("google.genai")
    monkeypatch.setenv("RGI_GEMINI_API_KEY", "fake-test-key-never-a-real-secret")
    monkeypatch.setenv("RGI_FREE_TIER_ACK", "true")
    settings.cache_clear()


def test_official_sdk_structured_contract(isolated_settings, monkeypatch):
    make_client(monkeypatch)
    captured = []

    def respond(request):
        captured.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"summary":"Mock transport output"}'}],
                            "role": "model",
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 8, "totalTokenCount": 20},
            },
        )

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(respond))
    output, used, usage = Gemini().generate("plan", "test only", {}, 400)
    assert output.summary == "Mock transport output"
    assert used == 20 and usage["input_tokens"] == 12
    assert len(captured) == 1
    assert captured[0]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured[0]["generationConfig"]["maxOutputTokens"] == 400
    assert "tools" not in captured[0]


def test_429_pauses_without_sdk_retry_or_provider_switch(isolated_settings, monkeypatch):
    make_client(monkeypatch)
    calls = []

    def respond(request):
        calls.append(request.url)
        return httpx.Response(
            429,
            headers={"Retry-After": "120"},
            json={"error": {"code": 429, "message": "Mock quota exhausted", "status": "RESOURCE_EXHAUSTED"}},
        )

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(respond))
    with pytest.raises(QuotaPause):
        Gemini().generate("plan", "test only", {}, 400)
    assert len(calls) == 1
