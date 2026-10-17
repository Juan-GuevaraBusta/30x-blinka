"""Normalize extracted fields before deterministic rule checks (docs/04 §4)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

# Trailing legal suffixes removed after lowercasing (docs/04 beneficiary normalization).
_SUFFIX_TOKENS = frozenset(
    {
        "llc",
        "ltd",
        "ltda",
        "inc",
        "corp",
        "co",
        "sa",
        "sas",
        "spa",
        "limited",
        "corporation",
    }
)


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_party_name(raw: str | None) -> str | None:
    """Lowercase, no accents/punctuation, strip common corporate suffixes."""
    if raw is None:
        return None
    collapsed = _strip_accents(raw).lower()
    collapsed = re.sub(r"[^\w\s]", " ", collapsed)
    collapsed = re.sub(r"\s+", " ", collapsed).strip()
    if not collapsed:
        return None
    parts = collapsed.split()
    while len(parts) > 1 and parts[-1] in _SUFFIX_TOKENS:
        parts.pop()
    if len(parts) >= 2 and parts[-2] == "s" and parts[-1] == "a":
        parts.pop()
        parts.pop()
    return " ".join(parts) if parts else None


def normalize_beneficiary(raw: str | None) -> str | None:
    return normalize_party_name(raw)


def normalize_currency(raw: str | None) -> str | None:
    if raw is None:
        return None
    code = raw.strip().upper()
    return code if code else None


def normalize_due_date(raw: date | str | None) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    text = raw.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def normalize_amount(raw: float | int | str | None) -> float | None:
    """Parse numeric amounts including EU and US grouping (adversarial set in DATA_MANIFEST)."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return float(raw)

    text = str(raw).strip()
    if not text:
        return None

    cleaned = re.sub(r"[^\d,.\-]", "", text)
    if not cleaned or cleaned in {"-", ".", ",", "-.", "-,"}:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        left, right = cleaned.split(",", 1)
        if right.isdigit() and len(right) <= 2:
            cleaned = f"{left.replace('.', '')}.{right}"
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")

    try:
        return float(cleaned)
    except ValueError:
        return None
