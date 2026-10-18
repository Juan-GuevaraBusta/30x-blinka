"""Reads the committed `eval/reports/metrics_summary.json` (T-metrics follow-up).

Resolved relative to `data_root`, never to this module's own path -- the same
site-packages problem `production_processor.py` documents for `fx.json`: once
the backend package is installed, `Path(__file__)` lives under
`site-packages/app/api/`, not the repo, so the file would never be found.

I9 discipline: a missing or malformed file returns `None`/empty, never a
fabricated number. This module only reads; it never runs `eval/run_motor.py`
or any other script.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.api.schemas import MetricsReading

_SUMMARY_RELATIVE_PATH = Path("eval") / "reports" / "metrics_summary.json"


def _load_summary(data_root: Path) -> dict[str, Any] | None:
    path = data_root / _SUMMARY_RELATIVE_PATH
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("entries"), list):
        return None
    return payload


def _entry_value(payload: dict[str, Any], entry_id: str) -> Any | None:
    for entry in payload.get("entries", []):
        if isinstance(entry, dict) and entry.get("id") == entry_id:
            return entry.get("value")
    return None


def _is_plain_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def make_metrics_reader(data_root: Path) -> Callable[[], MetricsReading | None]:
    """Reader for `GET /metrics` (unsafe_pay/autonomy_pct only, I9: never 0 by default)."""

    def _read() -> MetricsReading | None:
        payload = _load_summary(data_root)
        if payload is None:
            return None
        unsafe_pay = _entry_value(payload, "e2e_dev_unsafe_pay")
        autonomy_pct = _entry_value(payload, "e2e_dev_autonomy")
        if not _is_plain_number(unsafe_pay) or not _is_plain_number(autonomy_pct):
            return None
        return MetricsReading(unsafe_pay=unsafe_pay, autonomy_pct=autonomy_pct)

    return _read


def make_evidence_reader(
    data_root: Path,
) -> Callable[[], tuple[list[dict[str, Any]], str | None] | None]:
    """Reader for `GET /metrics/evaluation` (full versioned entries list)."""

    def _read() -> tuple[list[dict[str, Any]], str | None] | None:
        payload = _load_summary(data_root)
        if payload is None:
            return None
        cleaned: list[dict[str, Any]] = []
        for entry in payload.get("entries", []):
            if not isinstance(entry, dict):
                continue
            if not {"id", "label", "value", "source"} <= entry.keys():
                continue
            cleaned.append(
                {
                    "id": entry["id"],
                    "label": entry["label"],
                    "value": entry["value"],
                    "source": entry["source"],
                }
            )
        generated_at = payload.get("generated_at")
        return cleaned, generated_at if isinstance(generated_at, str) else None

    return _read
