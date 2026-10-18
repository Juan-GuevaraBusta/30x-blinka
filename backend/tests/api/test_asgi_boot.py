"""Production ASGI factory (T4.9): SQLite boot, URL rewrite, CORS guard. No sockets."""

from __future__ import annotations

import json

import pytest
from app.api.asgi import (
    InvalidCorsOriginsError,
    UnsupportedDatabaseUrlError,
    create_production_app,
    load_approver_emails,
    load_approver_groups,
    prepare_database_url,
)
from app.models.rules_config import RulesConfig, load_rules_config
from app.persistence import SqlStore, init_database, seed_rules
from app.persistence.tables import RulesDocument
from app.rules.approval_policy import ApprovalPolicyGroupError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tests.api.support import ADMIN_HEADERS, COMPANY_PATH, RULES_PATH, TEST_ADMIN_KEY


def test_postgresql_scheme_rewritten_without_connecting() -> None:
    url = prepare_database_url("postgresql://demo.example/blinka")

    assert url.startswith("postgresql+psycopg://")
    assert "demo.example" in url
    assert "sslmode=require" in url


def test_render_internal_host_skips_sslmode() -> None:
    url = prepare_database_url("postgresql://user:pass@dpg-abc123-a/blinka")

    assert url.startswith("postgresql+psycopg://")
    assert "sslmode" not in url


def test_factory_sqlite_seed_get_put(tmp_path) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}", "ADMIN_API_KEY": TEST_ADMIN_KEY}
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    got = client.get("/rules")
    assert got.status_code == 200
    body = got.json()
    assert body["human_approval_threshold"] == 3000.0

    updated = {**body, "human_approval_threshold": 2500.0}
    put = client.put("/rules", json=updated, headers=ADMIN_HEADERS)
    assert put.status_code == 200
    assert put.json()["human_approval_threshold"] == 2500.0

    again = client.get("/rules")
    assert again.json()["human_approval_threshold"] == 2500.0


def test_second_seed_does_not_overwrite_put(tmp_path) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}", "ADMIN_API_KEY": TEST_ADMIN_KEY}
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    client = TestClient(app)
    base = client.get("/rules").json()
    custom = {**base, "human_approval_threshold": 2500.0}
    client.put("/rules", json=custom, headers=ADMIN_HEADERS)

    store = SqlStore(create_engine(mapping["DATABASE_URL"]))
    seeded_again = seed_rules(store, RULES_PATH)

    assert seeded_again.human_approval_threshold == 2500.0
    assert client.get("/rules").json()["human_approval_threshold"] == 2500.0


def test_put_rules_returns_503_when_admin_api_key_env_unset(tmp_path) -> None:
    """T5.9 (D055): fail-closed when the production env never set ADMIN_API_KEY."""
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}"}
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    client = TestClient(app)

    response = client.put(
        "/rules", json=client.get("/rules").json(), headers=ADMIN_HEADERS
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "admin_key_not_configured"}


def test_decisions_empty_after_seed(tmp_path) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}"}
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    from tests.api.support import USER_HEADERS

    client = TestClient(app, headers=USER_HEADERS)

    assert client.get("/decisions").json() == []


def test_star_cors_aborts_startup(tmp_path) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}", "CORS_ORIGINS": "*"}

    with pytest.raises(InvalidCorsOriginsError):
        create_production_app(mapping, rules_path=RULES_PATH)


def test_import_app_api_does_not_open_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden_create_engine(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("create_engine must not run on import app.api")

    monkeypatch.setattr("sqlalchemy.create_engine", _forbidden_create_engine)
    import importlib
    import sys

    sys.modules.pop("app.api", None)
    import app.api

    importlib.reload(app.api)
    assert app.api.__all__ == ["create_app"]


# --- R2: one canonical approver loader (follow-up to T5.9) -------------------------


def test_load_approver_emails_rules_do_not_extend_allowlist(tmp_path) -> None:
    """R1 regression: `rules.approvers` is mutable via PUT /rules, and the public
    demo proxy injects the admin key for any visitor, so an admin-key holder (or
    the proxy on their behalf) adding an extra approver there must NOT be able
    to extend who may approve/reject after a restart. company.json alone decides
    the allowlist, independent of whatever PUT /rules currently holds."""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "company.json").write_text(
        json.dumps({"approvers": {"default": "static@demo.test"}}), encoding="utf-8"
    )
    rules = load_rules_config(RULES_PATH)
    rules = rules.model_copy(
        update={"approvers": {"default": "static@demo.test", "intruder": "attacker@evil.test"}}
    )

    result = load_approver_emails(tmp_path, rules=rules)

    assert result == frozenset({"static@demo.test"})
    assert "attacker@evil.test" not in result


def test_load_approver_emails_reads_company_json_when_no_rules() -> None:
    data_root = RULES_PATH.resolve().parent.parent

    result = load_approver_emails(data_root, rules=None)

    company = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    assert result == frozenset(company["approvers"].values())


def test_load_approver_emails_missing_company_file_fails_closed_empty(tmp_path) -> None:
    result = load_approver_emails(tmp_path, rules=None)

    assert result == frozenset()


def test_load_approver_emails_malformed_company_file_fails_closed_empty(tmp_path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "company.json").write_text("{not valid json", encoding="utf-8")

    result = load_approver_emails(tmp_path, rules=None)

    assert result == frozenset()


def test_load_approver_emails_ignores_empty_rules_approvers_too() -> None:
    rules = load_rules_config(RULES_PATH)
    rules = rules.model_copy(update={"approvers": {}})
    data_root = RULES_PATH.resolve().parent.parent

    result = load_approver_emails(data_root, rules=rules)

    company = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    assert result == frozenset(company["approvers"].values())


# --- R4/R3: persisted rules failing the new cross-field validator must not crash
# --- boot; fall back (fail-closed) to the seed file instead ------------------------


def _insert_raw_rules_payload(db_path, payload: dict) -> None:
    engine = create_engine(f"sqlite:///{db_path}")
    init_database(engine)
    with Session(engine) as session:
        session.add(RulesDocument(id=1, payload=json.dumps(payload)))
        session.commit()


def test_boot_falls_back_to_seed_when_persisted_rules_fail_new_validator(
    tmp_path,
) -> None:
    db = tmp_path / "boot.sqlite"
    bad_payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    # Violates the T5.9 cross-field validator added after some data may already
    # have been persisted (e.g. in Postgres): threshold above the per-payment cap.
    bad_payload["human_approval_threshold"] = bad_payload["limits"]["per_payment"] + 1
    _insert_raw_rules_payload(db, bad_payload)
    mapping = {"DATABASE_URL": f"sqlite:///{db}", "ADMIN_API_KEY": TEST_ADMIN_KEY}

    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    client = TestClient(app)

    response = client.get("/rules")
    assert response.status_code == 200
    seeded = RulesConfig.model_validate(response.json())
    assert seeded == load_rules_config(RULES_PATH)


def test_boot_still_crashes_loudly_when_seed_file_itself_is_invalid(tmp_path) -> None:
    """Sanity check: the fallback never silently serves invalid rules either."""
    db = tmp_path / "boot.sqlite"
    bad_rules_path = tmp_path / "rules.json"
    bad_payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    bad_payload["human_approval_threshold"] = bad_payload["limits"]["per_payment"] + 1
    bad_rules_path.write_text(json.dumps(bad_payload), encoding="utf-8")
    _insert_raw_rules_payload(db, bad_payload)
    mapping = {"DATABASE_URL": f"sqlite:///{db}"}

    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError, fail loud
        create_production_app(mapping, rules_path=bad_rules_path, cors_origins="")


# --- T7.1 (D059): approver_groups live in company.json, approval_policy in rules ---


def test_load_approver_groups_reads_company_json() -> None:
    data_root = RULES_PATH.resolve().parent.parent

    groups = load_approver_groups(data_root)

    company = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    expected = {
        name: frozenset(members) for name, members in company["approver_groups"].items()
    }
    assert groups == expected


def test_load_approver_groups_missing_company_file_fails_closed_empty(tmp_path) -> None:
    assert load_approver_groups(tmp_path) == {}


def test_load_approver_groups_malformed_company_file_fails_closed_empty(tmp_path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "company.json").write_text("{not valid json", encoding="utf-8")

    assert load_approver_groups(tmp_path) == {}


def test_load_approver_emails_unions_approver_groups_members(tmp_path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "company.json").write_text(
        json.dumps(
            {
                "approvers": {"default": "static@demo.test"},
                "approver_groups": {"finanzas": ["finanzas-only@demo.test"]},
            }
        ),
        encoding="utf-8",
    )

    result = load_approver_emails(tmp_path, rules=None)

    assert result == frozenset({"static@demo.test", "finanzas-only@demo.test"})


def _write_rules_and_company(
    tmp_path, *, rules_payload: dict, company_payload: dict
) -> tuple[object, object]:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rules_path = data_dir / "rules.json"
    company_path = data_dir / "company.json"
    rules_path.write_text(json.dumps(rules_payload), encoding="utf-8")
    company_path.write_text(json.dumps(company_payload), encoding="utf-8")
    return rules_path, company_path


def test_create_production_app_rejects_approval_policy_with_unknown_group(tmp_path) -> None:
    base_rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    base_rules["approval_policy"] = {
        "routes": [
            {
                "id": "default",
                "match": {},
                "require": {"mode": "approvals", "min_approvals": 1, "from_groups": ["ghost"]},
            }
        ]
    }
    base_company = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    base_company["approver_groups"] = {"finanzas": ["finanzas@demo.test"]}
    rules_path, _company_path = _write_rules_and_company(
        tmp_path, rules_payload=base_rules, company_payload=base_company
    )
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}"}

    with pytest.raises(ApprovalPolicyGroupError):
        create_production_app(mapping, rules_path=rules_path, cors_origins="")


def test_create_production_app_rejects_approval_policy_unreachable_min_approvals(
    tmp_path,
) -> None:
    base_rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    base_rules["approval_policy"] = {
        "routes": [
            {
                "id": "default",
                "match": {},
                "require": {
                    "mode": "approvals",
                    "min_approvals": 2,
                    "from_groups": ["finanzas"],
                },
            }
        ]
    }
    base_company = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    base_company["approver_groups"] = {"finanzas": ["only-one@demo.test"]}
    rules_path, _company_path = _write_rules_and_company(
        tmp_path, rules_payload=base_rules, company_payload=base_company
    )
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}"}

    with pytest.raises(ApprovalPolicyGroupError):
        create_production_app(mapping, rules_path=rules_path, cors_origins="")


@pytest.mark.parametrize(
    "raw",
    [
        "  postgresql://u:p@db.example.supabase.co:5432/postgres\n",
        '"postgresql://u:p@db.example.supabase.co:5432/postgres"',
        "'postgres://u:p@db.example.supabase.co:5432/postgres'",
        "postgresql+psycopg2://u:p@db.example.supabase.co:5432/postgres",
        "DATABASE_URL=postgresql://u:p@db.example.supabase.co:5432/postgres",
    ],
)
def test_prepare_database_url_tolerates_common_paste_mistakes(raw: str) -> None:
    url = prepare_database_url(raw)
    assert url.startswith("postgresql+psycopg://u:p@db.example.supabase.co:5432/postgres")


def test_unsupported_database_url_names_only_the_scheme() -> None:
    with pytest.raises(UnsupportedDatabaseUrlError) as exc:
        prepare_database_url("mysql://user:secret@host/db")
    assert "mysql" in str(exc.value)
    assert "secret" not in str(exc.value)
