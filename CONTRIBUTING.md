# Contributing

## Setup

Backend (Python 3.11+):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Frontend:

```bash
cd frontend
npm install
```

## Running checks

Backend, from the repository root:

```bash
ruff check .
python -m pytest -q
python eval/run_motor.py
```

Frontend, from `frontend/`:

```bash
npm ci
npm run lint
npx tsc --noEmit
npm test
```

## Commit style

Conventional Commits, prefixed with the roadmap task ID from `docs/TASK_BOARD.md`, for example:

```text
T2.3: implement R02 per-payment limit
```

(`AGENTS.md` §3.) Code, identifiers, and commit messages are written in English; documentation and UI copy are written in Spanish (`AGENTS.md` §3). Commits do not include `Co-Authored-By` or any AI attribution — this is a convention of this repository's human author.

## Spec-per-task workflow

Every non-trivial task on the board has a contract file, `docs/T<phase>_<n>_SPEC.md` (for example `docs/T2_3_SPEC.md`), written before it is implemented. Each contract defines scope, out-of-scope, and acceptance criteria. Start here:

- `docs/TASK_BOARD.md` — current status of every task and gate.
- `docs/05_PHASES_AND_ROADMAP.md` — phases, gates, and roadmap.
- `AGENTS.md` — ownership per folder, conventions, and the discovery protocol for skills.

If you want to contribute a new task, open or request its `docs/T*_SPEC.md` contract first.

## Invariants

Every contribution must keep the invariants in `AGENTS.md` §2 (I1–I9) green — notably that the LLM never decides a payment, that any error or low confidence fails closed into ESCALAR, and that no real money moves. See `AGENTS.md` for the full table; it is not duplicated here.
