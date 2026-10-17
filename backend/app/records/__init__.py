"""Decision records and explanation templates. No LLM."""

from app.records import templates
from app.records.build import (
    RecordContext,
    build_admin_notice,
    build_next_step,
    build_summary,
    build_technical_error_summary,
    build_verifier_summary,
    enrich_check_details,
    format_check_detail,
)

__all__ = [
    "RecordContext",
    "build_admin_notice",
    "build_next_step",
    "build_summary",
    "build_technical_error_summary",
    "build_verifier_summary",
    "enrich_check_details",
    "format_check_detail",
    "templates",
]
