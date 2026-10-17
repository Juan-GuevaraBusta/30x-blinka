"""Reproducible rules seed (T4.2). Does not load invoices or decisions."""

from __future__ import annotations

from pathlib import Path

from app.models.rules_config import RulesConfig, load_rules_config
from app.persistence.errors import RulesMissing
from app.persistence.sql_store import SqlStore


def seed_rules(store: SqlStore, rules_path: Path) -> RulesConfig:
    try:
        return store.rules
    except RulesMissing:
        loaded = load_rules_config(rules_path)
        return store.put_rules(loaded)
