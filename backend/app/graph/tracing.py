"""Best-effort LangSmith session. A trace failure never changes the payment."""

from __future__ import annotations

from typing import Protocol

from app.config import Settings
from app.models.domain import TraceRef


class TraceSession(Protocol):
    def open_config(self, *, metadata: dict[str, str], tags: list[str]) -> dict: ...

    def finish(self, decision: str) -> TraceRef | None: ...


class NullTrace:
    """open_config returns {}. finish returns None. Does not raise."""

    def open_config(self, *, metadata: dict[str, str], tags: list[str]) -> dict:
        return {}

    def finish(self, decision: str) -> TraceRef | None:
        return None


class _LangSmithSession:
    """SDK session. Constructed only when tracing is on and a key is set."""

    def __init__(self, settings: Settings) -> None:
        from langchain_core.tracers.langchain import LangChainTracer
        from langsmith import Client

        client_kwargs: dict[str, str] = {"api_key": settings.langsmith_api_key}
        endpoint = settings.langsmith_endpoint.strip()
        if endpoint:
            client_kwargs["api_url"] = endpoint
        self._client = Client(**client_kwargs)
        self._tracer = LangChainTracer(
            project_name=settings.langsmith_project,
            client=self._client,
        )
        self._failed = False

    def open_config(self, *, metadata: dict[str, str], tags: list[str]) -> dict:
        if self._failed:
            return {}
        try:
            return {
                "callbacks": [self._tracer],
                "metadata": dict(metadata),
                "tags": list(tags),
            }
        except Exception:
            self._failed = True
            return {}

    def finish(self, decision: str) -> TraceRef | None:
        if self._failed:
            return None
        try:
            run = self._tracer.latest_run
            if run is None:
                return None
            root_id = run.trace_id or run.id
            url = getattr(run, "url", None)
            if not isinstance(url, str) or not url:
                url = None
            return TraceRef(langsmith_run_id=str(root_id), url=url)
        except Exception:
            return None


def make_langsmith_session(settings: Settings) -> TraceSession:
    """Tracing off or blank key: NullTrace, and no LangSmith client."""
    if not settings.langsmith_tracing or not settings.langsmith_api_key.strip():
        return NullTrace()
    try:
        return _LangSmithSession(settings)
    except Exception:
        return NullTrace()
