"""T3.1.1 — Settings, load_settings, resolve_backend."""

from __future__ import annotations

import pytest
from app.config import ConfigError, Settings, load_settings, resolve_backend


def test_settings_defaults_from_empty_mapping() -> None:
    s = Settings.from_mapping({})
    assert s.llm_base_url == ""
    assert s.llm_api_key == ""
    assert s.extractor_model == ""
    assert s.verifier_model == ""
    assert s.polisher_model == ""
    assert s.polisher_enabled is False
    assert s.jev_api_key == ""
    assert s.jev_base_url == "https://api.typesafe.ai"
    assert s.jev_model == "jev-latest"
    assert s.decision_backend == "auto"
    assert s.http_timeout_seconds == 30.0


def test_settings_ignores_unrelated_env_keys() -> None:
    s = Settings.from_mapping(
        {
            "PATH": "/usr/bin",
            "LANGSMITH_API_KEY": "should-not-appear",
            "EXTRACTOR_MODEL": "gpt-test",
        }
    )
    assert s.extractor_model == "gpt-test"
    assert not hasattr(s, "path")


def test_polisher_enabled_invalid_raises() -> None:
    with pytest.raises(ConfigError) as exc:
        Settings.from_mapping({"POLISHER_ENABLED": "yes"})
    assert exc.value.code == "invalid_bool"
    assert str(exc.value) == "invalid_bool"


def test_decision_backend_invalid_raises() -> None:
    with pytest.raises(ConfigError) as exc:
        Settings.from_mapping({"DECISION_BACKEND": "llm"})
    assert exc.value.code == "invalid_backend"


def test_http_timeout_zero_raises() -> None:
    with pytest.raises(ConfigError) as exc:
        Settings.from_mapping({"HTTP_TIMEOUT_SECONDS": "0"})
    assert exc.value.code == "invalid_timeout"


def test_llm_base_url_strips_trailing_slash() -> None:
    s = Settings.from_mapping({"LLM_BASE_URL": "https://api.example.com/"})
    assert s.llm_base_url == "https://api.example.com"


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"DECISION_BACKEND": "auto", "JEV_API_KEY": ""}, "plan_b"),
        ({"DECISION_BACKEND": "auto", "JEV_API_KEY": "  key  "}, "jev"),
        ({"DECISION_BACKEND": "jev", "JEV_API_KEY": ""}, "jev"),
        ({"DECISION_BACKEND": "plan_b", "JEV_API_KEY": "present"}, "plan_b"),
    ],
)
def test_resolve_backend(env: dict[str, str], expected: str) -> None:
    s = Settings.from_mapping(env)
    assert resolve_backend(s) == expected


def test_load_settings_reads_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXTRACTOR_MODEL", "from-env")
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    s = load_settings()
    assert s.extractor_model == "from-env"
