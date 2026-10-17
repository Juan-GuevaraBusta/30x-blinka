"""FX conversion to base currency using fixed table (docs/04 §4, T2.2)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from app.models.domain import FxQuote
from app.rules.normalize import normalize_amount, normalize_currency

FxError = Literal["missing_amount", "missing_currency", "unknown_currency"]

_DEFAULT_FX_PATH = Path(__file__).resolve().parents[3] / "data" / "fx.json"
_cached_table: FxTable | None = None


@dataclass(frozen=True)
class FxTable:
    as_of: date
    base_currency: str
    quote: str
    rates: Mapping[str, float]


@dataclass(frozen=True)
class FxConversionResult:
    amount_base: float | None
    fx: FxQuote | None
    currency: str | None
    error: FxError | None


def load_fx_table(path: Path | None = None, *, reload: bool = False) -> FxTable:
    global _cached_table
    resolved = path if path is not None else _DEFAULT_FX_PATH
    if not reload and path is None and _cached_table is not None:
        return _cached_table

    raw = json.loads(resolved.read_text(encoding="utf-8"))
    as_of = date.fromisoformat(str(raw["as_of"]))
    rates = {str(k): float(v) for k, v in raw["rates"].items()}
    table = FxTable(
        as_of=as_of,
        base_currency=str(raw["base_currency"]),
        quote=str(raw["quote"]),
        rates=rates,
    )
    if path is None:
        _cached_table = table
    return table


def convert_to_base(
    amount: float | int | str | None,
    currency: str | None,
    table: FxTable,
) -> FxConversionResult:
    parsed_amount = normalize_amount(amount)
    if parsed_amount is None:
        return FxConversionResult(
            amount_base=None,
            fx=None,
            currency=normalize_currency(currency),
            error="missing_amount",
        )

    code = normalize_currency(currency)
    if code is None:
        return FxConversionResult(
            amount_base=None,
            fx=None,
            currency=None,
            error="missing_currency",
        )

    rate = table.rates.get(code)
    if rate is None:
        return FxConversionResult(
            amount_base=None,
            fx=None,
            currency=code,
            error="unknown_currency",
        )

    rate_f = float(rate)
    amount_base = round(parsed_amount * rate_f, 2)
    return FxConversionResult(
        amount_base=amount_base,
        fx=FxQuote(rate=rate_f, date=table.as_of),
        currency=code,
        error=None,
    )
