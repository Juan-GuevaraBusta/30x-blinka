"""SQL-backed store with the same surface as MemoryStore (T4.2)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.store import DuplicateDecisionError
from app.models.domain import DecisionRecord, HumanEvent
from app.models.rules_config import RulesConfig
from app.persistence.errors import RulesMissing
from app.persistence.tables import DecisionRecordRow, RulesDocument


class SqlStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @property
    def rules(self) -> RulesConfig:
        with Session(self._engine) as session:
            row = session.get(RulesDocument, 1)
            if row is None:
                raise RulesMissing()
            return RulesConfig.model_validate_json(row.payload)

    def put_rules(self, rules: RulesConfig) -> RulesConfig:
        payload = rules.model_dump_json()
        with Session(self._engine) as session:
            row = session.get(RulesDocument, 1)
            if row is None:
                session.add(RulesDocument(id=1, payload=payload))
            else:
                row.payload = payload
            session.commit()
        return rules

    def has_invoice(self, invoice_id: str) -> bool:
        with Session(self._engine) as session:
            found = session.scalar(
                select(DecisionRecordRow.id).where(DecisionRecordRow.invoice_id == invoice_id)
            )
            return found is not None

    def add_decision(self, record: DecisionRecord) -> DecisionRecord:
        payload = record.model_dump_json()
        with Session(self._engine) as session:
            next_position = session.scalar(
                select(func.coalesce(func.max(DecisionRecordRow.position), 0))
            )
            position = int(next_position or 0) + 1
            row = DecisionRecordRow(
                id=record.id,
                invoice_id=record.invoice_id,
                decision=record.decision,
                position=position,
                payload=payload,
            )
            session.add(row)
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
            row.payload = updated.model_dump_json()
            session.commit()
            return updated

    @property
    def decisions(self) -> dict[str, DecisionRecord]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(DecisionRecordRow).order_by(DecisionRecordRow.position)
            ).all()
            return {row.id: DecisionRecord.model_validate_json(row.payload) for row in rows}
