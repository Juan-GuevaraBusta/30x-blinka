"""Application settings from environment mapping (no .env file load)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

BackendKind = Literal["jev", "plan_b"]

_ENV_KEYS: dict[str, str] = {
    "LLM_BASE_URL": "llm_base_url",
    "LLM_API_KEY": "llm_api_key",
    "EXTRACTOR_MODEL": "extractor_model",
    "VERIFIER_MODEL": "verifier_model",
    "POLISHER_MODEL": "polisher_model",
    "POLISHER_ENABLED": "polisher_enabled",
    "JEV_API_KEY": "jev_api_key",
    "JEV_BASE_URL": "jev_base_url",
    "JEV_MODEL": "jev_model",
    "DECISION_BACKEND": "decision_backend",
    "HTTP_TIMEOUT_SECONDS": "http_timeout_seconds",
    "LANGSMITH_TRACING": "langsmith_tracing",
    "LANGSMITH_API_KEY": "langsmith_api_key",
    "LANGSMITH_PROJECT": "langsmith_project",
    "LANGSMITH_ENDPOINT": "langsmith_endpoint",
}


class ConfigError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm_base_url: str = ""
    llm_api_key: str = ""
    extractor_model: str = ""
    verifier_model: str = ""
    polisher_model: str = ""
    polisher_enabled: bool = False
    jev_api_key: str = ""
    jev_base_url: str = "https://api.typesafe.ai"
    jev_model: str = "jev-latest"
    decision_backend: str = "auto"
    http_timeout_seconds: float = 30.0
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "blinka-invoice-agent-dev"
    langsmith_endpoint: str = ""

    @field_validator("llm_base_url", "jev_base_url", mode="before")
    @classmethod
    def strip_trailing_slash(cls, value: object) -> object:
        if isinstance(value, str):
            return value.rstrip("/")
        return value

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, str]) -> Settings:
        raw: dict[str, object] = {}
        for env_key, field_name in _ENV_KEYS.items():
            if env_key not in mapping:
                continue
            value = mapping[env_key]
            if field_name in ("polisher_enabled", "langsmith_tracing"):
                raw[field_name] = _parse_bool(value)
            elif field_name == "decision_backend":
                raw[field_name] = _parse_backend(value)
            elif field_name == "http_timeout_seconds":
                raw[field_name] = _parse_timeout(value)
            else:
                raw[field_name] = value
        return cls.model_validate(raw)


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ConfigError("invalid_bool")


def _parse_backend(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in ("auto", "jev", "plan_b"):
        return normalized
    raise ConfigError("invalid_backend")


def _parse_timeout(value: str) -> float:
    try:
        parsed = float(value.strip())
    except ValueError:
        raise ConfigError("invalid_timeout") from None
    if parsed <= 0:
        raise ConfigError("invalid_timeout")
    return parsed


def load_settings() -> Settings:
    return Settings.from_mapping(os.environ)


def resolve_backend(settings: Settings) -> BackendKind:
    backend = settings.decision_backend
    if backend == "jev":
        return "jev"
    if backend == "plan_b":
        return "plan_b"
    if settings.jev_api_key.strip():
        return "jev"
    return "plan_b"
