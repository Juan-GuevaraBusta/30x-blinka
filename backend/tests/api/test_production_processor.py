"""G4 production invoice processor: graph wiring without network."""

from __future__ import annotations

from datetime import datetime

import app.api.asgi as asgi_module
import pytest
from app.api.asgi import create_production_app
from app.api.production_processor import make_production_processor
from app.api.schemas import InvoiceRejected, InvoiceUpload
from app.graph.build import GraphError
from app.graph.deps import GraphDeps
from app.models.domain import DecisionRecord
from app.models.rules_config import RulesConfig
from app.persistence import SqlStore
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import create_engine
from tests.api.support import REPO_ROOT, RULES_PATH, load_rules, make_record

_META = {
    "invoice_id": "INV-G4-001",
    "channel": "pdf_text",
    "received_at": "2026-03-04T10:15:00Z",
}


def _upload(**overrides: str) -> InvoiceUpload:
    fields = dict(_META)
    fields.update(overrides)
    return InvoiceUpload(
        invoice_id=fields["invoice_id"],
        channel=fields["channel"],
        received_at=datetime.fromisoformat(fields["received_at"].replace("Z", "+00:00")),
        content=b"%PDF-demo",
    )


def test_process_upload_happy_path_uses_store_rules(tmp_path) -> None:
    db = tmp_path / "proc.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    from app.persistence import init_database, seed_rules

    init_database(engine)
    store = SqlStore(engine)
    seed_rules(store, RULES_PATH)
    expected = make_record(invoice_id="INV-G4-001", id="dec_g4")

    def fake_factory(
        _settings: object,
        rules: RulesConfig,
        _ledger: tuple[object, ...],
    ) -> GraphDeps:
        assert rules.human_approval_threshold == 3000.0
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
        assert kwargs["invoice_id"] == "INV-G4-001"
        assert kwargs["owner_id"] == "usr_synth_001"
        return expected

    processor = make_production_processor(
        store,
        deps_factory=fake_factory,
        checkpointer=MemorySaver(),
    )
    import app.api.production_processor as mod

    original = mod.run_invoice
    mod.run_invoice = fake_run_invoice
    try:
        record = processor(_upload(), "usr_synth_001")
    finally:
        mod.run_invoice = original

    assert record.id == "dec_g4"


def test_graph_error_maps_to_invoice_rejected(tmp_path) -> None:
    db = tmp_path / "rej.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    from app.persistence import init_database, seed_rules

    init_database(engine)
    store = SqlStore(engine)
    seed_rules(store, RULES_PATH)

    def boom_factory(
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
        deps_factory=boom_factory,
        checkpointer=MemorySaver(),
    )
    import app.api.production_processor as mod

    def raise_graph(_deps: GraphDeps, **kwargs: object) -> DecisionRecord:
        raise GraphError("empty_invoice_id")

    original = mod.run_invoice
    mod.run_invoice = raise_graph
    try:
        with pytest.raises(InvoiceRejected) as exc:
            processor(_upload(), "usr_synth_001")
    finally:
        mod.run_invoice = original

    assert exc.value.detail == "empty_invoice_id"


def test_production_app_post_persists_with_mocked_graph(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}"}
    expected = make_record(invoice_id="INV-G4-BOOT", id="dec_boot")

    def fake_processor(upload: InvoiceUpload, owner_id: str) -> DecisionRecord:
        return expected.model_copy(update={"invoice_id": upload.invoice_id})

    monkeypatch.setattr(
        asgi_module,
        "make_production_processor",
        lambda _store, **_: fake_processor,
    )
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    from tests.api.support import USER_HEADERS

    client = TestClient(app, headers=USER_HEADERS)

    response = client.post(
        "/invoices",
        data=_META,
        files={"file": ("invoice.pdf", b"%PDF-demo", "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["id"] == "dec_boot"

    got = client.get("/decisions/dec_boot")
    assert got.status_code == 200
    assert got.json()["summary"] == expected.summary


def test_build_graph_deps_labels_native_jev_backend() -> None:
    """`jev_label` must report the model actually used (`folder_batch.py`'s
    pattern), not always `settings.jev_model` regardless of backend."""
    from app.api.production_processor import build_graph_deps
    from app.config import Settings

    settings = Settings(
        llm_api_key="k",
        llm_base_url="https://llm.test",
        extractor_model="extractor-x",
        verifier_model="verifier-y",
        jev_api_key="jev-key",
        jev_model="jev-native-v1",
        decision_backend="jev",
    )
    deps = build_graph_deps(settings, load_rules(), (), data_root=REPO_ROOT)
    assert deps.jev_label == "jev-native-v1"


def test_build_graph_deps_labels_plan_b_jev_model() -> None:
    """Plan-B (LLM-backed) JEV must label the role model actually used --
    `jev_planb_model`, falling back to `extractor_model` -- never the native
    `jev_model` it never calls."""
    from app.api.production_processor import build_graph_deps
    from app.config import Settings

    settings = Settings(
        llm_api_key="k",
        llm_base_url="https://llm.test",
        extractor_model="extractor-x",
        verifier_model="verifier-y",
        jev_model="jev-native-v1",
        jev_planb_model="planb-model-z",
        decision_backend="plan_b",
    )
    deps = build_graph_deps(settings, load_rules(), (), data_root=REPO_ROOT)
    assert deps.jev_label == "planb-model-z"


def test_build_graph_deps_plan_b_falls_back_to_extractor_model() -> None:
    from app.api.production_processor import build_graph_deps
    from app.config import Settings

    settings = Settings(
        llm_api_key="k",
        llm_base_url="https://llm.test",
        extractor_model="extractor-x",
        verifier_model="verifier-y",
        jev_model="jev-native-v1",
        decision_backend="plan_b",
    )
    deps = build_graph_deps(settings, load_rules(), (), data_root=REPO_ROOT)
    assert deps.jev_label == "extractor-x"


def test_process_upload_reads_fx_from_data_root_not_package_path(tmp_path, monkeypatch) -> None:
    # Render installs the package into site-packages, so the module-relative
    # default fx.json path does not exist there (prod 500 FileNotFoundError).
    import app.api.production_processor as mod
    import app.rules.fx as fx_module

    monkeypatch.setattr(fx_module, "_DEFAULT_FX_PATH", tmp_path / "missing" / "fx.json")
    monkeypatch.setattr(fx_module, "_cached_table", None)

    db = tmp_path / "proc.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    from app.persistence import init_database, seed_rules

    init_database(engine)
    store = SqlStore(engine)
    seed_rules(store, RULES_PATH)
    expected = make_record(invoice_id="INV-G4-001", id="dec_g4")

    def fake_factory(
        _settings: object, rules: RulesConfig, _ledger: tuple[object, ...]
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
        data_root=RULES_PATH.parents[1],
        deps_factory=fake_factory,
        checkpointer=MemorySaver(),
    )
    monkeypatch.setattr(mod, "run_invoice", lambda _deps, **_kw: expected)

    record = processor(_upload(), "usr_synth_001")

    assert record.id == "dec_g4"
