"""`app.api.metrics_summary_reader` — reads eval/reports/metrics_summary.json.

I9 discipline: missing/malformed file or missing/non-numeric entries never
fabricate a number -- the reader returns None (or an empty entries list),
never a 0.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.api.metrics_summary_reader import make_evidence_reader, make_metrics_reader


def test_metrics_reader_missing_file_returns_none(tmp_path: Path) -> None:
    reader = make_metrics_reader(tmp_path)

    assert reader() is None


def test_metrics_reader_malformed_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "eval" / "reports" / "metrics_summary.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")

    reader = make_metrics_reader(tmp_path)

    assert reader() is None


def test_metrics_reader_missing_required_entries_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "eval" / "reports" / "metrics_summary.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"entries": []}), encoding="utf-8")

    reader = make_metrics_reader(tmp_path)

    assert reader() is None


def test_metrics_reader_returns_numbers_from_entries(tmp_path: Path) -> None:
    path = tmp_path / "eval" / "reports" / "metrics_summary.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "id": "e2e_dev_unsafe_pay",
                        "label": "unsafe_pay e2e (dev)",
                        "value": 0,
                        "source": "eval/reports/verifier_tuning.md",
                    },
                    {
                        "id": "e2e_dev_autonomy",
                        "label": "Autonomía e2e (dev)",
                        "value": 55.9,
                        "source": "eval/reports/verifier_tuning.md",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    reader = make_metrics_reader(tmp_path)
    reading = reader()

    assert reading is not None
    assert reading.unsafe_pay == 0
    assert reading.autonomy_pct == 55.9


def test_metrics_reader_rejects_non_numeric_value(tmp_path: Path) -> None:
    path = tmp_path / "eval" / "reports" / "metrics_summary.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "id": "e2e_dev_unsafe_pay",
                        "label": "unsafe_pay",
                        "value": "pendiente",
                        "source": "x",
                    },
                    {
                        "id": "e2e_dev_autonomy",
                        "label": "autonomy",
                        "value": 10,
                        "source": "x",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    reader = make_metrics_reader(tmp_path)

    assert reader() is None


def test_evidence_reader_missing_file_returns_none(tmp_path: Path) -> None:
    reader = make_evidence_reader(tmp_path)

    assert reader() is None


def test_evidence_reader_filters_incomplete_entries(tmp_path: Path) -> None:
    path = tmp_path / "eval" / "reports" / "metrics_summary.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-10-18T00:00:00Z",
                "entries": [
                    {"id": "ok", "label": "Ok", "value": 1, "source": "x"},
                    {"id": "missing_source", "label": "Bad", "value": 1},
                ],
            }
        ),
        encoding="utf-8",
    )

    reader = make_evidence_reader(tmp_path)
    result = reader()

    assert result is not None
    entries, generated_at = result
    assert entries == [{"id": "ok", "label": "Ok", "value": 1, "source": "x"}]
    assert generated_at == "2026-10-18T00:00:00Z"
