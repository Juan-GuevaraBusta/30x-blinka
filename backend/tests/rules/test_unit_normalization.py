"""R19 unit matching: singular/plural/English spellings name the same unit."""

from __future__ import annotations

import pytest
from app.rules.variable_pricing import normalize_unit


@pytest.mark.parametrize(
    "raw", ["hora", "horas", "Horas", " HORAS ", "hour", "hours", "h", "hr", "hrs", "hrs."]
)
def test_hour_spellings_normalize_to_hora(raw: str) -> None:
    assert normalize_unit(raw) == "hora"


@pytest.mark.parametrize("raw", ["unidad", "unidades", "Unit", "units"])
def test_unit_spellings_normalize_to_unidad(raw: str) -> None:
    assert normalize_unit(raw) == "unidad"


@pytest.mark.parametrize("raw", ["dia", "día", "días", "DIAS", "day", "days"])
def test_day_spellings_normalize_to_dia(raw: str) -> None:
    assert normalize_unit(raw) == "dia"


def test_distinct_units_never_collapse() -> None:
    assert normalize_unit("horas") != normalize_unit("dias")
    assert normalize_unit("licencias") == "licencias"
    assert normalize_unit("licencias") != normalize_unit("licencia")
