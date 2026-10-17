"""In-memory rules, decisions, and human events. Disk and SQL are T4.2."""

from __future__ import annotations

from app.models.domain import DecisionRecord, HumanEvent
from app.models.rules_config import RulesConfig


class DuplicateDecisionError(Exception):
    def __init__(self, invoice_id: str) -> None:
        super().__init__(invoice_id)
        self.invoice_id = invoice_id


class MemoryStore:
    def __init__(self, rules: RulesConfig) -> None:
        self.rules = rules
        self.decisions: dict[str, DecisionRecord] = {}
        self._invoice_ids: set[str] = set()

    def put_rules(self, rules: RulesConfig) -> RulesConfig:
        """Replace rules only. Caller must pass an already validated `RulesConfig`."""
        self.rules = rules
        return self.rules

    def has_invoice(self, invoice_id: str) -> bool:
        return invoice_id in self._invoice_ids

    def add_decision(self, record: DecisionRecord) -> DecisionRecord:
        if record.id in self.decisions or record.invoice_id in self._invoice_ids:
            raise DuplicateDecisionError(record.invoice_id)
        self.decisions[record.id] = record
        self._invoice_ids.add(record.invoice_id)
        return record

    def get(self, decision_id: str) -> DecisionRecord | None:
        return self.decisions.get(decision_id)

    def add_human_event(self, decision_id: str, event: HumanEvent) -> DecisionRecord:
        """Copy the record. The previous object stays unchanged for any other holder."""
        current = self.decisions[decision_id]
        updated = current.model_copy(update={"human_events": [*current.human_events, event]})
        self.decisions[decision_id] = updated
        return updated
