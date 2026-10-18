"""T4.10: pipeline smoke with external synthetic PDFs (no network).

Strategy A per docs/PIPELINE_SMOKE_EXTERNAL_SPEC.md: real PDF bytes on disk,
`make_production_processor` with `run_invoice` mocked to return a valid record.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from app.api.production_processor import make_production_processor
from app.api.schemas import InvoiceUpload
from app.graph.build import GraphError
from app.graph.deps import GraphDeps
from app.models.domain import DecisionRecord
from app.models.rules_config import RulesConfig
from app.persistence import SqlStore, init_database, seed_rules
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import create_engine
from tests.api.support import RULES_PATH, make_record

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SMOKE_DIR = _REPO_ROOT / "data" / "invoices" / "smoke-external"
_PDF_FIXTURES = sorted(_SMOKE_DIR.glob("external-smoke-*.pdf"))

_META = {
    "invoice_id": "garage-smoke-001",
    "channel": "pdf_text",
    "received_at": "2025-12-22T10:00:00Z",
}


def _upload(pdf_path: Path, invoice_id: str = "garage-smoke-001") -> InvoiceUpload:
    return InvoiceUpload(
        invoice_id=invoice_id,
        channel=_META["channel"],
        received_at=datetime.fromisoformat(_META["received_at"].replace("Z", "+00:00")),
        content=pdf_path.read_bytes(),
    )


@pytest.mark.parametrize("pdf_path", _PDF_FIXTURES, ids=[p.name for p in _PDF_FIXTURES])
def test_external_pdf_ingest_and_processor_schema(tmp_path: Path, pdf_path: Path) -> None:
    assert pdf_path.is_file(), f"missing fixture {pdf_path}"
    db = tmp_path / "smoke.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    init_database(engine)
    store = SqlStore(engine)
    seed_rules(store, RULES_PATH)
    expected = make_record(invoice_id="garage-smoke-001", id="dec_smoke_ext")

    def fake_factory(
        _settings: object,
        rules: RulesConfig,
        _ledger: tuple[object, ...],
    ) -> GraphDeps:
        return GraphDeps(
            extractor=object(),
            verifier=object(),
            jev=object(),
            rules=rules,
            fx=object(),
            ledger=(),
            company_name=rules.company.name,
            rules_version="v1",
            model_extractor="x",
            model_verifier="y",
            jev_label="z",
        )

    def fake_run_invoice(_deps: GraphDeps, **kwargs: object) -> DecisionRecord:
        assert kwargs["phase"] == "demo"
        assert kwargs["raw"]  # ingest path exercised before mock returns
        return expected

    processor = make_production_processor(
        store,
        deps_factory=fake_factory,
        checkpointer=MemorySaver(),
        data_root=_REPO_ROOT,
    )
    import app.api.production_processor as mod

    original = mod.run_invoice
    mod.run_invoice = fake_run_invoice
    try:
        record = processor(_upload(pdf_path, invoice_id=f"garage-{pdf_path.stem}"), "test-user-id")
    finally:
        mod.run_invoice = original

    assert isinstance(record, DecisionRecord)
    assert record.decision in ("PAGAR", "ESCALAR", "FRENAR")


def test_external_pdf_graph_error_fail_closed(tmp_path: Path) -> None:
    pdf_path = _PDF_FIXTURES[0]
    db = tmp_path / "smoke_err.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    init_database(engine)
    store = SqlStore(engine)
    seed_rules(store, RULES_PATH)

    def fake_factory(
        _settings: object,
        rules: RulesConfig,
        _ledger: tuple[object, ...],
    ) -> GraphDeps:
        return GraphDeps(
            extractor=object(),
            verifier=object(),
            jev=object(),
            rules=rules,
            fx=object(),
            ledger=(),
            company_name=rules.company.name,
            rules_version="v1",
            model_extractor="x",
            model_verifier="y",
            jev_label="z",
        )

    processor = make_production_processor(
        store,
        deps_factory=fake_factory,
        checkpointer=MemorySaver(),
        data_root=_REPO_ROOT,
    )
    import app.api.production_processor as mod
    from app.api.schemas import InvoiceRejected

    def raise_graph(_deps: GraphDeps, **kwargs: object) -> DecisionRecord:
        raise GraphError("error_tecnico")

    original = mod.run_invoice
    mod.run_invoice = raise_graph
    try:
        with pytest.raises(InvoiceRejected):
            processor(_upload(pdf_path, invoice_id="garage-smoke-err"), "test-user-id")
    finally:
        mod.run_invoice = original
