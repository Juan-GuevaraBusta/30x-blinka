"""T9.8 (D067): companies, membership and `GET /me`.

Identity is the hackathon one (`X-User-Id` / `X-User-Email` forwarded by the
Next proxy, not verified server-side -- see `docs/T9_8_SPEC.md` §5).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.tenancy import (
    CREATOR_GROUPS,
    AlreadyMemberError,
    Company,
    CompanyNameTakenError,
    CompanyNotFoundError,
    Member,
)
from app.api.user_scope import require_user_id
from app.rules.fx import supported_currencies


class CompanyBody(BaseModel):
    id: str
    name: str
    base_currency: str
    is_demo: bool
    configured: bool


class MemberBody(BaseModel):
    user_id: str
    email: str
    role: str
    approver_groups: list[str]
    is_approver: bool


class MeBody(BaseModel):
    user_id: str
    email: str | None
    company: CompanyBody | None
    member: MemberBody | None


class CreateCompanyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    base_currency: str = Field(min_length=3, max_length=3)
    is_demo: bool = False


class UpdateMemberBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["admin", "member"] | None = None
    approver_groups: list[str] | None = None


class AdminMemberBody(BaseModel):
    """`PUT /admin/members` (X-Admin-Key only): the seed script attaches a
    real Supabase user to a company with this."""

    model_config = ConfigDict(extra="forbid")

    company_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    email: str = Field(min_length=3)
    role: Literal["admin", "member"] = "member"
    approver_groups: list[str] = Field(default_factory=list)


def _clean_groups(groups: list[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    for group in groups:
        name = group.strip()
        if not name:
            raise HTTPException(status_code=422, detail="invalid_approver_group")
        if name not in cleaned:
            cleaned.append(name)
    return tuple(cleaned)


def member_body(member: Member) -> MemberBody:
    return MemberBody(
        user_id=member.user_id,
        email=member.email,
        role=member.role,
        approver_groups=list(member.approver_groups),
        is_approver=member.is_approver,
    )


def build_company_router(
    store: Any,
    *,
    clock: Callable[[], datetime],
    check_admin_key: Callable[..., None],
) -> APIRouter:
    router = APIRouter()

    def _company_body(company: Company) -> CompanyBody:
        return CompanyBody(
            id=company.id,
            name=company.name,
            base_currency=company.base_currency,
            is_demo=company.is_demo,
            configured=store.rules_for(company.id) is not None,
        )

    def _require_email(raw: str | None) -> str:
        email = (raw or "").strip().lower()
        if "@" not in email:
            raise HTTPException(status_code=422, detail="missing_user_email")
        return email

    def _now() -> str:
        return clock().isoformat()

    @router.get("/me")
    def me(
        user_id: Annotated[str, Depends(require_user_id)],
        x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
    ) -> MeBody:
        member = store.membership(user_id)
        company = store.get_company(member.company_id) if member is not None else None
        return MeBody(
            user_id=user_id,
            email=member.email if member is not None else (x_user_email or None),
            company=_company_body(company) if company is not None else None,
            member=member_body(member) if member is not None else None,
        )

    @router.get("/companies")
    def list_companies(
        _user_id: Annotated[str, Depends(require_user_id)],
    ) -> list[CompanyBody]:
        return [_company_body(c) for c in store.list_companies()]

    @router.post("/companies", status_code=201)
    def create_company(
        body: CreateCompanyBody,
        user_id: Annotated[str, Depends(require_user_id)],
        x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
    ) -> MeBody:
        email = _require_email(x_user_email)
        if store.membership(user_id) is not None:
            raise HTTPException(status_code=409, detail="already_in_company")
        currency = body.base_currency.strip().upper()
        if currency not in supported_currencies():
            raise HTTPException(status_code=422, detail="unsupported_currency")
        name = " ".join(body.name.split())
        if not name:
            raise HTTPException(status_code=422, detail="invalid_company_name")
        try:
            company = store.create_company(
                name=name,
                base_currency=currency,
                is_demo=body.is_demo,
                created_by=user_id,
                at=_now(),
            )
        except CompanyNameTakenError:
            raise HTTPException(status_code=409, detail="company_name_taken") from None
        member = store.add_member(
            company_id=company.id,
            user_id=user_id,
            email=email,
            role="admin",
            approver_groups=CREATOR_GROUPS,
            at=_now(),
        )
        return MeBody(
            user_id=user_id,
            email=email,
            company=_company_body(company),
            member=member_body(member),
        )

    @router.post("/companies/{company_id}/join")
    def join_company(
        company_id: str,
        user_id: Annotated[str, Depends(require_user_id)],
        x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
    ) -> MeBody:
        email = _require_email(x_user_email)
        company = store.get_company(company_id)
        if company is None:
            raise HTTPException(status_code=404, detail="not_found")
        try:
            member = store.add_member(
                company_id=company_id,
                user_id=user_id,
                email=email,
                role="member",
                approver_groups=(),
                at=_now(),
            )
        except AlreadyMemberError:
            raise HTTPException(status_code=409, detail="already_in_company") from None
        return MeBody(
            user_id=user_id,
            email=email,
            company=_company_body(company),
            member=member_body(member),
        )

    def _require_member_of(user_id: str, company_id: str) -> Member:
        member = store.membership(user_id)
        if member is None or member.company_id != company_id:
            raise HTTPException(status_code=403, detail="not_a_member")
        return member

    @router.get("/companies/{company_id}/members")
    def list_members(
        company_id: str,
        user_id: Annotated[str, Depends(require_user_id)],
    ) -> list[MemberBody]:
        _require_member_of(user_id, company_id)
        return [member_body(m) for m in store.list_members(company_id)]

    @router.patch("/companies/{company_id}/members/{member_user_id}")
    def update_member(
        company_id: str,
        member_user_id: str,
        body: UpdateMemberBody,
        user_id: Annotated[str, Depends(require_user_id)],
    ) -> MemberBody:
        caller = _require_member_of(user_id, company_id)
        if caller.role != "admin":
            raise HTTPException(status_code=403, detail="admin_required")
        groups = _clean_groups(body.approver_groups) if body.approver_groups is not None else None
        updated = store.update_member(
            company_id, member_user_id, role=body.role, approver_groups=groups
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="not_found")
        return member_body(updated)

    @router.put("/admin/members")
    def admin_put_member(
        body: AdminMemberBody,
        _admin: None = Depends(check_admin_key),
    ) -> MemberBody:
        try:
            member = store.add_member(
                company_id=body.company_id,
                user_id=body.user_id.strip(),
                email=body.email.strip().lower(),
                role=body.role,
                approver_groups=_clean_groups(body.approver_groups),
                at=_now(),
                replace=True,
            )
        except CompanyNotFoundError:
            raise HTTPException(status_code=404, detail="not_found") from None
        return member_body(member)

    return router
