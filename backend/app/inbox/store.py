"""T9.2 (D061) §5 — In-memory `inbox_message` store.

In-memory, same convention `app.api.store.MemoryStore` used before its SQL
backend (T4.2) existed: a durable (SQL) inbox store is a natural follow-up
task, deliberately out of scope here to avoid touching the shared
`app/persistence/` tables module while another agent edits adjacent backend
files this same round (see module docstring in `app.inbox`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.inbox.classifier import Classification, ClassifiedBy
from app.inbox.parser import DocumentChannel

InboxEventAction = Literal["procesada_humano", "descartada_humano"]


class InboxSignalBody(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    points: int
    evidence: str


class InboxEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    author: str
    at: AwareDatetime
    action: InboxEventAction
    reason: str


class InboxMessage(BaseModel):
    """§5 `inbox_message` row shape, as the API's public response body."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    owner_id: str
    message_id: str
    from_addr: str
    subject: str
    received_at: AwareDatetime
    classification: Classification
    score: int
    signals: tuple[InboxSignalBody, ...] = Field(default_factory=tuple)
    reason: str
    classified_by: ClassifiedBy
    decision_id: str | None = None
    events: tuple[InboxEvent, ...] = Field(default_factory=tuple)


class InboxStore:
    """Idempotent by `(owner_id, message_id)` (§2). Not thread-safe beyond the
    caller's own `_INVOICE_LOCK` serialization for the mutating paths that
    touch the invoice pipeline; plain reads/writes here are dict operations.
    """

    def __init__(self) -> None:
        self._messages: dict[str, InboxMessage] = {}
        self._by_key: dict[tuple[str, str], str] = {}
        self._documents: dict[str, tuple[DocumentChannel, bytes]] = {}
        self._seq = 0

    def next_id(self) -> str:
        self._seq += 1
        return f"inbox_{self._seq:06d}"

    def find_by_message_id(self, owner_id: str, message_id: str) -> InboxMessage | None:
        found_id = self._by_key.get((owner_id, message_id))
        return self._messages.get(found_id) if found_id is not None else None

    def add(
        self, message: InboxMessage, *, document: tuple[DocumentChannel, bytes]
    ) -> InboxMessage:
        self._messages[message.id] = message
        self._by_key[(message.owner_id, message.message_id)] = message.id
        self._documents[message.id] = document
        return message

    def update(self, message: InboxMessage) -> InboxMessage:
        self._messages[message.id] = message
        return message

    def get_for_owner(self, id: str, owner_id: str) -> InboxMessage | None:
        found = self._messages.get(id)
        if found is None or found.owner_id != owner_id:
            return None
        return found

    def get_document(self, id: str) -> tuple[DocumentChannel, bytes] | None:
        return self._documents.get(id)

    def list_for_owner(self, owner_id: str) -> list[InboxMessage]:
        return [m for m in self._messages.values() if m.owner_id == owner_id]
