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


# --------------------------------------------------------------------------------------
# T5.13 (D063) — invoice-number normalization and strict party identity (R01/R05/R08)
# --------------------------------------------------------------------------------------

_INVOICE_RUN = re.compile(r"[0-9]+|[^\W\d_]+")

# Equivalent spellings of the SAME legal form map to one canonical token. Different
# legal forms stay distinct (LLC != Inc != S.A.); dotted acronyms such as "L.L.C." or
# "S.A.S" are NOT collapsed, so they never match the undotted form (fail closed).
_LEGAL_FORMS: dict[str, str] = {
    "llc": "llc",
    "ltd": "ltd",
    "limited": "ltd",
    "ltda": "ltda",
    "inc": "inc",
    "incorporated": "inc",
    "corp": "corp",
    "corporation": "corp",
    "co": "co",
    "sa": "sa",
    "sas": "sas",
    "spa": "spa",
}


def normalize_invoice_number(raw: str | None) -> str | None:
    """Canonical invoice number for duplicate detection (R05).

    NFKC + casefold, split into letter runs and digit runs, strip leading zeros in
    digit runs, drop every separator: ``INV-001`` == ``inv 001`` == ``INV-0001`` ==
    ``INV.001`` == ``INV001``. Runs are joined with ``-`` so ``A-1-2`` != ``A-12``.
    An empty result counts as missing (``None``).
    """
    if raw is None:
        return None
    text = unicodedata.normalize("NFKC", raw).casefold()
    runs = [
        (run.lstrip("0") or "0") if run.isdigit() else run
        for run in _INVOICE_RUN.findall(text)
    ]
    return "-".join(runs) or None


def _has_invisible_format_chars(text: str) -> bool:
    return any(unicodedata.category(ch) == "Cf" for ch in text)


def _mixes_scripts(text: str) -> bool:
    """True when non-ASCII letters (after accent stripping) mix with ASCII letters."""
    stripped = _strip_accents(text)
    letters = [ch for ch in stripped if ch.isalpha()]
    has_ascii = any(ch.isascii() for ch in letters)
    has_other = any(not ch.isascii() for ch in letters)
    return has_ascii and has_other


def party_identity(raw: str | None) -> tuple[str, tuple[str, ...]] | None:
    """Strict identity ``(base name, canonical legal forms)`` for R01/R08.

    Returns ``None`` (never matches anything) for missing names, names with
    invisible format characters (zero-width) or names mixing ASCII letters with
    other-script letters (homoglyph lookalikes), after NFKC.
    """
    if raw is None:
        return None
    text = unicodedata.normalize("NFKC", raw)
    if _has_invisible_format_chars(text) or _mixes_scripts(text):
        return None
    collapsed = _strip_accents(text).casefold()
    collapsed = re.sub(r"[^\w\s]", " ", collapsed)
    parts = collapsed.split()
    if not parts:
        return None
    forms: list[str] = []
    while len(parts) > 1 and parts[-1] in _LEGAL_FORMS:
        forms.insert(0, _LEGAL_FORMS[parts.pop()])
    return " ".join(parts), tuple(forms)


def same_party(left: str | None, right: str | None) -> bool:
    """Same legal entity: same base name AND same canonical legal form (fail closed)."""
    a = party_identity(left)
    b = party_identity(right)
    return a is not None and b is not None and a == b
