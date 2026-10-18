"""Unit tests for `backend/scripts/seed_demo.py` (T10).

A `FakeTransport` records every call and returns canned responses -- no real
sockets anywhere in this file, matching the "no network I/O at all in
dry-run mode" and "unit-testable without real sockets" requirements.
"""

from __future__ import annotations

import json

from scripts._demo_fixtures import (
    build_demo_agreements,
    build_demo_rules_config,
    pick_approver_email,
)

from scripts import seed_demo

BASE_URL = "http://localhost:8000"


class FakeTransport:
    """Records every call; returns a canned `HttpResult` or a 404 fallback."""

    def __init__(
        self, responses: dict[tuple[str, str], seed_demo.HttpResult] | None = None
    ) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, str, dict[str, str], object | None]] = []

    def __call__(
        self, method: str, url: str, headers: dict[str, str], body: object | None
    ) -> seed_demo.HttpResult:
        self.calls.append((method, url, dict(headers), body))
        return self.responses.get(
            (method, url), seed_demo.HttpResult(status_code=404, body={"detail": "not_found"})
        )


def _agreement_url(vendor_key: str) -> str:
    return f"{BASE_URL}/agreements/{vendor_key}"


def _active_agreement_body(vendor_key: str, terms_json: dict, confirmed_by: str) -> dict:
    active = {
        "vendor_key": vendor_key,
        "version": 1,
        "terms": terms_json,
        "source_sha256": None,
        "spans": {},
        "confirmed_by": confirmed_by,
        "confirmed_at": "2026-01-01T00:00:00Z",
        "status": "active",
    }
    return {"vendor_key": vendor_key, "active": active, "versions": [active]}


# --- (a) dry-run makes zero calls and prints the expected plan ---------------


def test_dry_run_makes_zero_calls_and_prints_plan(capsys) -> None:
    transport = FakeTransport()

    exit_code = seed_demo.main(["--base-url", BASE_URL], transport=transport, env={})

    assert exit_code == 0
    assert transport.calls == []
    out = capsys.readouterr().out
    assert "GET /agreements/globex" in out
    assert "PUT /agreements/globex" in out
    assert "GET /agreements/andesbyte" in out
    assert "GET /agreements/cuotasur" in out
    assert "/rules" not in out  # --with-rules was not passed


def test_dry_run_with_rules_includes_rules_calls(capsys) -> None:
    transport = FakeTransport()

    exit_code = seed_demo.main(
        ["--base-url", BASE_URL, "--with-rules"], transport=transport, env={}
    )

    assert exit_code == 0
    assert transport.calls == []
    out = capsys.readouterr().out
    assert "GET /rules" in out
    assert "PUT /rules" in out


# --- (b) --apply without --with-rules only touches /agreements/* -------------


def test_apply_without_with_rules_only_touches_agreements() -> None:
    transport = FakeTransport()

    exit_code = seed_demo.main(
        ["--base-url", BASE_URL, "--apply"],
        transport=transport,
        env={"ADMIN_API_KEY": "secret-key"},
    )

    assert exit_code == 0
    assert transport.calls  # something happened
    assert not any(url.endswith("/rules") for _m, url, _h, _b in transport.calls)
    for vendor_key in build_demo_agreements():
        urls = [url for _m, url, _h, _b in transport.calls]
        assert _agreement_url(vendor_key) in urls


# --- (c) a second --apply run against an already-matching transport skips ----


def test_apply_second_run_skips_everything_when_already_matching(capsys) -> None:
    demo_agreements = build_demo_agreements()
    demo_rules = build_demo_rules_config()
    confirmed_by = pick_approver_email()

    responses: dict[tuple[str, str], seed_demo.HttpResult] = {
        ("GET", f"{BASE_URL}/rules"): seed_demo.HttpResult(
            status_code=200, body=json.loads(demo_rules.model_dump_json())
        ),
    }
    for vendor_key, terms in demo_agreements.items():
        responses[("GET", _agreement_url(vendor_key))] = seed_demo.HttpResult(
            status_code=200,
            body=_active_agreement_body(
                vendor_key, json.loads(terms.model_dump_json()), confirmed_by
            ),
        )

    transport = FakeTransport(responses)
    exit_code = seed_demo.main(
        ["--base-url", BASE_URL, "--apply", "--with-rules"],
        transport=transport,
        env={"ADMIN_API_KEY": "secret-key"},
    )

    assert exit_code == 0
    puts = [url for method, url, _h, _b in transport.calls if method == "PUT"]
    assert puts == []  # every step reported "skip", never a duplicate PUT
    out = capsys.readouterr().out.lower()
    assert out.count("skip") >= 4  # rules + 3 vendors


def test_apply_upgrades_when_terms_differ_using_current_version() -> None:
    demo_agreements = build_demo_agreements()
    confirmed_by = pick_approver_email()
    vendor_key, _terms = next(iter(demo_agreements.items()))

    stale_terms = {
        "kind": "retainer",
        "vendor_name": "Globex LLC",
        "vendor_key": vendor_key,
        "department": None,
        "currency": "USD",
        "valid_from": "2025-01-01",
        "valid_to": None,
        "sender_emails": [],
        "source_clauses": {},
        "periodicity": "monthly",
        "amount": {"min": 1, "max": 1},
        "total_cap": None,
    }
    responses = {
        ("GET", _agreement_url(vendor_key)): seed_demo.HttpResult(
            status_code=200, body=_active_agreement_body(vendor_key, stale_terms, confirmed_by)
        ),
    }
    transport = FakeTransport(responses)

    exit_code = seed_demo.main(
        ["--base-url", BASE_URL, "--apply"],
        transport=transport,
        env={"ADMIN_API_KEY": "secret-key"},
    )

    assert exit_code == 0
    put_calls = [
        (url, body) for method, url, _h, body in transport.calls if method == "PUT"
    ]
    put_for_vendor = next(body for url, body in put_calls if url == _agreement_url(vendor_key))
    assert put_for_vendor["expected_version"] == 1  # the stale version, not 0


# --- (d) missing ADMIN_API_KEY in apply mode fails loudly, leaking nothing ---


def test_apply_missing_admin_key_fails_loudly_without_network() -> None:
    transport = FakeTransport()

    exit_code = seed_demo.main(["--base-url", BASE_URL, "--apply"], transport=transport, env={})

    assert exit_code != 0
    assert transport.calls == []


def test_admin_key_value_is_sent_but_never_printed(capsys) -> None:
    transport = FakeTransport()

    exit_code = seed_demo.main(
        ["--base-url", BASE_URL, "--apply"],
        transport=transport,
        env={"ADMIN_API_KEY": "super-secret-value"},
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "super-secret-value" not in captured.out
    assert "super-secret-value" not in captured.err
    put_calls = [headers for method, _url, headers, _body in transport.calls if method == "PUT"]
    assert put_calls  # at least one write happened
    assert all(headers.get("X-Admin-Key") == "super-secret-value" for headers in put_calls)
