"""seed_rules idempotency and database_url_from_mapping."""

from __future__ import annotations

import pytest
from app.models.rules_config import RulesConfig
from app.persistence import (
    MissingDatabaseUrlError,
    SqlStore,
    database_url_from_mapping,
    init_database,
    seed_rules,
)
from app.persistence.tables import RulesDocument
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from tests.api.support import RULES_PATH, rules_payload


def _store(tmp_path) -> SqlStore:
    url = f"sqlite:///{tmp_path}/blinka.sqlite"
    engine = create_engine(url)
    init_database(engine)
    return SqlStore(engine)


def test_seed_inserts_rules_from_file(tmp_path) -> None:
    store = _store(tmp_path)
    seeded = seed_rules(store, RULES_PATH)

    assert seeded.human_approval_threshold == 3000.0
    assert store.rules.model_dump(mode="json") == seeded.model_dump(mode="json")


def test_seed_second_call_is_idempotent(tmp_path) -> None:
    store = _store(tmp_path)
    first = seed_rules(store, RULES_PATH)
    second = seed_rules(store, RULES_PATH)

    assert second.model_dump(mode="json") == first.model_dump(mode="json")
    with Session(store._engine) as session:
        count = session.scalar(select(func.count()).select_from(RulesDocument))
        assert count == 1


def test_seed_does_not_overwrite_put_rules(tmp_path) -> None:
    store = _store(tmp_path)
    seed_rules(store, RULES_PATH)
    custom = RulesConfig.model_validate({**rules_payload(), "human_approval_threshold": 2500.0})
    store.put_rules(custom)

    again = seed_rules(store, RULES_PATH)

    assert again.human_approval_threshold == 2500.0
    assert store.rules.human_approval_threshold == 2500.0


def test_seed_leaves_decisions_empty(tmp_path) -> None:
    store = _store(tmp_path)
    seed_rules(store, RULES_PATH)

    assert store.decisions == {}


def test_database_url_missing_raises() -> None:
    with pytest.raises(MissingDatabaseUrlError) as exc:
        database_url_from_mapping({})

    assert str(exc.value) == "missing_database_url"


def test_postgres_url_returned_without_connecting() -> None:
    url = database_url_from_mapping({"DATABASE_URL": "postgresql://demo.example/blinka"})

    assert url == "postgresql://demo.example/blinka"
