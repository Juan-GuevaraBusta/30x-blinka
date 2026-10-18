"""SQL-backed store with the same surface as MemoryStore (T4.2)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.store import (
    AgreementNotFoundError,
    AgreementVersionConflictError,
    AlreadyAllowedError,
    DuplicateDecisionError,
    R01NotFailedError,
    VendorOnboardingDisabledError,
)
from app.api.tenancy import (
    DEMO_COMPANY_ID,
    AlreadyMemberError,
    Company,
    CompanyNameTakenError,
    CompanyNotFoundError,
    Member,
    normalize_company_name,
)
from app.models.agreement import (
    VendorAgreement,
    VendorAgreementVersion,
    parse_vendor_agreement,
    vendor_agreement_json,
)
from app.models.domain import DecisionRecord, HumanEvent
from app.models.rules_config import RulesConfig, VendorAddition
from app.persistence.errors import RulesMissing
from app.persistence.tables import (
    ChainEntryRow,
    CompanyMemberRow,
    CompanyRow,
    DecisionRecordRow,
    RulesDocument,
    VendorAgreementVersionRow,
)
from app.records.chain import (
    GENESIS_PREV_HASH,
    AgreementChangePayload,
    AllowlistChangePayload,
    ChainVerification,
    agreement_change_entry_payload,
    allowlist_change_entry_payload,
    canonical_json,
    compute_decision_entry_hash,
    compute_entry_hash,
    decision_entry_payload,
    human_event_entry_payload,
)
from app.records.chain import verify_chain as _verify_chain_entries
from app.rules.agreements import ActiveAgreement, vendor_key_conflicts_with_base
from app.rules.normalize import normalize_beneficiary


class SqlStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # --- T9.8 (D067): companies and members -----------------------------------

    @staticmethod
    def _company(row: CompanyRow) -> Company:
        return Company(
            id=row.id,
            name=row.name,
            base_currency=row.base_currency,
            is_demo=bool(row.is_demo),
            created_by=row.created_by,
            created_at=row.created_at,
        )

    @staticmethod
    def _member(row: CompanyMemberRow) -> Member:
        groups = json.loads(row.approver_groups or "[]")
        return Member(
            company_id=row.company_id,
            user_id=row.user_id,
            email=row.email,
            role=row.role,
            approver_groups=tuple(str(g) for g in groups),
            created_at=row.created_at,
        )

    @property
    def template_rules(self) -> RulesConfig:
        return self.rules

    def list_companies(self) -> list[Company]:
        with Session(self._engine) as session:
            rows = session.scalars(select(CompanyRow)).all()
            return sorted((self._company(r) for r in rows), key=lambda c: c.name.casefold())

    def get_company(self, company_id: str) -> Company | None:
        with Session(self._engine) as session:
            row = session.get(CompanyRow, company_id)
            return self._company(row) if row is not None else None

    def create_company(
        self, *, name: str, base_currency: str, is_demo: bool, created_by: str, at: str
    ) -> Company:
        row = CompanyRow(
            id=str(uuid.uuid4()),
            name=name.strip(),
            name_key=normalize_company_name(name),
            base_currency=base_currency,
            is_demo=is_demo,
            created_by=created_by,
            created_at=at,
        )
        with Session(self._engine) as session:
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise CompanyNameTakenError(name) from None
            return self._company(row)

    def membership(self, user_id: str) -> Member | None:
        with Session(self._engine) as session:
            row = session.scalar(
                select(CompanyMemberRow).where(CompanyMemberRow.user_id == user_id)
            )
            return self._member(row) if row is not None else None

    def list_members(self, company_id: str) -> list[Member]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(CompanyMemberRow)
                .where(CompanyMemberRow.company_id == company_id)
                .order_by(CompanyMemberRow.id)
            ).all()
            return [self._member(r) for r in rows]

    def add_member(
        self,
        *,
        company_id: str,
        user_id: str,
        email: str,
        role: str,
        approver_groups: tuple[str, ...],
        at: str,
        replace: bool = False,
    ) -> Member:
        with Session(self._engine) as session:
            if session.get(CompanyRow, company_id) is None:
                raise CompanyNotFoundError(company_id)
            existing = session.scalar(
                select(CompanyMemberRow).where(CompanyMemberRow.user_id == user_id)
            )
            if existing is not None and not replace:
                raise AlreadyMemberError(user_id)
            if existing is not None:
                session.delete(existing)
                session.flush()
            row = CompanyMemberRow(
                company_id=company_id,
                user_id=user_id,
                email=email,
                role=role,
                approver_groups=json.dumps(list(approver_groups)),
                created_at=at,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise AlreadyMemberError(user_id) from None
            return self._member(row)

    def update_member(
        self,
        company_id: str,
        user_id: str,
        *,
        role: str | None = None,
        approver_groups: tuple[str, ...] | None = None,
    ) -> Member | None:
        with Session(self._engine) as session:
            row = session.scalar(
                select(CompanyMemberRow).where(
                    CompanyMemberRow.user_id == user_id,
                    CompanyMemberRow.company_id == company_id,
                )
            )
            if row is None:
                return None
            if role is not None:
                row.role = role
            if approver_groups is not None:
                row.approver_groups = json.dumps(list(approver_groups))
            session.commit()
            return self._member(row)

    # --- rules (one document per company) ---------------------------------------

    @staticmethod
    def _rules_row(session: Session, company_id: str) -> RulesDocument | None:
        return session.scalar(
            select(RulesDocument)
            .where(RulesDocument.company_id == company_id)
            .order_by(RulesDocument.id)
            .limit(1)
        )

    @property
    def rules(self) -> RulesConfig:
        found = self.rules_for(DEMO_COMPANY_ID)
        if found is None:
            raise RulesMissing()
        return found

    def rules_for(self, company_id: str) -> RulesConfig | None:
        """`None` means the company is unconfigured (T9.8 fail-closed)."""
        with Session(self._engine) as session:
            row = self._rules_row(session, company_id)
            if row is None:
                return None
            return RulesConfig.model_validate_json(row.payload)

    def put_rules(self, rules: RulesConfig, *, company_id: str = DEMO_COMPANY_ID) -> RulesConfig:
        payload = rules.model_dump_json()
        with Session(self._engine) as session:
            row = self._rules_row(session, company_id)
            if row is None:
                # Explicit id: a legacy row may have been inserted with id=1
                # without advancing a Postgres sequence.
                next_id = session.scalar(select(func.coalesce(func.max(RulesDocument.id), 0)))
                session.add(
                    RulesDocument(id=int(next_id or 0) + 1, payload=payload, company_id=company_id)
                )
            else:
                row.payload = payload
            session.commit()
        return rules

    def has_invoice(self, invoice_id: str, owner_id: str) -> bool:
        with Session(self._engine) as session:
            found = session.scalar(
                select(DecisionRecordRow.id).where(
                    DecisionRecordRow.invoice_id == invoice_id,
                    DecisionRecordRow.owner_id == owner_id,
                )
            )
            return found is not None

    def has_company_invoice(self, invoice_id: str, company_id: str) -> bool:
        with Session(self._engine) as session:
            found = session.scalar(
                select(DecisionRecordRow.id).where(
                    DecisionRecordRow.invoice_id == invoice_id,
                    DecisionRecordRow.company_id == company_id,
                )
            )
            return found is not None

    def decisions_for(self, company_id: str) -> dict[str, DecisionRecord]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(DecisionRecordRow)
                .where(DecisionRecordRow.company_id == company_id)
                .order_by(DecisionRecordRow.position)
            ).all()
            return {row.id: DecisionRecord.model_validate_json(row.payload) for row in rows}

    def list_decisions_for_company(
        self, company_id: str, decision: str | None = None
    ) -> list[DecisionRecord]:
        records = list(self.decisions_for(company_id).values())
        if decision is None:
            return records
        return [item for item in records if item.decision == decision]

    def get_for_company(self, decision_id: str, company_id: str) -> DecisionRecord | None:
        with Session(self._engine) as session:
            row = session.get(DecisionRecordRow, decision_id)
            if row is None or row.company_id != company_id:
                return None
            return DecisionRecord.model_validate_json(row.payload)

    def list_decisions_for_owner(
        self, owner_id: str, decision: str | None = None
    ) -> list[DecisionRecord]:
        with Session(self._engine) as session:
            stmt = select(DecisionRecordRow).where(DecisionRecordRow.owner_id == owner_id)
            if decision is not None:
                stmt = stmt.where(DecisionRecordRow.decision == decision)
            stmt = stmt.order_by(DecisionRecordRow.position)
            rows = session.scalars(stmt).all()
            return [DecisionRecord.model_validate_json(row.payload) for row in rows]

    def get_for_owner(self, decision_id: str, owner_id: str) -> DecisionRecord | None:
        with Session(self._engine) as session:
            row = session.get(DecisionRecordRow, decision_id)
            if row is None or row.owner_id != owner_id:
                return None
            return DecisionRecord.model_validate_json(row.payload)

    def add_decision(
        self,
        record: DecisionRecord,
        owner_id: str = "test-user-id",
        *,
        company_id: str = DEMO_COMPANY_ID,
    ) -> DecisionRecord:
        payload = record.model_dump_json()
        with Session(self._engine) as session:
            next_position = session.scalar(
                select(func.coalesce(func.max(DecisionRecordRow.position), 0))
            )
            position = int(next_position or 0) + 1
            # T5.10 (D055): resolve the chain tip with a plain SELECT before
            # `session.add`ing anything below -- SQLAlchemy autoflushes a
            # pending INSERT on the next SELECT, which would otherwise raise
            # the duplicate-invoice IntegrityError here instead of inside the
            # `try`/`except` around `session.commit()` further down.
            prev_hash = self._chain_tip(session)
            row = DecisionRecordRow(
                id=record.id,
                owner_id=owner_id,
                invoice_id=record.invoice_id,
                decision=record.decision,
                position=position,
                payload=payload,
                company_id=company_id,
            )
            session.add(row)
            # Append-only chain entry for this decision, inside the same
            # session/transaction `position` is computed in, so ordering
            # stays deterministic under the T5.8 invoice lock. This entry's
            # hash excludes `human_events` and is NEVER recomputed or
            # rewritten later -- see app.records.chain.
            record_hash = compute_decision_entry_hash(record, prev_hash)
            session.add(
                ChainEntryRow(
                    kind="decision",
                    ref_id=record.id,
                    payload=None,
                    prev_hash=prev_hash,
                    record_hash=record_hash,
                    company_id=company_id,
                )
            )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise DuplicateDecisionError(record.invoice_id) from None
        return record

    def get(self, decision_id: str) -> DecisionRecord | None:
        with Session(self._engine) as session:
            row = session.get(DecisionRecordRow, decision_id)
            if row is None:
                return None
            return DecisionRecord.model_validate_json(row.payload)

    def add_human_event(self, decision_id: str, event: HumanEvent) -> DecisionRecord:
        with Session(self._engine) as session:
            row = session.get(DecisionRecordRow, decision_id)
            if row is None:
                raise KeyError(decision_id)
            current = DecisionRecord.model_validate_json(row.payload)
            updated = current.model_copy(update={"human_events": [*current.human_events, event]})
            # Business state (T5.9): the decision row's payload keeps
            # growing its `human_events` list, same as before T5.10.
            row.payload = updated.model_dump_json()
            # T5.10 (D055): append a NEW, separate `human_event` chain entry
            # instead of touching this decision's existing entry. Nothing
            # previously written to `chain_entries` is ever read back and
            # rewritten here -- append-only, inside the same T5.8-locked
            # session/transaction as the payload update above.
            prev_hash = self._chain_tip(session)
            event_payload = human_event_entry_payload(event)
            record_hash = compute_entry_hash(event_payload, prev_hash)
            session.add(
                ChainEntryRow(
                    kind="human_event",
                    ref_id=decision_id,
                    payload=canonical_json(event_payload),
                    prev_hash=prev_hash,
                    record_hash=record_hash,
                    company_id=row.company_id,
                )
            )
            session.commit()
            return updated

    def add_beneficiary_from_decision(
        self,
        decision_id: str,
        *,
        author: str,
        reason: str,
        at: datetime,
        company_id: str = DEMO_COMPANY_ID,
    ) -> RulesConfig:
        with Session(self._engine) as session:
            rules_row = self._rules_row(session, company_id)
            if rules_row is None:
                raise VendorOnboardingDisabledError()
            rules = RulesConfig.model_validate_json(rules_row.payload)
            onboarding = rules.vendor_onboarding
            if onboarding is None or not onboarding.enabled:
                raise VendorOnboardingDisabledError()
            row = session.get(DecisionRecordRow, decision_id)
            if row is None or row.company_id != company_id:
                raise KeyError(decision_id)
            record = DecisionRecord.model_validate_json(row.payload)
            if not any(c.rule == "R01" and c.result == "FALLA" for c in record.checks):
                raise R01NotFailedError()
            beneficiary = (record.extracted.beneficiary or "").strip()
            if not beneficiary:
                raise ValueError("missing_beneficiary")
            allowed = {normalize_beneficiary(name) for name in rules.allowed_beneficiaries}
            if normalize_beneficiary(beneficiary) in allowed:
                raise AlreadyAllowedError()
            addition = VendorAddition(
                beneficiary=beneficiary,
                added_at=at,
                added_by=author,
                reason=reason,
                source_decision_id=decision_id,
            )
            updated_rules = rules.model_copy(
                update={
                    "allowed_beneficiaries": [*rules.allowed_beneficiaries, beneficiary],
                    "vendor_additions": [*rules.vendor_additions, addition],
                }
            )
            rules_row.payload = updated_rules.model_dump_json()
            change = AllowlistChangePayload(
                beneficiary=beneficiary,
                author=author,
                reason=reason,
                at=at,
                source_decision_id=decision_id,
            )
            prev_hash = self._chain_tip(session)
            payload = allowlist_change_entry_payload(change)
            record_hash = compute_entry_hash(payload, prev_hash)
            session.add(
                ChainEntryRow(
                    kind="allowlist_change",
                    ref_id=decision_id,
                    payload=canonical_json(payload),
                    prev_hash=prev_hash,
                    record_hash=record_hash,
                    company_id=company_id,
                )
            )
            session.commit()
            return updated_rules

    @staticmethod
    def _chain_tip(session: Session) -> str:
        """Current chain tip (the last entry's `record_hash`), or genesis
        when `chain_entries` is empty. Read-only; `seq` is the only order."""
        last_hash = session.scalar(
            select(ChainEntryRow.record_hash).order_by(ChainEntryRow.seq.desc()).limit(1)
        )
        return last_hash if last_hash is not None else GENESIS_PREV_HASH

    @property
    def decisions(self) -> dict[str, DecisionRecord]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(DecisionRecordRow).order_by(DecisionRecordRow.position)
            ).all()
            return {row.id: DecisionRecord.model_validate_json(row.payload) for row in rows}

    def verify_chain(self) -> ChainVerification:
        """GET /decisions/verify-chain (T5.10, D055): walk `chain_entries` in
        `seq` order and, for each entry, recompute its hash from *current*
        stored data -- a `decision` entry re-reads the live
        `DecisionRecordRow` (minus `human_events`, so a legitimate later
        approve/reject never breaks it); a `human_event` entry re-reads its
        own stored, immutable payload. Read-only: never mutates a row.
        """
        with Session(self._engine) as session:
            chain_rows = session.scalars(
                select(ChainEntryRow).order_by(ChainEntryRow.seq)
            ).all()
            entries: list[tuple[str, object, str, str]] = []
            for entry in chain_rows:
                if entry.kind == "decision":
                    decision_row = session.get(DecisionRecordRow, entry.ref_id)
                    if decision_row is None:
                        # The decision this entry is about was deleted
                        # directly in the DB -- report the break here.
                        return ChainVerification(
                            ok=False, length=len(chain_rows), first_broken_id=entry.ref_id
                        )
                    try:
                        record = DecisionRecord.model_validate_json(decision_row.payload)
                    except ValidationError:
                        return ChainVerification(
                            ok=False, length=len(chain_rows), first_broken_id=entry.ref_id
                        )
                    payload: object = decision_entry_payload(record)
                else:
                    if entry.payload is None:
                        return ChainVerification(
                            ok=False, length=len(chain_rows), first_broken_id=entry.ref_id
                        )
                    try:
                        payload = json.loads(entry.payload)
                    except json.JSONDecodeError:
                        return ChainVerification(
                            ok=False, length=len(chain_rows), first_broken_id=entry.ref_id
                        )
                entries.append((entry.ref_id, payload, entry.prev_hash, entry.record_hash))
        return _verify_chain_entries(entries)

    # --- T9.1 (D061): vendor agreement registry ---------------------------------

    @staticmethod
    def _row_to_version(row: VendorAgreementVersionRow) -> VendorAgreementVersion:
        return VendorAgreementVersion(
            vendor_key=row.vendor_key,
            version=row.version,
            terms=parse_vendor_agreement(json.loads(row.terms_json)),
            source_sha256=row.source_sha256,
            spans=json.loads(row.spans_json),
            confirmed_by=row.confirmed_by,
            confirmed_at=row.confirmed_at,
            status=row.status,  # type: ignore[arg-type]
        )

    def list_agreement_vendor_keys(self, *, company_id: str = DEMO_COMPANY_ID) -> list[str]:
        with Session(self._engine) as session:
            keys = session.scalars(
                select(VendorAgreementVersionRow.vendor_key)
                .where(VendorAgreementVersionRow.company_id == company_id)
                .distinct()
            ).all()
            return sorted(keys)

    def list_agreement_versions(
        self, vendor_key: str, *, company_id: str = DEMO_COMPANY_ID
    ) -> list[VendorAgreementVersion]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(VendorAgreementVersionRow)
                .where(
                    VendorAgreementVersionRow.vendor_key == vendor_key,
                    VendorAgreementVersionRow.company_id == company_id,
                )
                .order_by(VendorAgreementVersionRow.version)
            ).all()
            return [self._row_to_version(row) for row in rows]

    def get_active_agreement_version(
        self, vendor_key: str, *, company_id: str = DEMO_COMPANY_ID
    ) -> VendorAgreementVersion | None:
        with Session(self._engine) as session:
            row = session.scalar(
                select(VendorAgreementVersionRow)
                .where(
                    VendorAgreementVersionRow.vendor_key == vendor_key,
                    VendorAgreementVersionRow.status == "active",
                    VendorAgreementVersionRow.company_id == company_id,
                )
                .order_by(VendorAgreementVersionRow.version.desc())
                .limit(1)
            )
            return self._row_to_version(row) if row is not None else None

    def list_active_agreements(
        self, *, company_id: str = DEMO_COMPANY_ID
    ) -> list[ActiveAgreement]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(VendorAgreementVersionRow).where(
                    VendorAgreementVersionRow.status == "active",
                    VendorAgreementVersionRow.company_id == company_id,
                )
            ).all()
            return [
                ActiveAgreement(
                    agreement=parse_vendor_agreement(json.loads(row.terms_json)),
                    version=row.version,
                    confirmed_by=row.confirmed_by,
                    spans=json.loads(row.spans_json),
                )
                for row in rows
            ]

    def confirm_agreement(
        self,
        vendor_key: str,
        *,
        terms: VendorAgreement,
        confirmed_by: str,
        expected_version: int,
        source_sha256: str | None,
        spans: dict[str, str],
        at: datetime,
        company_id: str = DEMO_COMPANY_ID,
    ) -> VendorAgreementVersion:
        from app.rules.agreements import AgreementConflictError

        with Session(self._engine) as session:
            rules_row = self._rules_row(session, company_id)
            if rules_row is not None:
                rules = RulesConfig.model_validate_json(rules_row.payload)
                if vendor_key_conflicts_with_base(rules, vendor_key):
                    raise AgreementConflictError(vendor_key)

            # `current_version` is the latest version number ever assigned to
            # this vendor_key (any status) -- a confirm after a `deactivate`
            # (no `active` row left) must still require that real latest
            # version, not reset to 0 and collide on the unique constraint.
            latest_version = session.scalar(
                select(func.max(VendorAgreementVersionRow.version)).where(
                    VendorAgreementVersionRow.vendor_key == vendor_key,
                    VendorAgreementVersionRow.company_id == company_id,
                )
            )
            current_version = int(latest_version) if latest_version is not None else 0
            if expected_version != current_version:
                raise AgreementVersionConflictError(vendor_key, expected_version, current_version)

            current_row = session.scalar(
                select(VendorAgreementVersionRow).where(
                    VendorAgreementVersionRow.vendor_key == vendor_key,
                    VendorAgreementVersionRow.status == "active",
                    VendorAgreementVersionRow.company_id == company_id,
                )
            )
            if current_row is not None:
                current_row.status = "superseded"

            confirmed_at_iso = at.isoformat().replace("+00:00", "Z")
            terms_json = vendor_agreement_json(terms)
            new_row = VendorAgreementVersionRow(
                vendor_key=vendor_key,
                version=current_version + 1,
                terms_json=terms_json,
                source_sha256=source_sha256,
                spans_json=json.dumps(spans, sort_keys=True),
                confirmed_by=confirmed_by,
                confirmed_at=confirmed_at_iso,
                status="active",
                company_id=company_id,
            )
            session.add(new_row)
            self._append_agreement_change(
                session,
                vendor_key=vendor_key,
                version=current_version + 1,
                status="active",
                confirmed_by=confirmed_by,
                confirmed_at=at,
                terms_json=terms_json,
                source_sha256=source_sha256,
                company_id=company_id,
            )
            session.commit()
            return self._row_to_version(new_row)

    def deactivate_agreement(
        self,
        vendor_key: str,
        *,
        author: str,
        at: datetime,
        company_id: str = DEMO_COMPANY_ID,
    ) -> VendorAgreementVersion:
        with Session(self._engine) as session:
            current_row = session.scalar(
                select(VendorAgreementVersionRow)
                .where(
                    VendorAgreementVersionRow.vendor_key == vendor_key,
                    VendorAgreementVersionRow.status == "active",
                    VendorAgreementVersionRow.company_id == company_id,
                )
                .order_by(VendorAgreementVersionRow.version.desc())
                .limit(1)
            )
            if current_row is None:
                raise AgreementNotFoundError(vendor_key)

            current_row.status = "superseded"
            confirmed_at_iso = at.isoformat().replace("+00:00", "Z")
            new_row = VendorAgreementVersionRow(
                vendor_key=vendor_key,
                version=current_row.version + 1,
                terms_json=current_row.terms_json,
                source_sha256=current_row.source_sha256,
                spans_json=current_row.spans_json,
                confirmed_by=author,
                confirmed_at=confirmed_at_iso,
                status="inactive",
                company_id=company_id,
            )
            session.add(new_row)
            self._append_agreement_change(
                session,
                vendor_key=vendor_key,
                version=current_row.version + 1,
                status="inactive",
                confirmed_by=author,
                confirmed_at=at,
                terms_json=current_row.terms_json,
                source_sha256=current_row.source_sha256,
                company_id=company_id,
            )
            session.commit()
            return self._row_to_version(new_row)

    def _append_agreement_change(
        self,
        session: Session,
        *,
        vendor_key: str,
        version: int,
        status: str,
        confirmed_by: str,
        confirmed_at: datetime,
        terms_json: str,
        source_sha256: str | None,
        company_id: str = DEMO_COMPANY_ID,
    ) -> None:
        terms_hash = hashlib.sha256(terms_json.encode("utf-8")).hexdigest()
        change = AgreementChangePayload(
            vendor_key=vendor_key,
            version=version,
            status=status,
            confirmed_by=confirmed_by,
            confirmed_at=confirmed_at,
            terms_hash=terms_hash,
            source_sha256=source_sha256,
        )
        prev_hash = self._chain_tip(session)
        payload = agreement_change_entry_payload(change)
        record_hash = compute_entry_hash(payload, prev_hash)
        session.add(
            ChainEntryRow(
                kind="agreement_change",
                ref_id=f"{vendor_key}:v{version}",
                payload=canonical_json(payload),
                prev_hash=prev_hash,
                record_hash=record_hash,
                company_id=company_id,
            )
        )
