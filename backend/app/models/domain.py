"""Frozen v1 domain schemas. Rule logic and decide() are T2.x."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Decision = Literal["PAGAR", "ESCALAR", "FRENAR"]
CheckStatus = Literal["OK", "FALLA", "INDETERMINADO"]
RuleCode = Literal[
    "R01",
    "R02",
    "R03",
    "R04",
    "R05",
    "R06",
    "R07",
    "R08",
    "R09",
    "R10",
    "R11",
    "R12",
    "R13",
    "R14",
    "R15",
    "R16",
    "R17",
    "R18",
    "R19",
    "R20",
]
FailAction = Literal["FRENAR", "ESCALAR"]
JevId = Literal["J1", "J2", "J3", "J4", "J5", "J6", "J7"]
InvoiceType = Literal["servicios", "productos", "suscripción", "honorarios", "otro"]
IssueKind = Literal["violation", "uncertainty"]
HumanAction = Literal["aprobada_humano", "rechazada_humano"]
SEVERITY: dict[str, int] = {"PAGAR": 0, "ESCALAR": 1, "FRENAR": 2}


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LineItem(_Frozen):
    description: str = Field(min_length=1)
    amount: float | None = None
    source_span: str | None = None


class FxQuote(_Frozen):
    rate: float = Field(gt=0)
    date: date


class Extraction(_Frozen):
    """Raw extract. None means missing; T2 escalates. amount_base and fx are filled by T2.2."""

    beneficiary: str | None = None
    amount: float | None = None
    currency: str | None = None
    amount_base: float | None = None
    fx: FxQuote | None = None
    due_date: date | None = None
    invoice_number: str | None = None
    recipient: str | None = None
    department: str | None = None
    invoice_type: InvoiceType | None = None
    lines: list[LineItem] = Field(default_factory=list)
    source_spans: dict[str, str] = Field(default_factory=dict)


class CheckEvidence(_Frozen):
    clause: str | None = None
    quote: str | None = None


class CheckResult(_Frozen):
    rule: RuleCode
    name: str = Field(min_length=1)
    result: CheckStatus
    detail: str = Field(min_length=1)
    on_fail: FailAction | None = None
    evidence: CheckEvidence | None = None


class JevSignal(_Frozen):
    id: JevId
    answer: bool | InvoiceType
    probability: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def answer_matches_question(self) -> JevSignal:
        if self.id == "J5":
            if not isinstance(self.answer, str):
                raise ValueError("J5 answer must be an invoice type")
        elif not isinstance(self.answer, bool):
            raise ValueError("yes/no JEV answers must be bool")
        return self


class VerifierIssue(_Frozen):
    code: str = Field(min_length=1)
    kind: IssueKind
    evidence: str | None = None
    admin_message: str | None = None


class VerifierReport(_Frozen):
    consistent: bool
    issues: list[VerifierIssue]


class HumanEvent(_Frozen):
    author: str = Field(min_length=1)
    at: AwareDatetime
    action: HumanAction
    reason: str = Field(min_length=1)


class TraceRef(_Frozen):
    langsmith_run_id: str | None = None
    url: str | None = None


class ModelVersions(_Frozen):
    rules_version: str = Field(min_length=1)
    model_extractor: str = Field(min_length=1)
    model_verifier: str = Field(min_length=1)
    jev: str = Field(min_length=1)


class DecisionRecord(_Frozen):
    id: str = Field(min_length=1)
    invoice_id: str = Field(min_length=1)
    received_at: AwareDatetime
    decision: Decision
    severity: Literal[0, 1, 2]
    summary: str = Field(min_length=1)
    extracted: Extraction
    checks: list[CheckResult]
    jev_signals: list[JevSignal]
    verifier: VerifierReport
    admin_notice: str | None = None
    next_step: str = Field(min_length=1)
    trace: TraceRef
    versions: ModelVersions
    human_events: list[HumanEvent]

    @model_validator(mode="after")
    def severity_matches_decision(self) -> DecisionRecord:
        if self.severity != SEVERITY[self.decision]:
            raise ValueError("severity must be 0 PAGAR, 1 ESCALAR, 2 FRENAR")
        return self
