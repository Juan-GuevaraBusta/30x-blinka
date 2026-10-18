"""T9.8 (D067): company-based multi-tenancy."""

from __future__ import annotations

import json
import sqlite3

from app.api.production_processor import effective_rules_and_contracts
from app.api.schemas import InvoiceUpload
from app.api.store import MemoryStore
from app.api.tenancy import (
    DEMO_COMPANY_ID,
    UNCONFIGURED_SUMMARY_PREFIX,
    apply_unconfigured_guard,
)
from app.models.domain import DecisionRecord, Extraction
from app.persistence import SqlStore, init_database
from app.rules.checks import check_r08
from app.rules.context import RuleContext
from app.rules.fx import load_fx_table, rebase_fx_table
from sqlalchemy import create_engine
from tests.api.support import (
    ADMIN_HEADERS,
    RULES_PATH,
    build_client,
    load_rules,
    make_record,
    rules_payload,
)

_B = {"X-User-Id": "user-b", "X-User-Email": "boss@beta.test"}
_B2 = {"X-User-Id": "user-b2", "X-User-Email": "clerk@beta.test"}
_META = {"invoice_id": "INV-NEW-1", "channel": "chat", "received_at": "2026-03-04T10:00:00Z"}


def _pagar_processor(upload: InvoiceUpload, owner_id: str) -> DecisionRecord:
    return make_record(invoice_id=upload.invoice_id, decision="PAGAR", checks=[])


def _create_beta(client) -> dict:
    response = client.post(
        "/companies", json={"name": "Beta SAS", "base_currency": "EUR"}, headers=_B
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- onboarding ---------------------------------------------------------------------


def test_user_without_company_gets_null_me_and_403_on_scoped_endpoints() -> None:
    client, _store, _clock = build_client()

    me = client.get("/me", headers=_B)
    assert me.status_code == 200
    assert me.json()["company"] is None
    for path in ("/decisions", "/rules", "/agreements", "/rules/effective"):
        response = client.get(path, headers=_B)
        assert response.status_code == 403, path
        assert response.json() == {"detail": "no_company"}


def test_list_companies_includes_demo() -> None:
    client, _store, _clock = build_client()

    names = [c["name"] for c in client.get("/companies", headers=_B).json()]

    assert "P.J Gorman" in names


def test_create_company_makes_creator_admin_and_approver() -> None:
    client, _store, _clock = build_client()

    body = _create_beta(client)

    assert body["company"]["name"] == "Beta SAS"
    assert body["company"]["base_currency"] == "EUR"
    assert body["company"]["configured"] is False
    assert body["member"]["role"] == "admin"
    assert body["member"]["approver_groups"] == ["finanzas", "cfo"]
    assert client.get("/me", headers=_B).json()["company"]["id"] == body["company"]["id"]


def test_create_company_rejects_unsupported_currency() -> None:
    client, _store, _clock = build_client()

    response = client.post(
        "/companies", json={"name": "Gamma", "base_currency": "XYZ"}, headers=_B
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "unsupported_currency"}


def test_create_company_rejects_taken_normalized_name_and_second_company() -> None:
    client, _store, _clock = build_client()
    _create_beta(client)

    taken = client.post(
        "/companies", json={"name": "  beta   sas ", "base_currency": "USD"}, headers=_B2
    )
    second = client.post(
        "/companies", json={"name": "Otra", "base_currency": "USD"}, headers=_B
    )

    assert taken.status_code == 409
    assert taken.json() == {"detail": "company_name_taken"}
    assert second.status_code == 409
    assert second.json() == {"detail": "already_in_company"}


def test_create_company_requires_email() -> None:
    client, _store, _clock = build_client()

    response = client.post(
        "/companies", json={"name": "Gamma", "base_currency": "USD"},
        headers={"X-User-Id": "user-x"},
    )

    assert response.status_code == 422


def test_join_then_admin_promotes_member() -> None:
    client, _store, _clock = build_client()
    company_id = _create_beta(client)["company"]["id"]

    joined = client.post(f"/companies/{company_id}/join", headers=_B2)
    assert joined.status_code == 200
    assert joined.json()["member"]["role"] == "member"
    assert joined.json()["member"]["is_approver"] is False

    forbidden = client.patch(
        f"/companies/{company_id}/members/user-b",
        json={"role": "member"},
        headers=_B2,
    )
    assert forbidden.status_code == 403

    promoted = client.patch(
        f"/companies/{company_id}/members/user-b2",
        json={"approver_groups": ["finanzas"]},
        headers=_B,
    )
    assert promoted.status_code == 200
    assert promoted.json()["is_approver"] is True
    members = client.get(f"/companies/{company_id}/members", headers=_B).json()
    assert {m["user_id"] for m in members} == {"user-b", "user-b2"}


def test_members_of_other_company_are_hidden() -> None:
    client, _store, _clock = build_client()
    _create_beta(client)

    response = client.get(f"/companies/{DEMO_COMPANY_ID}/members", headers=_B)

    assert response.status_code == 403


def test_admin_members_endpoint_requires_admin_key() -> None:
    client, store, _clock = build_client()
    body = {
        "company_id": DEMO_COMPANY_ID,
        "user_id": "real-user",
        "email": "Real@Example.com",
        "role": "admin",
        "approver_groups": ["finanzas", "cfo"],
    }

    assert client.put("/admin/members", json=body).status_code == 401
    ok = client.put("/admin/members", json=body, headers=ADMIN_HEADERS)

    assert ok.status_code == 200
    member = store.membership("real-user")
    assert member is not None
    assert member.company_id == DEMO_COMPANY_ID
    assert member.email == "real@example.com"


# --- fail-closed for an unconfigured company ----------------------------------------


def test_new_company_gets_empty_draft_rules() -> None:
    client, _store, _clock = build_client()
    _create_beta(client)

    rules = client.get("/rules", headers=_B).json()

    assert rules["company"] == {"name": "Beta SAS", "base_currency": "EUR"}
    assert rules["allowed_beneficiaries"] == []
    assert rules["department_budgets"] == {}
    assert rules["approvers"] == {}
    assert rules["approval_policy"] is None
    assert rules["limits"] == rules_payload()["limits"]


def test_new_company_invoice_escalates_even_if_processor_says_pagar() -> None:
    client, store, _clock = build_client(processor=_pagar_processor)
    _create_beta(client)

    response = client.post(
        "/invoices", data=_META, files={"file": ("f.txt", b"x")}, headers=_B
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["decision"] == "ESCALAR"
    assert body["severity"] == 1
    assert body["summary"].startswith(UNCONFIGURED_SUMMARY_PREFIX)
    assert store.membership("user-b") is not None


def test_configured_company_is_not_forced_to_escalate() -> None:
    client, _store, _clock = build_client(processor=_pagar_processor)
    _create_beta(client)
    put = client.put(
        "/rules", json=rules_payload(), headers={**_B, **ADMIN_HEADERS}
    )
    assert put.status_code == 200
    # T9.8: base currency always comes from the company, not the body.
    assert put.json()["company"]["base_currency"] == "EUR"

    response = client.post(
        "/invoices", data=_META, files={"file": ("f.txt", b"x")}, headers=_B
    )

    assert response.json()["decision"] == "PAGAR"


def test_member_cannot_put_rules() -> None:
    client, _store, _clock = build_client()
    company_id = _create_beta(client)["company"]["id"]
    client.post(f"/companies/{company_id}/join", headers=_B2)

    response = client.put("/rules", json=rules_payload(), headers={**_B2, **ADMIN_HEADERS})

    assert response.status_code == 403
    assert response.json() == {"detail": "admin_required"}


def test_unconfigured_guard_only_raises_severity() -> None:
    frenar = make_record(decision="FRENAR")

    guarded = apply_unconfigured_guard(frenar)

    assert guarded.decision == "FRENAR"
    assert guarded.summary.startswith(UNCONFIGURED_SUMMARY_PREFIX)
    assert apply_unconfigured_guard(guarded).summary == guarded.summary


def test_production_rules_for_unconfigured_company_fail_closed() -> None:
    store = MemoryStore(load_rules())
    company = store.create_company(
        name="Beta", base_currency="USD", is_demo=False, created_by="u", at="t"
    )

    rules, contracts = effective_rules_and_contracts(store, company_id=company.id)  # type: ignore[arg-type]

    assert contracts == {}
    assert rules.on_fail.R01 == "ESCALAR"
    assert "Globex LLC" not in rules.allowed_beneficiaries
    assert rules.company.name == "Beta"


def test_effective_rules_use_company_row_name_for_r08() -> None:
    """T9.8: the `companies` row is the single source of truth for a
    configured company's name, even though its rules were seeded from the
    shared `data/rules.json` template (whose own `company.name` is frozen
    eval data and never changes -- it stays «Acme Demo Inc.» on disk). R08
    ("recipient is the company") must compare against *this* company's
    row ("P.J Gorman", the live demo company), not the template's baked-in
    name.
    """
    store = MemoryStore(load_rules())

    rules, _contracts = effective_rules_and_contracts(store, company_id=DEMO_COMPANY_ID)

    assert rules.company.name == "P.J Gorman"

    def _r08_for(recipient: str) -> str:
        ctx = RuleContext(
            rules=rules,
            fx_table=load_fx_table(),
            extraction=Extraction(recipient=recipient),
        )
        return check_r08(ctx).result

    assert _r08_for("P.J Gorman") == "OK"
    assert _r08_for("Acme Demo Inc.") == "FALLA"


# --- isolation --------------------------------------------------------------------


def test_company_b_cannot_read_or_approve_demo_decisions() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())
    _create_beta(client)

    assert client.get("/decisions", headers=_B).json() == []
    assert client.get("/decisions/dec_0042", headers=_B).status_code == 404
    assert client.get("/decisions/dec_0042/approval", headers=_B).status_code == 404
    approve = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "boss@beta.test", "reason": "intento cruzado"},
        headers={**_B, **ADMIN_HEADERS},
    )
    assert approve.status_code == 404
    assert store.decisions["dec_0042"].human_events == []


def test_demo_approver_email_is_not_an_approver_of_company_b() -> None:
    client, store, _clock = build_client(processor=lambda u, o: make_record(
        id="dec_b1", invoice_id=u.invoice_id
    ))
    _create_beta(client)
    client.post("/invoices", data=_META, files={"file": ("f.txt", b"x")}, headers=_B)

    as_demo_author = client.post(
        "/decisions/dec_b1/approve",
        json={"author": "cfo@demo.test", "reason": "no es de esta empresa"},
        headers={**_B, **ADMIN_HEADERS},
    )
    as_own_admin = client.post(
        "/decisions/dec_b1/approve",
        json={"author": "boss@beta.test", "reason": "Revisada"},
        headers={**_B, **ADMIN_HEADERS},
    )

    assert as_demo_author.status_code == 422
    assert as_demo_author.json() == {"detail": "unknown_approver"}
    assert as_own_admin.status_code == 200
    assert store.decisions["dec_b1"].human_events[0].author == "boss@beta.test"


def test_plain_member_cannot_approve_even_naming_an_approver() -> None:
    client, _store, _clock = build_client(processor=lambda u, o: make_record(
        id="dec_b2", invoice_id=u.invoice_id
    ))
    company_id = _create_beta(client)["company"]["id"]
    client.post(f"/companies/{company_id}/join", headers=_B2)
    client.post("/invoices", data=_META, files={"file": ("f.txt", b"x")}, headers=_B2)

    response = client.post(
        "/decisions/dec_b2/approve",
        json={"author": "boss@beta.test", "reason": "suplantando"},
        headers={**_B2, **ADMIN_HEADERS},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "approver_required"}


def test_teammates_share_company_decisions() -> None:
    client, _store, _clock = build_client(processor=lambda u, o: make_record(
        id="dec_b3", invoice_id=u.invoice_id
    ))
    company_id = _create_beta(client)["company"]["id"]
    client.post(f"/companies/{company_id}/join", headers=_B2)
    client.post("/invoices", data=_META, files={"file": ("f.txt", b"x")}, headers=_B2)

    assert [d["id"] for d in client.get("/decisions", headers=_B).json()] == ["dec_b3"]


# --- base currency --------------------------------------------------------------------


def test_fx_rebase_to_company_currency() -> None:
    table = load_fx_table(RULES_PATH.resolve().parent / "fx.json")

    eur = rebase_fx_table(table, "EUR")

    assert eur.base_currency == "EUR"
    assert eur.rates["EUR"] == 1.0
    assert abs(eur.rates["USD"] - 1 / 1.08) < 1e-9
    assert rebase_fx_table(table, "USD") is table


# --- SQL persistence and migration ------------------------------------------------------


def test_sql_store_companies_members_and_scoped_rules(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path}/t.sqlite")
    init_database(engine)
    init_database(engine)  # idempotent
    store = SqlStore(engine)
    store.put_rules(load_rules())
    company = store.create_company(
        name="Beta SAS", base_currency="EUR", is_demo=False, created_by="u", at="t"
    )
    store.add_member(
        company_id=company.id, user_id="u", email="u@b.test", role="admin",
        approver_groups=("finanzas",), at="t",
    )

    assert {c.id for c in store.list_companies()} == {DEMO_COMPANY_ID, company.id}
    assert store.membership("u").approver_groups == ("finanzas",)  # type: ignore[union-attr]
    assert store.rules_for(company.id) is None
    store.put_rules(load_rules(), company_id=company.id)
    assert store.rules_for(company.id) is not None
    assert store.rules.company.name == "Acme Demo Inc."
    store.add_decision(make_record(id="d1", invoice_id="I1"), "u", company_id=company.id)
    assert store.decisions_for(DEMO_COMPANY_ID) == {}
    assert list(store.decisions_for(company.id)) == ["d1"]
    assert store.verify_chain().ok


def test_migration_backfills_legacy_rows_to_demo_company(tmp_path) -> None:
    db = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE rules_document (id INTEGER PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE decision_record (
            id VARCHAR PRIMARY KEY, owner_id VARCHAR NOT NULL, invoice_id VARCHAR NOT NULL,
            decision VARCHAR NOT NULL, position INTEGER NOT NULL, payload TEXT NOT NULL,
            CONSTRAINT uq_decision_owner_invoice UNIQUE (owner_id, invoice_id));
        """
    )
    record = make_record()
    conn.execute(
        "INSERT INTO rules_document (id, payload) VALUES (1, ?)",
        (RULES_PATH.read_text(encoding="utf-8"),),
    )
    conn.execute(
        "INSERT INTO decision_record VALUES (?, 'legacy', ?, ?, 1, ?)",
        (record.id, record.invoice_id, record.decision, record.model_dump_json()),
    )
    conn.commit()
    conn.close()

    engine = create_engine(f"sqlite:///{db}")
    init_database(engine)
    init_database(engine)
    store = SqlStore(engine)

    assert store.get_company(DEMO_COMPANY_ID).name == "P.J Gorman"  # type: ignore[union-attr]
    assert list(store.decisions_for(DEMO_COMPANY_ID)) == [record.id]
    assert store.rules_for(DEMO_COMPANY_ID) is not None
    with engine.connect() as raw:
        nulls = raw.exec_driver_sql(
            "SELECT COUNT(*) FROM chain_entries WHERE company_id IS NULL"
        ).scalar()
        companies = raw.exec_driver_sql("SELECT COUNT(*) FROM companies").scalar()
    assert nulls == 0
    assert companies == 1
    assert json.loads(store.rules.model_dump_json())["company"]["base_currency"] == "USD"
