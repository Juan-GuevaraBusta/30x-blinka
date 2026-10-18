"""T9.2 (D061) §2 — HTTP request bodies for `POST /inbox` (JSON input shape) and
the human actions on an inbox message.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InboxAttachmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = ""
    content_base64: str = Field(min_length=1)


class InboxEmailIn(BaseModel):
    """`POST /inbox` JSON body (§2), as an alternative to a multipart `.eml`."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    message_id: str | None = None
    from_addr: str = Field(min_length=1, alias="from")
    to_addr: str = Field(default="", alias="to")
    subject: str = ""
    date: str | None = None
    body_text: str = ""
    attachments: list[InboxAttachmentIn] = Field(default_factory=list)


class InboxProcessBody(BaseModel):
    """`POST /inbox/{id}/process` (§5): author must be a known approver."""

    model_config = ConfigDict(extra="forbid")

    author: str = Field(min_length=1, max_length=500)


class InboxDismissBody(BaseModel):
    """`POST /inbox/{id}/dismiss` (§5): leaves an event, never deletes."""

    model_config = ConfigDict(extra="forbid")

    author: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=500)
