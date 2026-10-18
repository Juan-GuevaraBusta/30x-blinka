#!/usr/bin/env python3
"""Official eval command (T5.1 / T5.1.3, docs/T5_1_SPEC.md §5, §6).

Runs the graph on the dev split (or reuses already-generated decisions JSON
with ``--skip-graph``), scores it with ``app.gate.eval_score``, and writes
the report skeleton. The holdout split (``data/invoices/holdout`` and
``data/golden/holdout.json``) is only opened when ``--include-holdout`` is
passed *and* column 7 (Estado) of the T5.2 row in ``docs/TASK_BOARD.md``
reads HECHA or HECHO (spec §5.1); otherwise this refuses with exit code 2
before touching either holdout path. There is no flag that skips that board
read: if the board is wrong, T5.2 fixes the board, not this script.

``eval/run_invoices.py`` keeps writing the decisions JSON only; this is the
one command that scores and writes ``eval/reports/latest.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.gate.eval_score import (
    EvalCase,
    render_report_markdown,
    rules_with_zero_cases,
    score_split,
)
from app.graph.folder_batch import (
    RULES_VERSION,
    FolderBatchError,
    repo_root_from_module,
)

GraphRunner = Callable[..., Any]


class HoldoutLockedError(Exception):
    """Raised when the holdout split is requested but T5.2 is not closed."""

    def __init__(self, estado: str | None) -> None:
        self.estado = estado
        super().__init__(f"holdout locked: T5.2 Estado column={estado!r}")


def board_t5_2_estado(board_text: str) -> str | None:
    """Return column 7 (Estado) of the T5.2 row, or None if the row is absent.

    Reads only that one column -- never the whole row -- so a mention of
    "HECHA"/"HECHO" in the Evidencia or Notas columns can't false-positive
    the gate (docs/T5_1_SPEC.md §5).
    """
    for line in board_text.splitlines():
        if not line.strip().startswith("|"):
            continue
        columns = [cell.strip() for cell in line.split("|")]
        if len(columns) < 8:
            continue
        if columns[1] == "T5.2":
            return columns[7]
    return None


def check_holdout_gate(board_path: Path) -> None:
    """Raise HoldoutLockedError unless T5.2's Estado column is HECHA/HECHO."""
    text = board_path.read_text(encoding="utf-8")
    estado = board_t5_2_estado(text)
    if estado not in ("HECHA", "HECHO"):
        raise HoldoutLockedError(estado)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _records_by_invoice_id(decisions_payload: dict) -> dict[str, dict]:
    return {record["invoice_id"]: record for record in decisions_payload.get("records", [])}


def build_cases(golden_payload: dict, decisions_payload: dict) -> list[EvalCase]:
    """Join golden entries (expected_decision/expected_rules) with obtained records."""
    records = _records_by_invoice_id(decisions_payload)
    return [
        EvalCase(
            invoice_id=entry["invoice_id"],
            expected_decision=entry["expected_decision"],
            expected_rules=tuple(entry.get("expected_rules", [])),
            record=records.get(entry["invoice_id"]),
        )
        for entry in golden_payload["entries"]
    ]


def confirmed_contracts_from_golden(golden_payload: dict) -> frozenset[str]:
    """Contract file names the dev golden records as human-confirmed.

    D015 keeps ``confirmed: false`` in the frozen ``data/contracts/*.txt``; the
    human confirmation lives in the golden's ``contract_confirmed``. It is a
    per-contract fact, so a contract counts only if every entry citing it says
    ``true`` (fail-closed on any disagreement). Only the contract file name is
    passed to the graph: terms are still read from the text and quoted.
    """
    seen: dict[str, bool] = {}
    for entry in golden_payload.get("entries", []):
        path = entry.get("contract_path")
        if not path:
            continue
        name = Path(path).name
        seen[name] = seen.get(name, True) and entry.get("contract_confirmed") is True
    return frozenset(name for name, ok in seen.items() if ok)


def _versions_tuples(decisions_payload: dict) -> list[tuple[str, str, str, str]]:
    tuples: list[tuple[str, str, str, str]] = []
    for record in decisions_payload.get("records", []):
        versions = record.get("versions") or {}
        tuples.append(
            (
                versions.get("rules_version", ""),
                versions.get("model_extractor", ""),
                versions.get("model_verifier", ""),
                versions.get("jev", ""),
            )
        )
    return tuples


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (root / path).resolve()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run dev (and, once T5.2 is closed, holdout) through the graph or "
            "through already-generated decisions JSON, score both with "
            "app.gate.eval_score, and write the report."
        ),
    )
    parser.add_argument("--output", required=True, help="Report markdown path.")
    parser.add_argument("--data-root", default=None, help="Repo root (default: auto-detect).")
    parser.add_argument(
        "--board", default="docs/TASK_BOARD.md", help="Board path for the T5.2 gate."
    )
    parser.add_argument("--catalog", default="data/invoices/catalog.json")
    parser.add_argument("--invoices-dev", default="data/invoices/dev")
    parser.add_argument("--invoices-holdout", default="data/invoices/holdout")
    parser.add_argument("--golden-dev", default="data/golden/dev.json")
    parser.add_argument("--golden-holdout", default="data/golden/holdout.json")
    parser.add_argument("--phase", default="eval", choices=("dev", "eval", "demo"))
    parser.add_argument(
        "--include-holdout",
        action="store_true",
        help=(
            "Also score the holdout split. Still refused with exit code 2 "
            "unless T5.2's Estado column reads HECHA/HECHO (spec §5.1)."
        ),
    )
    parser.add_argument(
        "--skip-graph",
        action="store_true",
        help="Reuse already-generated decisions JSON instead of calling run_invoice_folder.",
    )
    parser.add_argument("--decisions-dev", default=None, help="Pre-generated dev decisions JSON.")
    parser.add_argument(
        "--decisions-holdout", default=None, help="Pre-generated holdout decisions JSON."
    )
    return parser


def _run_split(
    *,
    split: str,
    invoices_dir: Path,
    catalog_path: Path,
    root: Path,
    phase: str,
    output_path: Path,
    graph_runner: GraphRunner,
    confirmed_contracts: frozenset[str] = frozenset(),
) -> dict:
    tmp_decisions = output_path.parent / f"{output_path.stem}.{split}.decisions.json"
    from app.config import load_settings
    from app.graph.tracing import make_langsmith_session

    settings = load_settings()
    tracer = make_langsmith_session(settings)
    report = graph_runner(
        invoices_dir,
        tmp_decisions,
        repo_root=root,
        catalog_path=catalog_path,
        phase=phase,
        settings=settings,
        tracer=tracer,
        confirmed_contracts=confirmed_contracts,
    )
    return _load_json(Path(report.output_path))


def run(argv: list[str] | None = None, *, graph_runner: GraphRunner | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.skip_graph and not args.decisions_dev:
        print("error: --skip-graph requires --decisions-dev", file=sys.stderr)
        return 2

    root = Path(args.data_root).resolve() if args.data_root else repo_root_from_module()
    board_path = _resolve(root, args.board)
    output_path = _resolve(root, args.output)

    if args.include_holdout:
        try:
            check_holdout_gate(board_path)
        except HoldoutLockedError as exc:
            print(
                "error: holdout locked. docs/TASK_BOARD.md T5.2 Estado column "
                f"(7th) is {exc.estado!r}, not HECHA/HECHO. No se abrió "
                "data/golden/holdout.json ni data/invoices/holdout/.",
                file=sys.stderr,
            )
            return 2
        if args.skip_graph and not args.decisions_holdout:
            print(
                "error: --include-holdout --skip-graph requires --decisions-holdout",
                file=sys.stderr,
            )
            return 2

    try:
        golden_dev = _load_json(_resolve(root, args.golden_dev))
        # Contract confirmations come from the dev golden only, for both splits:
        # the holdout golden is never read before scoring.
        confirmed_contracts = confirmed_contracts_from_golden(golden_dev)
        if args.skip_graph:
            decisions_dev = _load_json(_resolve(root, args.decisions_dev))
        else:
            decisions_dev = _run_split(
                split="dev",
                invoices_dir=_resolve(root, args.invoices_dev),
                catalog_path=_resolve(root, args.catalog),
                root=root,
                phase=args.phase,
                output_path=output_path,
                graph_runner=graph_runner or _default_graph_runner(),
                confirmed_contracts=confirmed_contracts,
            )

        holdout_score = None
        holdout_missing_rules: list[str] = []
        decisions_holdout: dict | None = None
        if args.include_holdout:
            golden_holdout = _load_json(_resolve(root, args.golden_holdout))
            if args.skip_graph:
                decisions_holdout = _load_json(_resolve(root, args.decisions_holdout))
            else:
                decisions_holdout = _run_split(
                    split="holdout",
                    invoices_dir=_resolve(root, args.invoices_holdout),
                    catalog_path=_resolve(root, args.catalog),
                    root=root,
                    phase=args.phase,
                    output_path=output_path,
                    graph_runner=graph_runner or _default_graph_runner(),
                    confirmed_contracts=confirmed_contracts,
                )
            holdout_cases = build_cases(golden_holdout, decisions_holdout)
            holdout_score = score_split(holdout_cases, "holdout")
            holdout_missing_rules = rules_with_zero_cases(golden_holdout["entries"])
    except FolderBatchError as exc:
        print(f"error: {exc.code} {exc.detail}".strip(), file=sys.stderr)
        return 2

    dev_cases = build_cases(golden_dev, decisions_dev)
    dev_score = score_split(dev_cases, "dev")

    versions_by_split = {"dev": _versions_tuples(decisions_dev)}
    if decisions_holdout is not None:
        versions_by_split["holdout"] = _versions_tuples(decisions_holdout)

    markdown = render_report_markdown(
        dev=dev_score,
        holdout=holdout_score,
        generated_at=datetime.now(tz=UTC).date().isoformat(),
        schema_version=golden_dev.get("schema_version", "no consta"),
        rules_version=RULES_VERSION,
        holdout_missing_rules=holdout_missing_rules,
        versions_by_split=versions_by_split,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"wrote {output_path} dev.n={dev_score.n} dev.unsafe_pay={dev_score.unsafe_pay}")
    if holdout_score is not None:
        print(f"holdout.n={holdout_score.n} holdout.unsafe_pay={holdout_score.unsafe_pay}")

    unsafe_total = dev_score.unsafe_pay + (holdout_score.unsafe_pay if holdout_score else 0)
    return 1 if unsafe_total > 0 else 0


def _default_graph_runner() -> GraphRunner:
    from app.graph.folder_batch import run_invoice_folder

    return run_invoice_folder


def main(argv: list[str] | None = None, *, graph_runner: GraphRunner | None = None) -> int:
    return run(argv, graph_runner=graph_runner)


if __name__ == "__main__":
    sys.exit(main())
