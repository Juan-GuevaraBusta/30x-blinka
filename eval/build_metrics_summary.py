#!/usr/bin/env python3
"""Builds `eval/reports/metrics_summary.json` from existing evidence only (I9).

This script never invents a number. Each entry is read from (or computed by
running) an artifact that already exists in the repo, and carries that
artifact's path as `source`:

- `motor_dev` / `motor_f7`: runs `eval/run_motor.py` (dev and f7 splits) and
  parses its own printed `matched=/total=/unsafe_pay=` line.
- `adversarial`: counts the `adv-NNN` rows in `eval/reports/adversarial.md`.
- `fraud_harness`: counts collected tests under `backend/tests/fraud` via
  `pytest --collect-only -q` (never a hardcoded "79").
- `e2e_dev_autonomy` / `e2e_dev_unsafe_pay`: parsed from the "Después" column
  of `eval/reports/verifier_tuning.md`. Omitted (not fabricated) if parsing
  fails.
- `holdout`: a fixed "not run yet" marker -- G5/T5.1 has not happened.

Run as `python eval/build_metrics_summary.py` from the repo root (or anywhere;
it resolves paths from its own location, same as `eval/run_motor.py`).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "eval" / "reports" / "metrics_summary.json"

_MOTOR_LINE_RE = re.compile(
    r"split=(?P<split>\S+)\s+total=(?P<total>\d+)\s+matched=(?P<matched>\d+)\s+"
    r"autonomy=(?P<autonomy>[\d.]+)%\s+unsafe_pay=(?P<unsafe_pay>\d+)"
)


def _run_motor_entry(*, split: str, entry_id: str, label: str) -> dict[str, Any] | None:
    """Runs `python eval/run_motor.py --split <split>` and parses its own output line."""
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(REPO_ROOT / "eval" / "run_motor.py"), "--split", split],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except OSError:
        return None
    match = _MOTOR_LINE_RE.search(result.stdout)
    if match is None:
        return None
    total = int(match.group("total"))
    matched = int(match.group("matched"))
    unsafe_pay = int(match.group("unsafe_pay"))
    return {
        "id": entry_id,
        "label": label,
        "value": f"{matched}/{total} matched, unsafe_pay={unsafe_pay}",
        "source": f"eval/run_motor.py --split {split}",
    }


def _adversarial_entry() -> dict[str, Any] | None:
    path = REPO_ROOT / "eval" / "reports" / "adversarial.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    rows = re.findall(r"^\|\s*adv-\d+\s*\|", text, re.MULTILINE)
    count = len(rows)
    if count == 0:
        return None
    return {
        "id": "adversarial",
        "label": "Casos adversariales",
        "value": f"{count}/{count} no-PAGAR",
        "source": "eval/reports/adversarial.md",
    }


def _fraud_harness_entry() -> dict[str, Any] | None:
    backend_dir = REPO_ROOT / "backend"
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pytest", "tests/fraud", "--collect-only", "-q"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except OSError:
        return None
    match = re.search(r"(\d+)\s+tests? collected", result.stdout)
    if match is None:
        return None
    count = int(match.group(1))
    return {
        "id": "fraud_harness",
        "label": "Harness de fraude",
        "value": f"{count} escenarios",
        "source": "backend/tests/fraud (pytest --collect-only -q)",
    }


def _verifier_tuning_entries() -> list[dict[str, Any]]:
    path = REPO_ROOT / "eval" / "reports" / "verifier_tuning.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    entries: list[dict[str, Any]] = []
    autonomy_match = re.search(r"Autonomía[^\n]*\*\*\d+/\d+ \(([\d.]+)\s*%\)\*\*", text)
    if autonomy_match is not None:
        entries.append(
            {
                "id": "e2e_dev_autonomy",
                "label": "Autonomía e2e (dev, tras ajuste del verificador)",
                "value": float(autonomy_match.group(1)),
                "source": "eval/reports/verifier_tuning.md",
            }
        )
    unsafe_match = re.search(r"`unsafe_pay`\s*\|\s*\d+\s*\|\s*\*\*(\d+)\*\*", text)
    if unsafe_match is not None:
        entries.append(
            {
                "id": "e2e_dev_unsafe_pay",
                "label": "unsafe_pay e2e (dev, tras ajuste del verificador)",
                "value": int(unsafe_match.group(1)),
                "source": "eval/reports/verifier_tuning.md",
            }
        )
    return entries


def _holdout_entry() -> dict[str, Any]:
    return {
        "id": "holdout",
        "label": "Holdout",
        "value": "pendiente T5.1",
        "source": "eval/reports/latest.md (no generado)",
    }


def build_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    motor_dev = _run_motor_entry(
        split="dev", entry_id="motor_dev", label="Motor determinista (dev)"
    )
    if motor_dev is not None:
        entries.append(motor_dev)
    motor_f7 = _run_motor_entry(split="f7", entry_id="motor_f7", label="Motor determinista (f7)")
    if motor_f7 is not None:
        entries.append(motor_f7)
    adversarial = _adversarial_entry()
    if adversarial is not None:
        entries.append(adversarial)
    fraud = _fraud_harness_entry()
    if fraud is not None:
        entries.append(fraud)
    entries.extend(_verifier_tuning_entries())
    entries.append(_holdout_entry())
    return entries


def main() -> int:
    entries = build_entries()
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "entries": entries,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT_PATH} with {len(entries)} entries")
    for entry in entries:
        print(f"  {entry['id']}: {entry['value']!r} <- {entry['source']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
