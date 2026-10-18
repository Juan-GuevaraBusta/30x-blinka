"""Seed demo rules/agreements via the REAL API (T10).

Idempotent CLI: default behavior is a dry run that only prints the plan
(every HTTP call it would make) with NO network I/O at all; `--apply`
actually performs the calls. `--with-rules` opts into the `PUT /rules` step
(a demo company config with a 2-of-N high-amount `approval_policy` route);
it is skipped entirely when absent. The agreement step always runs,
independent of `--with-rules`, for the 3 demo vendors (see
`scripts._demo_fixtures`).

`ADMIN_API_KEY` is read from the environment and required only in `--apply`
mode; it is sent as the `X-Admin-Key` header on every write request and is
never printed anywhere (plan, logs, or errors).

T9.8 (D067): every write is scoped to the demo company «Acme Demo Inc.».
The script first attaches its writer to that company through
`PUT /admin/members` (X-Admin-Key only): the real Supabase user given with
`--member-user-id/--member-email` (admin, approver groups finanzas+cfo), or a
service user `seed-demo-script` when none is given.

Usage::

    python backend/scripts/seed_demo.py                       # dry run
    python backend/scripts/seed_demo.py --with-rules           # dry run, incl. rules
    ADMIN_API_KEY=... python backend/scripts/seed_demo.py --apply --with-rules \
        --member-user-id <supabase-uuid> --member-email <email> --role admin
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.models.agreement import VendorAgreement, parse_vendor_agreement
from app.models.rules_config import RulesConfig
from pydantic import ValidationError

from scripts._demo_fixtures import (
    build_demo_agreements,
    build_demo_rules_config,
    pick_approver_email,
)

DEFAULT_BASE_URL = "http://localhost:8000"
DEMO_COMPANY_ID = "demo-acme"
SEED_SERVICE_USER_ID = "seed-demo-script"
DEMO_APPROVER_GROUPS = ["finanzas", "cfo"]


@dataclass(frozen=True)
class HttpResult:
    """A transport's response: status code plus the parsed JSON body."""

    status_code: int
    body: Any


# `Transport` is the injectable HTTP layer: (method, url, headers, json_body) ->
# HttpResult. Tests substitute a fake transport that records calls and returns
# canned results, with no real sockets anywhere.
Transport = Callable[[str, str, Mapping[str, str], Any | None], HttpResult]


@dataclass(frozen=True)
class PlannedCall:
    method: str
    path: str
    summary: str


def urllib_transport(
    method: str, url: str, headers: Mapping[str, str], body: Any | None
) -> HttpResult:
    """Default transport: stdlib `urllib.request`. Only used with `--apply`."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = dict(headers)
    if data is not None:
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read()
            parsed = json.loads(raw) if raw else {}
            return HttpResult(status_code=response.status, body=parsed)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"detail": raw.decode("utf-8", errors="replace")}
        return HttpResult(status_code=exc.code, body=parsed)


def _rules_matches(current_json: Any, demo_rules: RulesConfig) -> bool:
    if not isinstance(current_json, dict):
        return False
    try:
        current = RulesConfig.model_validate(current_json)
    except ValidationError:
        return False
    return current.model_dump(mode="json") == demo_rules.model_dump(mode="json")


def _agreement_matches(current_terms_json: Any, demo_terms: VendorAgreement) -> bool:
    if not isinstance(current_terms_json, dict):
        return False
    try:
        current = parse_vendor_agreement(current_terms_json)
    except ValidationError:
        return False
    return current.model_dump(mode="json") == demo_terms.model_dump(mode="json")


def build_plan(
    *, with_rules: bool, demo_agreements: Mapping[str, VendorAgreement]
) -> list[PlannedCall]:
    plan: list[PlannedCall] = [
        PlannedCall("PUT", "/admin/members", "attach the writer to «Acme Demo Inc.»")
    ]
    if with_rules:
        plan.append(PlannedCall("GET", "/rules", "check the current rules document"))
        plan.append(
            PlannedCall(
                "PUT", "/rules", "demo RulesConfig (skipped if already up to date)"
            )
        )
    for vendor_key, terms in demo_agreements.items():
        path = f"/agreements/{vendor_key}"
        plan.append(PlannedCall("GET", path, f"check current agreement for {terms.vendor_name}"))
        plan.append(
            PlannedCall(
                "PUT",
                path,
                f"confirm {terms.kind} agreement for {terms.vendor_name} "
                "(skipped if an active version already matches)",
            )
        )
    return plan


def _print_plan(plan: list[PlannedCall]) -> None:
    print("Dry run -- no network calls made. Planned calls:")
    for call in plan:
        print(f"  {call.method} {call.path} -- {call.summary}")


def _apply_member_step(
    transport: Transport,
    base_url: str,
    admin_key: str,
    *,
    user_id: str,
    email: str,
    role: str,
) -> bool:
    body = {
        "company_id": DEMO_COMPANY_ID,
        "user_id": user_id,
        "email": email,
        "role": role,
        "approver_groups": DEMO_APPROVER_GROUPS,
    }
    result = transport("PUT", f"{base_url}/admin/members", {"X-Admin-Key": admin_key}, body)
    if result.status_code == 200:
        print(f"attached: {email} to «Acme Demo Inc.» as {role} (finanzas, cfo)")
        return True
    print(
        f"error: PUT /admin/members failed with status {result.status_code}: {result.body}",
        file=sys.stderr,
    )
    return False


def _apply_rules_step(
    transport: Transport, base_url: str, write_headers: Mapping[str, str], demo_rules: RulesConfig
) -> None:
    read_headers = {"X-User-Id": write_headers["X-User-Id"]}
    get_result = transport("GET", f"{base_url}/rules", read_headers, None)
    if get_result.status_code == 200 and _rules_matches(get_result.body, demo_rules):
        print("skip: rules already up to date")
        return
    put_body = json.loads(demo_rules.model_dump_json())
    put_result = transport("PUT", f"{base_url}/rules", write_headers, put_body)
    if put_result.status_code == 200:
        print("applied: demo rules (PUT /rules)")
    else:
        print(
            f"error: PUT /rules failed with status {put_result.status_code}: {put_result.body}",
            file=sys.stderr,
        )


def _apply_agreement_step(
    transport: Transport,
    base_url: str,
    write_headers: Mapping[str, str],
    vendor_key: str,
    terms: VendorAgreement,
    confirmed_by: str,
) -> None:
    path = f"/agreements/{vendor_key}"
    read_headers = {"X-User-Id": write_headers["X-User-Id"]}
    get_result = transport("GET", f"{base_url}{path}", read_headers, None)
    if get_result.status_code == 404:
        expected_version = 0
    elif get_result.status_code == 200 and isinstance(get_result.body, dict):
        body = get_result.body
        active = body.get("active")
        if isinstance(active, dict) and _agreement_matches(active.get("terms"), terms):
            print(f"skip: {terms.vendor_name} already has matching active agreement")
            return
        if isinstance(active, dict):
            expected_version = int(active.get("version", 0))
        else:
            versions = body.get("versions") or []
            expected_version = max((int(v.get("version", 0)) for v in versions), default=0)
    else:
        print(
            f"error: unexpected GET {path} status {get_result.status_code}: {get_result.body}",
            file=sys.stderr,
        )
        return

    put_body = {
        "terms": json.loads(terms.model_dump_json()),
        "confirmed_by": confirmed_by,
        "expected_version": expected_version,
    }
    put_result = transport("PUT", f"{base_url}{path}", write_headers, put_body)
    if put_result.status_code == 200:
        version = put_result.body.get("version") if isinstance(put_result.body, dict) else "?"
        print(f"confirmed: {terms.vendor_name} agreement v{version}")
    else:
        print(
            f"error: PUT {path} failed with status {put_result.status_code}: {put_result.body}",
            file=sys.stderr,
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Seed demo rules/agreements through the real API. Default is a dry run "
            "(prints the plan, no network calls); pass --apply to execute it."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--with-rules",
        action="store_true",
        help="Also seed the demo RulesConfig via PUT /rules (opt-in, idempotent).",
    )
    parser.add_argument(
        "--member-user-id",
        help="Supabase user id to attach to «Acme Demo Inc.» (approver groups finanzas+cfo).",
    )
    parser.add_argument("--member-email", help="Email of --member-user-id.")
    parser.add_argument(
        "--role", choices=["admin", "member"], default="admin", help="Role (default admin)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the HTTP calls. Without this flag, only the plan is printed.",
    )
    return parser


def run(args: argparse.Namespace, transport: Transport, env: Mapping[str, str]) -> int:
    demo_agreements = build_demo_agreements()

    if not args.apply:
        _print_plan(build_plan(with_rules=args.with_rules, demo_agreements=demo_agreements))
        return 0

    admin_key = env.get("ADMIN_API_KEY")
    if not admin_key:
        print(
            "error: ADMIN_API_KEY environment variable is required with --apply",
            file=sys.stderr,
        )
        return 1

    if bool(args.member_user_id) != bool(args.member_email):
        print("error: --member-user-id and --member-email go together", file=sys.stderr)
        return 1

    confirmed_by = pick_approver_email()
    writer_id = args.member_user_id or SEED_SERVICE_USER_ID
    writer_email = args.member_email or confirmed_by
    writer_role = args.role if args.member_user_id else "admin"
    if not _apply_member_step(
        transport,
        args.base_url,
        admin_key,
        user_id=writer_id,
        email=writer_email,
        role=writer_role,
    ):
        return 1
    if writer_role != "admin":
        # Rules/agreements need an admin writer: fall back to the service user.
        writer_id = SEED_SERVICE_USER_ID
        if not _apply_member_step(
            transport, args.base_url, admin_key,
            user_id=writer_id, email=confirmed_by, role="admin",
        ):
            return 1
    write_headers = {"X-Admin-Key": admin_key, "X-User-Id": writer_id}

    if args.with_rules:
        demo_rules = build_demo_rules_config()
        _apply_rules_step(transport, args.base_url, write_headers, demo_rules)

    for vendor_key, terms in demo_agreements.items():
        _apply_agreement_step(
            transport, args.base_url, write_headers, vendor_key, terms, confirmed_by
        )

    return 0


def main(
    argv: list[str] | None = None,
    *,
    transport: Transport | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    args = build_arg_parser().parse_args(argv)
    chosen_transport = transport if transport is not None else urllib_transport
    chosen_env: Mapping[str, str] = env if env is not None else os.environ
    return run(args, chosen_transport, chosen_env)


if __name__ == "__main__":
    raise SystemExit(main())
