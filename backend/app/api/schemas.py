"""HTTP bodies for T4.1. Domain records stay in `app.models`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

ChannelName = Literal["pdf_text", "image", "email", "chat"]
MAX_INVOICE_BYTES = 2_000_000


class InvoiceRejected(Exception):
    """Processor refused the upload. `detail` is a short public code, never a traceback."""

    def __init__(self, detail: str) -> None:
        cleaned = " ".join(detail.split())
        if not cleaned or len(cleaned) > 120:
            cleaned = "rejected"
        super().__init__(cleaned)
        self.detail = cleaned


@dataclass(frozen=True)
class InvoiceUpload:
    invoice_id: str
    channel: ChannelName
    received_at: datetime
    content: bytes


class InvoiceMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: str = Field(min_length=1, max_length=64, pattern=r"^\S+$")
    channel: ChannelName
    received_at: AwareDatetime


class HumanDecisionBody(BaseModel):
    """Author and reason only. The client does not send `at` or a new decision."""

    model_config = ConfigDict(extra="forbid")

    author: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=500)


class MetricsReading:
    """Numbers from an injected reader. This task does not open `eval/reports/`."""

    def __init__(self, *, unsafe_pay: int | float, autonomy_pct: int | float) -> None:
        self.unsafe_pay = unsafe_pay
        self.autonomy_pct = autonomy_pct


class MetricsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # I9: null means "no report", not a claim that unsafe_pay is 0.
    unsafe_pay: int | float | None
    autonomy_pct: int | float | None
    source: Literal["none", "report"]
