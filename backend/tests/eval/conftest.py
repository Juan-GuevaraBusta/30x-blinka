"""Makes eval/run_eval.py importable as a top-level module in tests.

``eval/`` is a CLI scripts folder, not a package (same pattern as
``eval/run_motor.py`` / ``eval/run_invoices.py``). Adding it to ``sys.path``
lets tests do ``import run_eval`` instead of shelling out, so wiring can be
exercised with injected fakes/doubles (T5.1.3) without a subprocess.
"""

from __future__ import annotations

import sys
from pathlib import Path

_EVAL_DIR = Path(__file__).resolve().parents[3] / "eval"
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
