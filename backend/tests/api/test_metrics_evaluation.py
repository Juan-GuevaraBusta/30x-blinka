"""GET /metrics/evaluation — versioned evaluation evidence (I9: no report → empty)."""

from __future__ import annotations

from tests.api.support import build_client


def test_without_evidence_reader_is_empty() -> None:
    client, _store, _clock = build_client()

    response = client.get("/metrics/evaluation")

    assert response.status_code == 200
    assert response.json() == {"entries": [], "generated_at": None, "source": "none"}


def test_reader_returning_none_is_empty() -> None:
    client, _store, _clock = build_client(evidence_reader=lambda: None)

    response = client.get("/metrics/evaluation")

    assert response.status_code == 200
    assert response.json() == {"entries": [], "generated_at": None, "source": "none"}


def test_reader_entries_pass_through_with_source() -> None:
    entries = [
        {
            "id": "motor_dev",
            "label": "Motor determinista (dev)",
            "value": "33/34 matched, unsafe_pay=0",
            "source": "eval/run_motor.py --split dev",
        },
        {
            "id": "holdout",
            "label": "Holdout",
            "value": "pendiente T5.1",
            "source": "eval/reports/latest.md (no generado)",
        },
    ]

    def reader() -> tuple[list[dict], str | None]:
        return entries, "2026-10-18T00:00:00Z"

    client, _store, _clock = build_client(evidence_reader=reader)

    response = client.get("/metrics/evaluation")

    assert response.status_code == 200
    assert response.json() == {
        "entries": entries,
        "generated_at": "2026-10-18T00:00:00Z",
        "source": "report",
    }
