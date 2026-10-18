"""T9.2 (D061) §3 — Deterministic scored signals for the inbox classifier.

Every signal carries its point value and a short, readable Spanish evidence
string (I5: explanations come from templates over rule results, never from an
LLM as source of truth).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.inbox.config import InboxClassifierConfig
from app.inbox.parser import InboxAttachment, ParsedEmail, sender_domain, sender_email_address
from app.rules.normalize import normalize_beneficiary

# Domain labels too generic to count as a vendor-name match on their own.
_GENERIC_DOMAIN_TOKENS = frozenset(
    {"com", "co", "net", "org", "demo", "test", "mail", "info", "billing", "ap"}
)

_KEYWORDS: tuple[str, ...] = (
    "cuenta de cobro",
    "n.º de factura",
    "n° de factura",
    "factura",
    "invoice",
    "bill",
)

_CURRENCY_CODE = r"USD|EUR|COP|MXN|GBP"
_AMOUNT_NUMBER = r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?"
_AMOUNT_PATTERN = re.compile(
    rf"(?:(?:{_CURRENCY_CODE}|\$)\s?{_AMOUNT_NUMBER})|(?:{_AMOUNT_NUMBER}\s?(?:{_CURRENCY_CODE}))",
    re.IGNORECASE,
)
_INVOICE_NUMBER_PATTERN = re.compile(
    r"\b(?:INV|FAC)-[A-Za-z0-9-]+\b|factura\s+n[.ºo]?\s*\d+",
    re.IGNORECASE,
)
_DUE_DATE_PATTERN = re.compile(
    r"\bvence\b|\bvencimiento\b|\bdue date\b", re.IGNORECASE
)
_AUTO_REPLY_PHRASES: tuple[str, ...] = (
    "fuera de la oficina",
    "out of office",
    "respuesta automática",
    "automatic reply",
)
_PAYMENT_REMINDER_PHRASES: tuple[str, ...] = (
    "recordatorio de pago",
    "payment reminder",
    "pago pendiente",
    "saldo pendiente",
)


@dataclass(frozen=True)
class InboxSignal:
    id: str
    points: int
    evidence: str


def _text_blob(parsed: ParsedEmail) -> str:
    return f"{parsed.subject}\n{parsed.body_text}"


def _domain_tokens(domain: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", domain.lower())
        if token and token not in _GENERIC_DOMAIN_TOKENS
    }


def _domain_matches_known_vendor(domain: str, allowed_beneficiaries: tuple[str, ...]) -> str | None:
    """Fallback sender signal when no T9.1 `sender_emails` list is available.

    Pure heuristic over the sender's domain vs. normalized vendor names: no
    real contact-list lookup exists in the MVP, so this stays a best-effort,
    deterministic match (never a network call, never an LLM).
    """
    domain_tokens = _domain_tokens(domain)
    if not domain_tokens:
        return None
    for name in allowed_beneficiaries:
        normalized = normalize_beneficiary(name) or ""
        name_tokens = {t for t in normalized.split() if len(t) >= 4}
        if not name_tokens:
            continue
        for d_token in domain_tokens:
            if len(d_token) < 4:
                continue
            for n_token in name_tokens:
                if d_token == n_token or d_token in n_token or n_token in d_token:
                    return name
    return None


def _sender_known_evidence(
    parsed: ParsedEmail,
    *,
    sender_emails: frozenset[str],
    allowed_beneficiaries: tuple[str, ...],
) -> str | None:
    address = sender_email_address(parsed.from_addr)
    if address and address in sender_emails:
        return f'Remitente "{address}" está en sender_emails de un acuerdo activo.'
    domain = sender_domain(parsed.from_addr)
    matched_vendor = _domain_matches_known_vendor(domain, allowed_beneficiaries)
    if matched_vendor is not None:
        return f'Dominio "{domain}" asociado al proveedor permitido "{matched_vendor}".'
    return None


def compute_signals(
    parsed: ParsedEmail,
    *,
    config: InboxClassifierConfig,
    sender_emails: frozenset[str],
    allowed_beneficiaries: tuple[str, ...],
    pdf_attachments: tuple[InboxAttachment, ...],
) -> list[InboxSignal]:
    signals: list[InboxSignal] = []
    text = _text_blob(parsed)
    lowered = text.lower()

    sender_evidence = _sender_known_evidence(
        parsed, sender_emails=sender_emails, allowed_beneficiaries=allowed_beneficiaries
    )
    if sender_evidence is not None:
        signals.append(
            InboxSignal(
                id="sender_known",
                points=config.score_sender_known,
                evidence=sender_evidence,
            )
        )

    if pdf_attachments:
        pdf = pdf_attachments[0]
        signals.append(
            InboxSignal(
                id="pdf_attachment",
                points=config.score_pdf_attachment,
                evidence=f'Adjunto PDF: "{pdf.filename}".',
            )
        )
        if any(kw in pdf.filename.lower() for kw in ("factura", "invoice", "cuenta de cobro")):
            signals.append(
                InboxSignal(
                    id="pdf_name_bonus",
                    points=config.score_pdf_name_bonus,
                    evidence=f'Nombre del adjunto sugiere factura: "{pdf.filename}".',
                )
            )

    for keyword in _KEYWORDS:
        if keyword in lowered:
            signals.append(
                InboxSignal(
                    id="keyword",
                    points=config.score_keyword,
                    evidence=f'Palabra clave de factura "{keyword}" en asunto o cuerpo.',
                )
            )
            break  # one keyword signal total, per §3's table

    amount_match = _AMOUNT_PATTERN.search(text)
    if amount_match:
        signals.append(
            InboxSignal(
                id="amount_pattern",
                points=config.score_amount_pattern,
                evidence=f'Patrón de monto con moneda: "{amount_match.group(0)}".',
            )
        )

    invoice_number_match = _INVOICE_NUMBER_PATTERN.search(text)
    if invoice_number_match:
        signals.append(
            InboxSignal(
                id="invoice_number_pattern",
                points=config.score_invoice_number_pattern,
                evidence=f'Patrón de número de factura: "{invoice_number_match.group(0)}".',
            )
        )

    if _DUE_DATE_PATTERN.search(lowered):
        signals.append(
            InboxSignal(
                id="due_date",
                points=config.score_due_date,
                evidence="Fecha de vencimiento mencionada (vence / due date).",
            )
        )

    if parsed.list_unsubscribe or parsed.precedence_bulk:
        signals.append(
            InboxSignal(
                id="bulk_marketing",
                points=config.score_bulk_marketing,
                evidence="Encabezado List-Unsubscribe o Precedence: bulk presente.",
            )
        )

    if parsed.auto_submitted or any(phrase in lowered for phrase in _AUTO_REPLY_PHRASES):
        signals.append(
            InboxSignal(
                id="auto_reply",
                points=config.score_auto_reply,
                evidence="Respuesta automática (Auto-Submitted o frase de fuera de oficina).",
            )
        )

    bare_signals = invoice_number_match is None and amount_match is None and not pdf_attachments
    if bare_signals and any(phrase in lowered for phrase in _PAYMENT_REMINDER_PHRASES):
        signals.append(
            InboxSignal(
                id="payment_reminder_bare",
                points=config.score_payment_reminder_bare,
                evidence="Recordatorio de pago sin número de factura, monto ni adjunto.",
            )
        )

    return signals
