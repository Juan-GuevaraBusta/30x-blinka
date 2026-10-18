"""T7.3 (D059) — Metered invoice lines for variable pricing (outside frozen Extraction)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MeteredLine(BaseModel):
    """Quantities/rates extracted with a literal citation (I7); not trusted for payment."""

    model_config = ConfigDict(extra="forbid")

    quantity: float | None = None
    unit: str = Field(min_length=1)
    unit_rate: float | None = None
    base_amount: float | None = None
    line_amount: float | None = None
    source_span: str = Field(min_length=1)
