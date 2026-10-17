"""T0.1.2 — Smoke test: required repo scaffold paths exist (paths relative to repo root)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS: tuple[str, ...] = (
    "AGENTS.md",
    ".env.example",
    "backend/app/rules/",
    "backend/app/gate/",
    "backend/app/models/",
    "backend/app/graph/",
    "backend/app/api/",
    "backend/tests/rules/",
    "backend/tests/api/",
    "backend/tests/gate/",
    "backend/tests/adversarial/",
    "data/contracts/",
    "data/invoices/dev/",
    "data/invoices/holdout/",
    "data/golden/",
    "eval/reports/",
    "frontend/",
)

_REAL_SECRET_VALUE = re.compile(
    r"=\s*(?:sk-[a-zA-Z0-9]{8,}|lsv2_[a-zA-Z0-9]{8,})\s*(?:#.*)?$"
)


@pytest.mark.parametrize("relative_path", REQUIRED_PATHS, ids=lambda p: p.rstrip("/"))
def test_repo_scaffold_path_exists(relative_path: str) -> None:
    path = REPO_ROOT / relative_path
    assert path.exists(), f"Missing scaffold path: {relative_path}"


def test_env_example_langsmith_key_without_real_secrets() -> None:
    content = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "LANGSMITH_API_KEY" in content
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _REAL_SECRET_VALUE.search(stripped):
            pytest.fail(f".env.example must not contain real-looking secret values: {stripped}")
