"""HTTP bodies for T4.1. Domain records stay in `app.models`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.models.agreement import VendorAgreement, VendorAgreementVersion
from app.models.rules_config import RulesConfig

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


class ApprovalStatusBody(BaseModel):
    """GET /decisions/{id}/approval response (T7.1, D059 §4). Read-only."""

    model_config = ConfigDict(extra="forbid")

    route_id: str | None
    required: int
    collected: int
    approvers: list[str]
    satisfied: bool
    rejected: bool
    payment_ready: bool
    pending_checks: list[str]


class ChainVerificationBody(BaseModel):
    """GET /decisions/verify-chain response (T5.10, D055). Public, read-only."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    length: int
    first_broken_id: str | None


# --- T9.1 (D061): vendor agreement registry -----------------------------------


class AgreementDraftResponseBody(BaseModel):
    """POST /agreements/draft response (§3). Never persisted."""

    model_config = ConfigDict(extra="forbid")

    draft: dict[str, object]
    spans: dict[str, str]
    missing: list[str]
    source_sha256: str


class ConfirmAgreementBody(BaseModel):
    """PUT /agreements/{vendor_key} (§3)."""

    model_config = ConfigDict(extra="forbid")

    terms: VendorAgreement
    confirmed_by: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=0)
    source_sha256: str | None = None
    spans: dict[str, str] = Field(default_factory=dict)


class DeactivateAgreementBody(BaseModel):
    """POST /agreements/{vendor_key}/deactivate (§3). Admin-key gated; `author`
    is logged on the new `inactive` version and the `agreement_change` entry,
    same audit convention as T7.4's add-beneficiary action.
    """

    model_config = ConfigDict(extra="forbid")

    author: str = Field(min_length=1, max_length=500)


class AgreementListEntryBody(BaseModel):
    """One row of GET /agreements (§3): the vendor's current active version."""

    model_config = ConfigDict(extra="forbid")

    vendor_key: str
    vendor_name: str
    kind: str
    version: int
    status: Literal["active", "superseded", "inactive"]
    confirmed_by: str
    confirmed_at: AwareDatetime
    valid_from: str
    valid_to: str | None


class AgreementHistoryBody(BaseModel):
    """GET /agreements/{vendor_key} (§3): current + full version history."""

    model_config = ConfigDict(extra="forbid")

    vendor_key: str
    active: VendorAgreementVersion | None
    versions: list[VendorAgreementVersion]


class EffectiveRulesBody(BaseModel):
    """GET /rules/effective (§3): compiled rules plus provenance."""

    model_config = ConfigDict(extra="forbid")

    rules: RulesConfig
    provenance: dict[str, str]
