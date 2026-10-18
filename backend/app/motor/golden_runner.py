"""T2.8 — Deterministic motor run over golden extraction (docs/06 §4, G2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.models.domain import Extraction, JevSignal
from app.models.rules_config import RulesConfig, load_rules_config
from app.rules.context import ContractTerms, LedgerEntry, RuleContext
from app.rules.decide import decide
from app.rules.fx import FxTable, load_fx_table
from app.rules.ledger import Ledger, ledger_view_for_invoice, sort_key
from app.rules.run_checks import run_deterministic_checks

_DEFAULT_JEV_IDS = ("J1", "J2", "J3", "J4", "J7")


@dataclass(frozen=True)
class MotorCaseResult:
    invoice_id: str
    expected_decision: str
    actual_decision: str
    expected_rules: tuple[str, ...]
    failed_rules: tuple[str, ...]
    ok: bool
    detail: str | None = None


@dataclass(frozen=True)
class MotorReport:
    split: str
    total: int
    matched: int
    unsafe_pay: int
    failures: tuple[MotorCaseResult, ...]

    @property
    def autonomy_pct(self) -> float:
        if self.total == 0:
            return 100.0
        return 100.0 * self.matched / self.total


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _perfect_jev() -> list[JevSignal]:
    return [
        JevSignal(id=jid, answer=True, probability=0.99)  # type: ignore[arg-type]
        for jid in _DEFAULT_JEV_IDS
    ]


def enrich_ledger_seed(entry: dict) -> list[dict]:
    """Attach invoice department to seed rows when missing (R07 golden seeds)."""
    extraction = entry.get("extraction", {})
    dept = extraction.get("department")
    invoice_beneficiary = extraction.get("beneficiary")
    enriched: list[dict] = []
    for row in entry.get("ledger_seed", []):
        copy = dict(row)
        if (
            copy.get("department") is None
            and dept
            and copy.get("beneficiary") == invoice_beneficiary
        ):
            copy["department"] = dept
        enriched.append(copy)
    return enriched


def doc_text_for_entry(entry: dict, catalog_notes: dict[str, str]) -> str:
    if entry.get("case") == "r13":
        return catalog_notes.get(entry["invoice_id"], "")
    return ""


def build_rule_context(
    entry: dict,
    *,
    rules: RulesConfig,
    fx_table: FxTable,
    ledger: tuple[LedgerEntry, ...],
    catalog_notes: dict[str, str],
) -> RuleContext:
    extraction = Extraction.model_validate(entry["extraction"])
    terms_raw = entry.get("contract_terms")
    terms = ContractTerms.model_validate(terms_raw) if terms_raw else None
    received = datetime.fromisoformat(entry["received_at"].replace("Z", "+00:00"))
    return RuleContext(
        rules=rules,
        fx_table=fx_table,
        extraction=extraction,
        contract_terms=terms,
        contract_confirmed=bool(entry.get("contract_confirmed", False)),
        jev_signals=_perfect_jev(),
        doc_text=doc_text_for_entry(entry, catalog_notes),
        ledger=ledger,
        received_at=received,
        manual_block=bool(entry.get("manual_block", False)),
    )


def _catalog_notes(repo: Path, catalog_path: Path | None = None) -> dict[str, str]:
    path = catalog_path or (repo / "data" / "invoices" / "catalog.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row.get("notes", "") or "" for row in rows}


def _load_golden(repo: Path, split: str) -> list[dict]:
    path = repo / "data" / "golden" / f"{split}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload["entries"])


def _load_f7_rules(path: Path) -> RulesConfig:
    """Tolerant loader for ``data/f7/rules.json`` (T7.6 + T7.1-T7.3).

    That file carries ``approval_policy``/``payment_series``/``variable_pricing``
    together (T7.6 §2), one per T7.x task, but ``RulesConfig`` only accepts
    whichever of those three have actually landed so far (``extra="forbid"``,
    additive per task). Keeping only the keys the *current* ``RulesConfig``
    declares -- instead of failing on the ones that have not landed yet --
    is what lets ``enabled_features`` gate evaluation per feature without
    this split's rules file blocking every other feature in the meantime
    (docs/T7_6_SPEC.md §2). The strict, production loader
    (``app.models.rules_config.load_rules_config``) is untouched and keeps
    rejecting the full file until all three sections land -- see
    ``backend/tests/test_f7_corpus.py::test_f7_rules_json_validates_against_rules_config``.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    known_fields = set(RulesConfig.model_fields)
    filtered = {key: value for key, value in payload.items() if key in known_fields}
    return RulesConfig.model_validate(filtered)


def _load_golden_f7_enabled(repo: Path) -> list[dict]:
    """T7.6 — f7 entries whose ``feature`` is listed in the file's ``enabled_features``.

    Each T7.x task appends its own id once it lands; until then the list is
    empty and no f7 entry is evaluated (``run_motor.py --split f7`` reports
    ``total=0``).
    """
    path = repo / "data" / "golden" / "f7.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    enabled = set(payload.get("enabled_features", []))
    return [entry for entry in payload["entries"] if entry.get("feature") in enabled]


def _case_ok(
    expected_decision: str,
    actual_decision: str,
    expected_rules: list[str],
    failed_rules: list[str],
) -> tuple[bool, str | None]:
    if actual_decision != expected_decision:
        return False, f"decision {actual_decision} != {expected_decision}"
    missing = set(expected_rules) - set(failed_rules)
    if missing:
        return False, f"expected rule failures missing: {sorted(missing)}"
    return True, None


def run_golden_split(
    split: str,
    *,
    repo_root: Path | None = None,
) -> MotorReport:
    """Process golden entries in ledger order; compare decide() to labels.

    ``split="f7"`` (T7.6) is a separate, synthetic-only split: it reads
    ``data/golden/f7.json``, ``data/invoices/f7/catalog.json`` and
    ``data/f7/rules.json`` instead of the dev/holdout paths, and only
    evaluates entries whose ``feature`` is listed in f7's own
    ``enabled_features`` header. With no features enabled yet, this returns a
    trivial ``total=0`` report without touching ``data/f7/rules.json`` at
    all. Once a feature is enabled, ``data/f7/rules.json`` is read with
    ``_load_f7_rules`` (tolerant of the T7.x sections that have not landed
    yet), so T7.1-T7.3 landing their RulesConfig sections one at a time never
    blocks this split from reporting green in the meantime. dev and holdout
    keep reading exactly what they read before T7.6.
    """
    repo = repo_root or _repo_root()
    if split == "f7":
        entries = sorted(
            _load_golden_f7_enabled(repo),
            key=lambda e: sort_key(e["received_at"], e["invoice_id"]),
        )
        if not entries:
            return MotorReport(split="f7", total=0, matched=0, unsafe_pay=0, failures=())
        rules = _load_f7_rules(repo / "data" / "f7" / "rules.json")
        notes = _catalog_notes(repo, repo / "data" / "invoices" / "f7" / "catalog.json")
    else:
        rules = load_rules_config(repo / "data" / "rules.json")
        notes = _catalog_notes(repo)
        entries = sorted(
            _load_golden(repo, split),
            key=lambda e: sort_key(e["received_at"], e["invoice_id"]),
        )
    fx_table = load_fx_table(repo / "data" / "fx.json")

    settled = Ledger.empty()
    results: list[MotorCaseResult] = []
    unsafe_pay = 0

    for entry in entries:
        row = dict(entry)
        row["id"] = entry["invoice_id"]
        row["ledger_seed"] = enrich_ledger_seed(entry)
        ledger_view = ledger_view_for_invoice(row, settled)
        ctx = build_rule_context(
            entry, rules=rules, fx_table=fx_table, ledger=ledger_view, catalog_notes=notes
        )
        checks = run_deterministic_checks(ctx)
        actual = decide(checks)
        failed = [c.rule for c in checks if c.result != "OK"]
        expected_decision = entry["expected_decision"]
        expected_rules = list(entry.get("expected_rules", []))
        ok, detail = _case_ok(expected_decision, actual, expected_rules, failed)
        if actual == "PAGAR" and expected_decision != "PAGAR":
            unsafe_pay += 1
        results.append(
            MotorCaseResult(
                invoice_id=entry["invoice_id"],
                expected_decision=expected_decision,
                actual_decision=actual,
                expected_rules=tuple(expected_rules),
                failed_rules=tuple(failed),
                ok=ok,
                detail=detail,
            )
        )
        if actual == "PAGAR":
            ext = ctx.extraction
            settlement = LedgerEntry(
                beneficiary=ext.beneficiary or "",
                amount_base=float(ext.amount_base or 0.0),
                currency=ext.currency or "USD",
                invoice_number=ext.invoice_number or "",
                received_at=entry["received_at"],
                decision="PAGAR",
                department=ext.department,
            )
            settled = settled.record_settlement(settlement, invoice_id=entry["invoice_id"])

    matched = sum(1 for r in results if r.ok)
    failures = tuple(r for r in results if not r.ok)
    return MotorReport(
        split=split,
        total=len(results),
        matched=matched,
        unsafe_pay=unsafe_pay,
        failures=failures,
    )
