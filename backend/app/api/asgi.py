"""Production ASGI factory (T4.9). Import only when starting uvicorn; not from `app.api`."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.api.app import create_app
from app.api.production_processor import make_production_processor
from app.persistence import (
    database_url_from_mapping,
    init_database,
    seed_rules,
)
from app.persistence.sql_store import SqlStore

_RENDER_INTERNAL_HOST = re.compile(r"^dpg-[a-z0-9]+-a", re.IGNORECASE)


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
    seed_rules(store, path)
    data_root = path.resolve().parent.parent

    if cors_origins is None:
        origins = parse_cors_origins(env.get("CORS_ORIGINS"))
    else:
        origins = parse_cors_origins(cors_origins)

    limit = rate_limit_from_mapping(env)
    processor = make_production_processor(store, data_root=data_root)
    app = create_app(
        store,
        processor,
        clock=lambda: datetime.now(UTC),
        rate_limit=limit,
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
