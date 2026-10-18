"""Production ASGI factory (T4.9). Import only when starting uvicorn; not from `app.api`."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.api.app import create_app
from app.api.production_processor import make_production_processor
from app.models.rules_config import RulesConfig, load_rules_config
from app.persistence import (
    database_url_from_mapping,
    init_database,
    seed_rules,
)
from app.persistence.sql_store import SqlStore
from app.rules.approval_policy import validate_policy_groups

_RENDER_INTERNAL_HOST = re.compile(r"^dpg-[a-z0-9]+-a", re.IGNORECASE)

_logger = logging.getLogger(__name__)


class UnsupportedDatabaseUrlError(Exception):
    def __init__(self) -> None:
        super().__init__("unsupported_database_url")


class InvalidCorsOriginsError(Exception):
    def __init__(self) -> None:
        super().__init__("invalid_cors_origins")


class RulesFileMissingError(Exception):
    def __init__(self) -> None:
        super().__init__("rules_file_missing")


class InvalidRateLimitError(Exception):
    def __init__(self) -> None:
        super().__init__("invalid_rate_limit")


def prepare_database_url(url: str) -> str:
    """Normalize SQLAlchemy URL for sqlite and Postgres (T4.9 §5). No network I/O."""
    if url.startswith("sqlite:"):
        return url
    if url.startswith("postgres://"):
        normalized = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        normalized = "postgresql+psycopg://" + url[len("postgresql://") :]
    elif url.startswith("postgresql+psycopg://"):
        normalized = url
    else:
        raise UnsupportedDatabaseUrlError()

    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    query_items = list(parse_qsl(parsed.query, keep_blank_values=True))
    keys = {k.lower() for k, _ in query_items}
    if "sslmode" not in keys and not _RENDER_INTERNAL_HOST.match(host):
        query_items.append(("sslmode", "require"))
    new_query = urlencode(query_items)
    return urlunparse(parsed._replace(query=new_query))


def parse_cors_origins(raw: str | Sequence[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        if not raw.strip():
            return []
        parts = [piece.strip() for piece in raw.split(",")]
    else:
        parts = [str(piece).strip() for piece in raw]
    if not parts:
        return []
    if any(not piece or piece == "*" for piece in parts):
        raise InvalidCorsOriginsError()
    return parts


def rate_limit_from_mapping(mapping: Mapping[str, str]) -> int:
    raw = mapping.get("API_RATE_LIMIT_PER_MINUTE")
    if raw is None or not str(raw).strip():
        return 60
    try:
        value = int(str(raw).strip(), 10)
    except ValueError:
        raise InvalidRateLimitError() from None
    if value < 1:
        raise InvalidRateLimitError()
    return value


def load_approver_emails(
    data_root: Path, *, rules: RulesConfig | None = None
) -> frozenset[str]:
    """Canonical allowlist for approve/reject `author` (T5.9, D055; R1 follow-up).

    Source of truth is `data/company.json`'s `approvers` mapping, read once at
    boot, independent of later PUT /rules edits -- this is now the single
    reader (`asgi.py` and tests no longer duplicate it), but it must stay
    independent of `rules.approvers`. `RulesConfig.approvers` is mutable at
    runtime via PUT /rules, and the public demo proxy injects the admin key
    for any visitor, so if that mapping were ever allowed to extend this
    allowlist, any visitor could add themselves as an approver and, after a
    restart, pass `_require_known_approver`. The `rules` parameter is kept for
    call-site compatibility but intentionally ignored here -- it must never
    widen or otherwise change who may approve/reject.
    Any failure reading/parsing `company.json` -- missing file or malformed JSON
    -- fails closed to an empty set rather than raising, so a broken company
    directory can never widen who may approve/reject.
    """
    del rules
    company_path = data_root / "data" / "company.json"
    try:
        raw = company_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return frozenset()
    approvers = payload.get("approvers") if isinstance(payload, dict) else None
    emails: set[str] = set()
    if isinstance(approvers, dict):
        with contextlib.suppress(TypeError):
            emails.update(approvers.values())
    groups = payload.get("approver_groups") if isinstance(payload, dict) else None
    if isinstance(groups, dict):
        for members in groups.values():
            if isinstance(members, list):
                emails.update(member for member in members if isinstance(member, str))
    return frozenset(emails)


def load_approver_groups(data_root: Path) -> dict[str, frozenset[str]]:
    """Approver group membership for R14 route eligibility (T7.1, D059).

    Source of truth is `data/company.json`'s `approver_groups` mapping
    (`{"finanzas": ["finanzas@demo.test"], ...}`), never `rules.json` -- same
    reasoning as `load_approver_emails` above. Any failure reading/parsing
    `company.json` fails closed to an empty mapping.
    """
    company_path = data_root / "data" / "company.json"
    try:
        raw = company_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    groups = payload.get("approver_groups") if isinstance(payload, dict) else None
    if not isinstance(groups, dict):
        return {}
    result: dict[str, frozenset[str]] = {}
    for name, members in groups.items():
        if not isinstance(name, str) or not isinstance(members, list):
            continue
        result[name] = frozenset(member for member in members if isinstance(member, str))
    return result


def _build_engine(url: str) -> Engine:
    prepared = prepare_database_url(url)
    return create_engine(
        prepared,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
    )


def create_production_app(
    mapping: Mapping[str, str] | None = None,
    *,
    rules_path: Path | None = None,
    cors_origins: str | Sequence[str] | None = None,
) -> FastAPI:
    """Wire SqlStore, seed rules, and the T4.1 HTTP app. Uvicorn calls this with no args."""
    env: Mapping[str, str] = os.environ if mapping is None else mapping

    raw_url = database_url_from_mapping(env)
    engine = _build_engine(raw_url)
    init_database(engine)
    store = SqlStore(engine)

    path = rules_path if rules_path is not None else Path("data/rules.json")
    if not path.is_file():
        raise RulesFileMissingError()
    try:
        in_force_rules = seed_rules(store, path)
    except ValidationError:
        # R4/R3 follow-up (T5.9): `threshold_within_per_payment_limit` is a
        # cross-field validator added after this service may already have
        # persisted rules (e.g. in Postgres) that predate it. Without this
        # fallback, every future boot against that database would crash here
        # forever -- a schema tightening should never be able to take down the
        # whole service. Fail closed instead: log, then reseed from the
        # known-valid `data/rules.json` (never run with invalid rules). PUT
        # /rules still rejects an invalid body with 422, after the admin-key
        # check (see `app.py`'s `_check_admin_key` dependency).
        _logger.warning(
            "persisted rules failed validation at boot; reseeding from %s", path
        )
        in_force_rules = load_rules_config(path)
        store.put_rules(in_force_rules)
    data_root = path.resolve().parent.parent

    if cors_origins is None:
        origins = parse_cors_origins(env.get("CORS_ORIGINS"))
    else:
        origins = parse_cors_origins(cors_origins)

    # T5.9 (D055): read outside app/config.py, like DATABASE_URL and CORS_ORIGINS above.
    raw_admin_key = env.get("ADMIN_API_KEY")
    admin_api_key = raw_admin_key if raw_admin_key else None
    approver_emails = load_approver_emails(data_root, rules=in_force_rules)
    approver_groups = load_approver_groups(data_root)
    # T7.1 (D059): fail boot loudly if approval_policy references a group that
    # does not exist in company.json, or demands more approvals than the
    # union of its groups can ever supply -- never silently unreachable.
    validate_policy_groups(in_force_rules.approval_policy, approver_groups)

    limit = rate_limit_from_mapping(env)
    processor = make_production_processor(store, data_root=data_root)
    app = create_app(
        store,
        processor,
        clock=lambda: datetime.now(UTC),
        rate_limit=limit,
        admin_api_key=admin_api_key,
        approver_emails=approver_emails,
        approver_groups=approver_groups,
    )
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "PUT", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
            allow_credentials=False,
        )
    return app
