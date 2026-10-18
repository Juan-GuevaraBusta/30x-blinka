"""OpenAI-compatible chat completions for configured LLM roles."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.config import ConfigError, Settings

Role = Literal["extractor", "verifier", "polisher", "jev"]


class DecisionClientError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class HttpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["POST"]
    url: str
    headers: dict[str, str]
    body: bytes
    timeout_seconds: float


class HttpResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: int
    body: bytes


HttpTransport = Callable[[HttpRequest], HttpResponse]


class LlmClient:
    def __init__(
        self,
        role: str,
        model: str,
        settings: Settings,
        transport: HttpTransport,
    ) -> None:
        self.role = role
        self.model = model
        self._settings = settings
        self._transport = transport

    def complete_json(self, system: str, user: str) -> dict:
        url = f"{self._settings.llm_base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        request = HttpRequest(
            method="POST",
            url=url,
            headers={
                "Authorization": f"Bearer {self._settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            body=body_bytes,
            timeout_seconds=self._settings.http_timeout_seconds,
        )
        try:
            response = self._transport(request)
        except (TimeoutError, urllib.error.URLError):
            raise DecisionClientError("http_error") from None
        if response.status != 200:
            raise DecisionClientError("http_error")
        try:
            envelope = json.loads(response.body)
        except json.JSONDecodeError:
            raise DecisionClientError("http_error") from None
        try:
            content = envelope["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise DecisionClientError("invalid_json") from None
        if not isinstance(content, str):
            raise DecisionClientError("invalid_json")
        parsed = _parse_json_object_content(content)
        if parsed is None:
            raise DecisionClientError("invalid_json")
        return parsed


def get_llm(
    role: str,
    settings: Settings,
    *,
    transport: HttpTransport | None = None,
) -> LlmClient:
    if role not in ("extractor", "verifier", "polisher", "jev"):
        raise ConfigError("unknown_role")
    if role == "polisher" and not settings.polisher_enabled:
        raise ConfigError("polisher_disabled")
    model = _model_for_role(role, settings)
    if not settings.llm_api_key.strip():
        raise ConfigError("missing_llm_key")
    if not settings.llm_base_url.strip():
        raise ConfigError("missing_llm_base_url")
    effective_transport = transport if transport is not None else urllib_http_transport
    return LlmClient(role, model, settings, effective_transport)


def _model_for_role(role: Role, settings: Settings) -> str:
    if role == "extractor":
        model = settings.extractor_model
    elif role == "verifier":
        model = settings.verifier_model
    elif role == "jev":
        model = settings.jev_planb_model or settings.extractor_model
    else:
        model = settings.polisher_model
    if not model.strip():
        raise ConfigError("missing_model")
    return model


def model_for_role(role: Role, settings: Settings) -> str:
    """Public resolver, used to label which model backs a given LLM role."""
    return _model_for_role(role, settings)


def _strip_markdown_fence(content: str) -> str:
    """Remove one surrounding ```json ... ``` fence; some models add it despite the prompt."""
    text = content.strip()
    if not (text.startswith("```") and text.endswith("```")) or len(text) < 6:
        return content
    body = text[3:-3]
    first_newline = body.find("\n")
    if first_newline != -1 and body[:first_newline].strip().lower() in ("", "json"):
        body = body[first_newline + 1 :]
    return body


def _parse_json_object_content(content: str) -> dict | None:
    try:
        parsed = json.loads(_strip_markdown_fence(content))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def urllib_http_transport(request: HttpRequest) -> HttpResponse:
    req = urllib.request.Request(
        request.url,
        data=request.body,
        headers=request.headers,
        method=request.method,
    )
    with urllib.request.urlopen(req, timeout=request.timeout_seconds) as resp:
        status = getattr(resp, "status", 200)
        return HttpResponse(status=status, body=resp.read())
