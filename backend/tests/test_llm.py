"""T3.1.3 — get_llm and LlmClient.complete_json."""

from __future__ import annotations

import json

import pytest
from app.config import ConfigError, Settings
from app.llm import DecisionClientError, HttpRequest, HttpResponse, get_llm

TEST_KEY = "test-key-not-secret"


def _base_settings(**overrides: str) -> Settings:
    env = {
        "LLM_BASE_URL": "https://llm.example.com",
        "LLM_API_KEY": TEST_KEY,
        "EXTRACTOR_MODEL": "extractor-v1",
        "VERIFIER_MODEL": "verifier-v1",
        "POLISHER_MODEL": "polisher-v1",
        **overrides,
    }
    return Settings.from_mapping(env)


def test_get_llm_unknown_role_raises() -> None:
    s = _base_settings()
    with pytest.raises(ConfigError) as exc:
        get_llm("jev", s)
    assert exc.value.code == "unknown_role"


def test_get_llm_polisher_disabled_raises_without_transport() -> None:
    s = _base_settings(POLISHER_ENABLED="false")
    calls = 0

    def transport(_: HttpRequest) -> HttpResponse:
        nonlocal calls
        calls += 1
        return HttpResponse(status=200, body=b"{}")

    with pytest.raises(ConfigError) as exc:
        get_llm("polisher", s, transport=transport)
    assert exc.value.code == "polisher_disabled"
    assert calls == 0


def test_get_llm_extractor_missing_model_raises() -> None:
    s = _base_settings(EXTRACTOR_MODEL="")
    with pytest.raises(ConfigError) as exc:
        get_llm("extractor", s, transport=lambda _: HttpResponse(status=200, body=b"{}"))
    assert exc.value.code == "missing_model"


def test_get_llm_extractor_happy_path_transport() -> None:
    s = _base_settings()
    seen: list[HttpRequest] = []

    def transport(req: HttpRequest) -> HttpResponse:
        seen.append(req)
        body = {
            "choices": [{"message": {"content": json.dumps({"ok": True})}}],
        }
        return HttpResponse(status=200, body=json.dumps(body).encode())

    client = get_llm("extractor", s, transport=transport)
    assert client.role == "extractor"
    assert client.model == "extractor-v1"
    result = client.complete_json("sys", "usr")
    assert result == {"ok": True}
    assert len(seen) == 1
    req = seen[0]
    assert req.method == "POST"
    assert req.url == "https://llm.example.com/chat/completions"
    assert req.headers["Authorization"] == f"Bearer {TEST_KEY}"
    payload = json.loads(req.body)
    assert payload["model"] == "extractor-v1"
    assert payload["temperature"] == 0
    assert payload["messages"][0]["content"] == "sys"
    assert payload["messages"][1]["content"] == "usr"


def test_complete_json_invalid_content_raises() -> None:
    s = _base_settings()

    def transport(_: HttpRequest) -> HttpResponse:
        body = {"choices": [{"message": {"content": "no es json"}}]}
        return HttpResponse(status=200, body=json.dumps(body).encode())

    client = get_llm("extractor", s, transport=transport)
    with pytest.raises(DecisionClientError) as exc:
        client.complete_json("s", "u")
    assert exc.value.code == "invalid_json"


def test_complete_json_array_raises_invalid_json() -> None:
    s = _base_settings()

    def transport(_: HttpRequest) -> HttpResponse:
        body = {"choices": [{"message": {"content": "[1, 2]"}}]}
        return HttpResponse(status=200, body=json.dumps(body).encode())

    client = get_llm("extractor", s, transport=transport)
    with pytest.raises(DecisionClientError) as exc:
        client.complete_json("s", "u")
    assert exc.value.code == "invalid_json"
