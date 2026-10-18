"""eval/scenario_live.py wiring with a fake transport (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import scenario_live as sl


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.chain = 0

    def send(self, method, url, *, headers, json_body=None, form=None, files=None):
        self.calls.append((method, url, dict(headers)))
        if url.endswith("/verify-chain"):
            self.chain += 5
            return sl.Response(200, json.dumps({"ok": True, "length": self.chain}))
        if method == "POST" and url.endswith("/api/invoices"):
            text = files["file"][1].decode()
            decision, checks = "ESCALAR", [{"rule": "R06", "result": "INDETERMINADO"}]
            if "Zeta" in text:
                decision, checks = "FRENAR", [{"rule": "R01", "result": "FALLA"}]
            body = {
                "id": form["invoice_id"],
                "decision": decision,
                "checks": checks,
                "summary": "s",
                "trace": {"langsmith_run_id": None},
                "versions": {"rules_version": "v"},
                "extracted": {},
            }
            return sl.Response(201, json.dumps(body))
        if url.endswith("/approval"):
            return sl.Response(200, json.dumps({"required": 1, "collected": 1}))
        return sl.Response(404, json.dumps({"detail": "not_found"}))


def test_run_saves_raw_json_and_marks_mismatches(tmp_path: Path) -> None:
    fake = FakeTransport()
    s = sl.Scenario(fake, "https://web", "https://api", tmp_path, "T1")
    report = sl.run(s)

    assert "| 11 unknown vendor | FRENAR R01 | FRENAR | R01:FALLA | ok |" in report
    assert "MISMATCH" in report  # e.g. case 01 expected PAGAR
    assert (tmp_path / "report.md").is_file()
    assert any(p.name.endswith("_verify_chain_before.json") for p in tmp_path.iterdir())
    invoice_calls = [c for c in fake.calls if c[1].endswith("/api/invoices")]
    assert invoice_calls and all(c[2]["X-User-Id"] == "scenario-T1" for c in invoice_calls)
    # Admin actions go through the web proxy; only verify-chain hits the API host.
    assert {c[1] for c in fake.calls if c[1].startswith("https://api")} == {
        "https://api/decisions/verify-chain"
    }


def test_failing_rules_lists_non_ok_checks() -> None:
    rec = {"checks": [{"rule": "R01", "result": "OK"}, {"rule": "R05", "result": "FALLA"}]}
    assert sl.failing_rules(rec) == ["R05:FALLA"]
    assert sl.rule_ids(rec) == {"R05"}


def test_plan_only_does_not_touch_network() -> None:
    def boom() -> sl.Transport:
        raise AssertionError("no transport in plan mode")

    assert sl.main([], transport_factory=boom) == 0
