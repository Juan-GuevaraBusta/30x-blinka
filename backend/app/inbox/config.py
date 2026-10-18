"""T9.2 (D061) §3 — Scored-signal weights and thresholds for the inbox classifier.

Deliberately NOT part of `app.config.Settings` or `RulesConfig`: the spec requires
these weights to stay out of `PUT /rules` (never editable by a vendor/admin at
runtime), and a brand-new module avoids editing `app/config.py` while another
agent is working on adjacent backend modules this same round.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InboxClassifierConfig(BaseModel):
    """Weights and thresholds from `docs/T9_2_SPEC.md` §3 (D061)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Signal scores (table in §3).
    score_sender_known: int = 3
    score_pdf_attachment: int = 2
    score_pdf_name_bonus: int = 1
    score_keyword: int = 2
    score_amount_pattern: int = 1
    score_invoice_number_pattern: int = 1
    score_due_date: int = 1
    score_bulk_marketing: int = -3
    score_auto_reply: int = -3
    score_payment_reminder_bare: int = -2

    # Thresholds (§3): score >= es_factura -> es_factura; score <= no_es_factura ->
    # no_es_factura; anything strictly in between is the gray zone (desempate).
    threshold_es_factura: int = 5
    threshold_no_es_factura: int = 1

    # How much of the (untrusted, I7) body is shown to the tie-break LLM.
    llm_body_char_limit: int = 4000


def default_inbox_classifier_config() -> InboxClassifierConfig:
    return InboxClassifierConfig()
