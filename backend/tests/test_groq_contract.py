"""Actual Groq SDK + mock HTTP transport, never a live API/quality claim."""

import json
from datetime import datetime, timezone
import httpx
import pytest
from rgi.config import settings
from rgi.provider import Groq, QuotaPause, ConfigurationPause, groq_schema
from rgi.schemas import RoleOutput


def client(monkeypatch, respond):
    import groq

    monkeypatch.setenv("RGI_GROQ_API_KEY", "fake-test-key-not-a-secret")
    monkeypatch.setenv("RGI_FREE_TIER_ACK", "true")
    settings.cache_clear()
    actual_client = groq.Groq
    monkeypatch.setattr(
        groq,
        "Groq",
        lambda **kwargs: actual_client(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond))
        ),
    )
    return Groq()


def test_primary_defaults_and_strict_schema(isolated_settings):
    from rgi.schemas import RunInput
    from uuid import uuid4

    assert RunInput(collection_id=uuid4(), question="What remains unresolved?").provider == "groq"
    schema = groq_schema()
    assert set(schema["required"]) == set(RoleOutput.model_fields)

    def check(node):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
            for prop in node["properties"].values():
                check(prop)
        if "items" in node:
            check(node["items"])

    check(schema)


def test_structured_request_usage_and_pinned_run_model(isolated_settings, monkeypatch):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "mock",
                "object": "chat.completion",
                "created": 0,
                "model": "openai/gpt-oss-120b",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": RoleOutput(summary="SDK mock").model_dump_json(),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 17, "completion_tokens": 12, "total_tokens": 29},
            },
        )

    generator = client(monkeypatch, respond)
    monkeypatch.setenv("RGI_GROQ_MODEL", "openai/gpt-oss-20b")
    settings.cache_clear()
    output, used, usage = generator.generate("plan", "fixture context", {}, 400)
    assert output.summary == "SDK mock" and used == 29 and usage["input_tokens"] == 17
    assert len(calls) == 1
    assert calls[0]["model"] == "openai/gpt-oss-120b"
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert calls[0]["max_completion_tokens"] == 400
    assert "tools" not in calls[0] and "stream" not in calls[0]


def test_generated_schema_failure_keeps_outcome_uncertain(isolated_settings, monkeypatch):
    from rgi.provider import AmbiguousCall

    calls = []

    def respond(request):
        calls.append(request.url)
        return httpx.Response(
            400, json={"error": {"message": "mock generated failure", "code": "json_validate_failed"}}
        )

    with pytest.raises(AmbiguousCall):
        client(monkeypatch, respond).generate("plan", "test", {}, 400)
    assert len(calls) == 1


def test_groq_429_one_request_and_retry_after(isolated_settings, monkeypatch):
    calls = []

    def respond(request):
        calls.append(request.url)
        return httpx.Response(
            429,
            headers={"retry-after": "120"},
            json={"error": {"message": "mock quota", "type": "rate_limit_error"}},
        )

    generator = client(monkeypatch, respond)
    with pytest.raises(QuotaPause) as raised:
        generator.generate("plan", "test", {}, 400)
    assert len(calls) == 1
    assert (raised.value.retry_at - datetime.now(timezone.utc)).total_seconds() > 110


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413, 422])
def test_known_rejection_no_sdk_retry_or_fallback(isolated_settings, monkeypatch, status):
    calls = []

    def respond(request):
        calls.append(request.url)
        return httpx.Response(status, json={"error": {"message": "mock rejection"}})

    with pytest.raises(ConfigurationPause):
        client(monkeypatch, respond).generate("plan", "test", {}, 400)
    assert len(calls) == 1
