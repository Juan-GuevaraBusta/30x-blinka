"""T5.1.3 — eval/run_eval.py wiring tests (docs/T5_1_SPEC.md §5).

Only injected fakes/doubles exercise the "run the graph" path: this machine
has no .env / API keys, so the real graph is never invoked here. Every
fixture is synthetic. This module never opens data/golden/holdout.json or
data/invoices/holdout/ -- it always points those arguments at paths that do
not exist, so if the holdout lock were ever bypassed the test would fail
with a loud FileNotFoundError instead of silently passing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

import run_eval


def _board_text(estado: str) -> str:
    return (
        "| ID | Nombre | Fase | Dueño | Skill | Depende | Estado | Evidencia | Notas |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        f"| T5.2 | Calibrar JEV solo con dev | F5 | QA & Eval | NINGUNA | T5.7, G3 | {estado} |"
        ' nota con la palabra HECHA dentro de Evidencia | "HECHA" mencionada aquí también |\n'
    )


def _write(path: Path, payload: dict | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    path.write_text(text, encoding="utf-8")
    return path


def _golden(entries: list[dict]) -> dict:
    return {"schema_version": 1, "entries": entries}


def _decisions(records: list[dict]) -> dict:
    return {"schema_version": 1, "phase": "eval", "records": records}


def _record(invoice_id: str, decision: str) -> dict:
    return {
        "invoice_id": invoice_id,
        "decision": decision,
        "summary": f"Resumen sintético para {invoice_id} ({decision}).",
        "extracted": {"beneficiary": "Acme Demo Inc."},
        "checks": [],
        "human_events": [],
        "verifier": {"consistent": True, "issues": []},
        "versions": {
            "rules_version": "v1",
            "model_extractor": "fake-extractor",
            "model_verifier": "fake-verifier",
            "jev": "fake-jev",
        },
    }


# -- holdout lock (board parsing) ------------------------------------------------------


def test_board_t5_2_estado_reads_only_column_seven() -> None:
    # Columns 8/9 (Evidencia/Notas) mention "HECHA" on purpose; must be ignored.
    text = _board_text("PENDIENTE")
    assert run_eval.board_t5_2_estado(text) == "PENDIENTE"


def test_board_t5_2_estado_missing_row_returns_none() -> None:
    assert run_eval.board_t5_2_estado("| T5.1 | x | y | z | w | v | PENDIENTE | e | n |") is None


def test_check_holdout_gate_raises_when_not_hecha(tmp_path: Path) -> None:
    board = _write(tmp_path / "board.md", _board_text("PENDIENTE"))
    with pytest.raises(run_eval.HoldoutLockedError) as exc_info:
        run_eval.check_holdout_gate(board)
    assert exc_info.value.estado == "PENDIENTE"


@pytest.mark.parametrize("estado", ["HECHA", "HECHO"])
def test_check_holdout_gate_passes_when_hecha_or_hecho(tmp_path: Path, estado: str) -> None:
    board = _write(tmp_path / "board.md", _board_text(estado))
    run_eval.check_holdout_gate(board)  # must not raise


# -- CLI wiring ---------------------------------------------------------------------------


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_eval.main(["--help"])
    assert exc_info.value.code == 0


def test_run_dev_only_skip_graph_writes_report(tmp_path: Path) -> None:
    golden_dev = _write(
        tmp_path / "golden_dev.json",
        _golden([{"invoice_id": "dev-001", "expected_decision": "PAGAR", "expected_rules": []}]),
    )
    decisions_dev = _write(
        tmp_path / "decisions_dev.json", _decisions([_record("dev-001", "PAGAR")])
    )
    board = _write(tmp_path / "board.md", _board_text("PENDIENTE"))
    output = tmp_path / "latest.md"
    missing_holdout_golden = tmp_path / "does-not-exist-holdout.json"

    code = run_eval.main(
        [
            "--output",
            str(output),
            "--skip-graph",
            "--golden-dev",
            str(golden_dev),
            "--decisions-dev",
            str(decisions_dev),
            "--golden-holdout",
            str(missing_holdout_golden),
            "--board",
            str(board),
        ]
    )
    assert code == 0
    text = output.read_text(encoding="utf-8")
    assert "El holdout no se usó para calibrar umbrales." in text
    assert "pendiente T5.3" in text
    assert "| dev | 1 |" in text


def test_run_include_holdout_refused_when_board_pending(tmp_path: Path) -> None:
    golden_dev = _write(
        tmp_path / "golden_dev.json",
        _golden([{"invoice_id": "dev-001", "expected_decision": "PAGAR", "expected_rules": []}]),
    )
    decisions_dev = _write(
        tmp_path / "decisions_dev.json", _decisions([_record("dev-001", "PAGAR")])
    )
    board = _write(tmp_path / "board.md", _board_text("PENDIENTE"))
    output = tmp_path / "latest.md"
    # Paths that do not exist: if the gate were bypassed, reading them would
    # raise FileNotFoundError instead of returning 2.
    missing_golden_holdout = tmp_path / "data" / "golden" / "holdout.json"
    missing_decisions_holdout = tmp_path / "decisions_holdout.json"

    code = run_eval.main(
        [
            "--output",
            str(output),
            "--skip-graph",
            "--include-holdout",
            "--golden-dev",
            str(golden_dev),
            "--decisions-dev",
            str(decisions_dev),
            "--golden-holdout",
            str(missing_golden_holdout),
            "--decisions-holdout",
            str(missing_decisions_holdout),
            "--board",
            str(board),
        ]
    )
    assert code == 2
    assert not output.exists()
    assert not missing_golden_holdout.exists()


@pytest.mark.parametrize("estado", ["HECHA", "HECHO"])
def test_run_include_holdout_allowed_when_board_closed(tmp_path: Path, estado: str) -> None:
    golden_dev = _write(
        tmp_path / "golden_dev.json",
        _golden([{"invoice_id": "dev-001", "expected_decision": "PAGAR", "expected_rules": []}]),
    )
    decisions_dev = _write(
        tmp_path / "decisions_dev.json", _decisions([_record("dev-001", "PAGAR")])
    )
    golden_holdout = _write(
        tmp_path / "golden_holdout.json",
        _golden(
            [{"invoice_id": "hold-001", "expected_decision": "FRENAR", "expected_rules": ["R01"]}]
        ),
    )
    decisions_holdout = _write(
        tmp_path / "decisions_holdout.json", _decisions([_record("hold-001", "FRENAR")])
    )
    board = _write(tmp_path / "board.md", _board_text(estado))
    output = tmp_path / "latest.md"

    code = run_eval.main(
        [
            "--output",
            str(output),
            "--skip-graph",
            "--include-holdout",
            "--golden-dev",
            str(golden_dev),
            "--decisions-dev",
            str(decisions_dev),
            "--golden-holdout",
            str(golden_holdout),
            "--decisions-holdout",
            str(decisions_holdout),
            "--board",
            str(board),
        ]
    )
    assert code == 0
    text = output.read_text(encoding="utf-8")
    assert "| holdout | 1 |" in text
    assert "### holdout" in text


def test_run_uses_injected_graph_runner_without_network(tmp_path: Path) -> None:
    """Exercises the non-skip-graph path with a fake run_invoice_folder, no .env needed."""

    @dataclass(frozen=True)
    class FakeReport:
        processed: int
        output_path: Path

    calls: list[dict] = []

    def fake_graph_runner(invoices_dir, output_path, **kwargs):
        calls.append(
            {"invoices_dir": Path(invoices_dir), "output_path": Path(output_path), **kwargs}
        )
        _write(Path(output_path), _decisions([_record("dev-001", "PAGAR")]))
        return FakeReport(processed=1, output_path=Path(output_path))

    golden_dev = _write(
        tmp_path / "golden_dev.json",
        _golden([{"invoice_id": "dev-001", "expected_decision": "PAGAR", "expected_rules": []}]),
    )
    invoices_dev_dir = tmp_path / "invoices_dev"
    invoices_dev_dir.mkdir()
    catalog = _write(tmp_path / "catalog.json", [])
    board = _write(tmp_path / "board.md", _board_text("PENDIENTE"))
    output = tmp_path / "latest.md"

    code = run_eval.main(
        [
            "--output",
            str(output),
            "--golden-dev",
            str(golden_dev),
            "--invoices-dev",
            str(invoices_dev_dir),
            "--catalog",
            str(catalog),
            "--board",
            str(board),
        ],
        graph_runner=fake_graph_runner,
    )

    assert code == 0
    assert len(calls) == 1
    assert calls[0]["invoices_dir"] == invoices_dev_dir
    assert calls[0]["phase"] == "eval"
    assert output.read_text(encoding="utf-8")


def test_run_skip_graph_requires_decisions_dev(tmp_path: Path) -> None:
    code = run_eval.main(["--output", str(tmp_path / "latest.md"), "--skip-graph"])
    assert code == 2


def test_confirmed_contracts_from_golden_is_per_file_and_fail_closed() -> None:
    golden = {
        "entries": [
            {"contract_path": "data/contracts/a.txt", "contract_confirmed": True},
            {"contract_path": "data/contracts/a.txt", "contract_confirmed": True},
            {"contract_path": "data/contracts/b.txt", "contract_confirmed": True},
            {"contract_path": "data/contracts/b.txt", "contract_confirmed": False},
            {"contract_path": "data/contracts/c.txt"},
            {"contract_path": None, "contract_confirmed": True},
        ]
    }
    assert run_eval.confirmed_contracts_from_golden(golden) == frozenset({"a.txt"})


def test_run_passes_dev_golden_confirmations_to_graph_runner(tmp_path: Path) -> None:
    golden = {
        "schema_version": 1,
        "entries": [
            {"contract_path": "data/contracts/globex-llc.txt", "contract_confirmed": True}
        ],
    }
    golden_path = tmp_path / "dev.json"
    golden_path.write_text(json.dumps(golden), encoding="utf-8")
    seen: dict = {}

    def fake_graph_runner(invoices_dir, output_path, **kwargs):
        seen.update(kwargs)
        raise run_eval.FolderBatchError("stop_here")

    rc = run_eval.run(
        [
            "--output", str(tmp_path / "r.md"),
            "--data-root", str(tmp_path),
            "--golden-dev", str(golden_path),
        ],
        graph_runner=fake_graph_runner,
    )
    assert rc == 2
    assert seen["confirmed_contracts"] == frozenset({"globex-llc.txt"})
