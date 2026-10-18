"""T7.1 (D059) §4 — «x de N» approvals, route eligibility, and GET .../approval.

Approval never rewrites `decision` (I2); it is recorded as an appended
`HumanEvent` on the T5.10 hash chain. These tests cover the route-specific
validations that only kick in when the record carries an R14 FALLA, plus the
unchanged legacy flow for records without a policy.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.api.support import ADMIN_HEADERS, build_client, make_record

R04_OK = {
    "rule": "R04",
    "name": "Aprobación humana por monto",
    "result": "OK",
    "detail": "USD 4.200 llega al umbral de aprobación humana.",
}
R04_FALLA = {
    "rule": "R04",
    "name": "Aprobación humana por monto",
    "result": "FALLA",
    "detail": "USD 4.200 llega al umbral de aprobación humana.",
    "on_fail": "ESCALAR",
}
R14_TWO_OF_FINANZAS_CFO = {
    "rule": "R14",
    "name": "Política de aprobación",
    "result": "FALLA",
    "detail": 'Ruta "alto-monto": requiere 2 aprobaciones de finanzas o cfo.',
    "on_fail": "ESCALAR",
    "evidence": {"clause": "alto-monto", "quote": "min_approvals=2;groups=cfo,finanzas"},
}
R14_ONE_OF_CFO = {
    "rule": "R14",
    "name": "Política de aprobación",
    "result": "FALLA",
    "detail": 'Ruta "marketing-cfo": requiere 1 aprobaciones de cfo.',
    "on_fail": "ESCALAR",
    "evidence": {"clause": "marketing-cfo", "quote": "min_approvals=1;groups=cfo"},
}
R07_FALLA = {
    "rule": "R07",
    "name": "Presupuesto del departamento",
    "result": "FALLA",
    "detail": "Presupuesto restante de Marketing insuficiente.",
    "on_fail": "FRENAR",
}


def _record_with_r14(checks: list[dict[str, object]], **kwargs: object) -> object:
    return make_record(checks=checks, **kwargs)


# --- GET /decisions/{id}/approval: records without a policy (unchanged flow) ------


def test_approval_status_without_r14_reports_required_one() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA]))

    response = client.get("/decisions/dec_0042/approval")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "route_id": None,
        "required": 1,
        "collected": 0,
        "approvers": [],
        "satisfied": False,
        "rejected": False,
        "payment_ready": False,
        "pending_checks": [],
    }


def test_approval_status_without_r14_satisfied_after_one_approval() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA]))
    client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "ok"},
        headers=ADMIN_HEADERS,
    )

    response = client.get("/decisions/dec_0042/approval")

    body = response.json()
    assert body["collected"] == 1
    assert body["satisfied"] is True
    assert body["payment_ready"] is True


def test_approval_status_missing_decision_returns_404(client: TestClient) -> None:
    response = client.get("/decisions/missing/approval")
    assert response.status_code == 404


# --- Route-based policy: two distinct approvals satisfy a 2-approval route --------


def test_two_distinct_eligible_approvals_satisfy_route_of_two() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_TWO_OF_FINANZAS_CFO]))

    first = client.get("/decisions/dec_0042/approval").json()
    assert first == {
        "route_id": "alto-monto",
        "required": 2,
        "collected": 0,
        "approvers": [],
        "satisfied": False,
        "rejected": False,
        "payment_ready": False,
        "pending_checks": [],
    }

    r1 = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "finanzas@demo.test", "reason": "cumple politica"},
        headers=ADMIN_HEADERS,
    )
    assert r1.status_code == 200

    mid = client.get("/decisions/dec_0042/approval").json()
    assert mid["collected"] == 1
    assert mid["approvers"] == ["finanzas@demo.test"]
    assert mid["satisfied"] is False
    assert mid["payment_ready"] is False

    r2 = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "segunda aprobacion"},
        headers=ADMIN_HEADERS,
    )
    assert r2.status_code == 200

    final = client.get("/decisions/dec_0042/approval").json()
    assert final["collected"] == 2
    assert sorted(final["approvers"]) == ["cfo@demo.test", "finanzas@demo.test"]
    assert final["satisfied"] is True
    assert final["payment_ready"] is True


def test_payment_ready_false_while_another_check_still_fails() -> None:
    client, store, _clock = build_client()
    store.add_decision(
        make_record(checks=[R04_FALLA, R14_ONE_OF_CFO, R07_FALLA], decision="ESCALAR")
    )

    client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "aprueba cfo"},
        headers=ADMIN_HEADERS,
    )

    status = client.get("/decisions/dec_0042/approval").json()
    assert status["satisfied"] is True
    assert status["pending_checks"] == ["R07"]
    assert status["payment_ready"] is False


def test_same_author_approving_twice_returns_409() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_TWO_OF_FINANZAS_CFO]))
    client.post(
        "/decisions/dec_0042/approve",
        json={"author": "finanzas@demo.test", "reason": "primera"},
        headers=ADMIN_HEADERS,
    )

    response = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "finanzas@demo.test", "reason": "repetida"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "already_approved"}


def test_author_outside_route_groups_returns_422() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_ONE_OF_CFO]))

    response = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "finanzas@demo.test", "reason": "no es cfo"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "approver_not_in_route"}


def test_approve_after_route_satisfied_returns_409_approval_closed() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_ONE_OF_CFO]))
    client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "aprueba"},
        headers=ADMIN_HEADERS,
    )

    response = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "de nuevo"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] in {"already_approved", "approval_closed"}


def test_reject_after_route_satisfied_returns_409_approval_closed() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_ONE_OF_CFO]))
    client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "aprueba"},
        headers=ADMIN_HEADERS,
    )

    response = client.post(
        "/decisions/dec_0042/reject",
        json={"author": "cfo@demo.test", "reason": "tarde"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "approval_closed"


def test_reject_closes_route_and_blocks_further_approvals() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_TWO_OF_FINANZAS_CFO]))

    rejected = client.post(
        "/decisions/dec_0042/reject",
        json={"author": "cfo@demo.test", "reason": "no corresponde"},
        headers=ADMIN_HEADERS,
    )
    assert rejected.status_code == 200

    status = client.get("/decisions/dec_0042/approval").json()
    assert status["rejected"] is True
    assert status["payment_ready"] is False

    blocked = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "finanzas@demo.test", "reason": "tarde"},
        headers=ADMIN_HEADERS,
    )
    assert blocked.status_code == 409
    assert blocked.json() == {"detail": "approval_closed"}


def test_approve_unknown_author_still_returns_422_before_route_checks() -> None:
    """Global `data/company.json` approvers allowlist still gates first (unchanged)."""
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_ONE_OF_CFO]))

    response = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "intruder@example.com", "reason": "no autorizado"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "unknown_approver"}


R14_INDETERMINADO = {
    "rule": "R14",
    "name": "Política de aprobación",
    "result": "INDETERMINADO",
    "detail": "No se pudo resolver la ruta de la política: falta el departamento.",
    "on_fail": "ESCALAR",
}


def test_indeterminate_r14_never_reports_satisfied_or_payment_ready() -> None:
    # Fail-closed (I3): an unresolved route must not fall back to "1 approval
    # from anyone"; the required route could have demanded 2 from cfo/finanzas.
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_INDETERMINADO]))

    response = client.get("/decisions/dec_0042/approval")

    body = response.json()
    assert body["satisfied"] is False
    assert body["payment_ready"] is False
    assert "R14" in body["pending_checks"]


def test_indeterminate_r14_blocks_approve_but_allows_reject() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R04_FALLA, R14_INDETERMINADO]))

    approve = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "ok"},
        headers=ADMIN_HEADERS,
    )
    status = client.get("/decisions/dec_0042/approval").json()
    reject = client.post(
        "/decisions/dec_0042/reject",
        json={"author": "cfo@demo.test", "reason": "no"},
        headers=ADMIN_HEADERS,
    )

    assert approve.status_code == 409
    assert approve.json()["detail"] == "policy_route_unresolved"
    assert status["payment_ready"] is False
    assert reject.status_code == 200


R06_VARIABLE = {
    "rule": "R06",
    "name": "Cuadra con contrato",
    "result": "INDETERMINADO",
    "detail": "Acuerdo de pago variable: no hay tarifa fija.",
    "on_fail": "ESCALAR",
}
R19_VARIABLE = {
    "rule": "R19",
    "name": "Cuadra con la fórmula pactada",
    "result": "INDETERMINADO",
    "detail": "Elemento variable de un acuerdo: requiere revisión humana.",
    "on_fail": "ESCALAR",
}


def test_human_approval_resolves_escalation_only_reasons() -> None:
    # Demo case: a variable agreement escalates via R06/R19 INDETERMINADO; the
    # human approval is exactly what resolves them, so payment becomes ready.
    client, store, _clock = build_client()
    store.add_decision(make_record(checks=[R06_VARIABLE, R19_VARIABLE]))
    client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "Horas revisadas"},
        headers=ADMIN_HEADERS,
    )

    body = client.get("/decisions/dec_0042/approval").json()

    assert body["satisfied"] is True
    assert body["pending_checks"] == []
    assert body["payment_ready"] is True
