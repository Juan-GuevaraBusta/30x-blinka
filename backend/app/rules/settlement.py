"""T5.13 (D063) — Base-currency amount for extractions and ledger settlements.

The extractor never fills ``amount_base`` (``extract.py`` sets ``None``); before
T5.13 every settlement stored ``float(None or 0.0)`` = 0.0, so R03/R07/R05-probable
never accumulated in production. The graph now fills ``amount_base``/``fx`` once
from the fixed FX table, and every settlement recomputes it from
``amount`` + ``currency``. When no conversion is possible the ledger line carries
``amount_base=None`` (never 0.0) and every sum over it is INDETERMINADO.
"""

from __future__ import annotations

from app.models.domain import Extraction
from app.rules.fx import FxTable, convert_to_base


def with_base_amount(extraction: Extraction, fx: FxTable) -> Extraction:
    """Fill ``amount_base``/``fx`` from ``amount`` + ``currency`` (overwrites any value)."""
    converted = convert_to_base(extraction.amount, extraction.currency, fx)
    return extraction.model_copy(update={"amount_base": converted.amount_base, "fx": converted.fx})


def settlement_amount_base(extraction: Extraction, fx: FxTable) -> float | None:
    """Base amount for a ledger line; ``None`` when it cannot be established."""
    converted = convert_to_base(extraction.amount, extraction.currency, fx)
    if converted.amount_base is not None:
        return converted.amount_base
    if extraction.amount_base is not None:
        return float(extraction.amount_base)
    return None
