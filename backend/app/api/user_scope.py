"""Hackathon demo: trust X-User-Id from the Next proxy (no JWT verification)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException


def require_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> str:
    if x_user_id is None or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="missing_user_id")
    return x_user_id.strip()
