# Spec de scaffold — T0.1

Dueño: Orquestador. Skill: NINGUNA. Alcance: solo estructura y configuración mínima. **No se escribe código de negocio** (ni reglas, ni `decide()`, ni modelos de dominio, ni datos de facturas).

Estado: contrato para el agente que implemente T0.1. Se puede pegar tal cual en el mensaje del siguiente agente.

## 1. Árbol obligatorio (lo que T0.1 debe dejar creado)

Rutas `backend/app/*` y `backend/tests/*` son paquetes/directorios Python vacíos. Rutas `data/*`, `frontend/` y `eval/*` son contenedores vacíos. En directorios vacíos que Git no trackea se pone `.gitkeep`; en paquetes Python vacíos, un `__init__.py` vacío.

```
.env.example                     # T0.1 — ver §3
.gitignore                       # T0.1 — ver §5
pyproject.toml                   # T0.1 — ver §4 (ruff + pytest + python 3.11)
AGENTS.md                        # ya existe
README.md                        # ya existe
docs/                            # ya existe; no tocar salvo los logs de T0.1
backend/
  app/
    __init__.py                  # vacío
    api/                         # T4.x — API
    graph/                       # T3.7 — Agent Graph
    extraction/                  # T3.3 — Agent Graph
    jev/                         # T3.5 — Agent Graph
    verifier/                    # T3.6 — Agent Graph
    rules/                       # T2.x — Rules Engine
    records/                     # T2.6 — Rules Engine
    models/                      # T1.3 — Spec & Data
    # config.py NO se crea en T0.1: es de Agent Graph (T3.1), dueño único.
  tests/
    rules/                       # T2.x — Rules Engine
    api/                         # T4.x — API
    gate/                        # T2.7/T3.10 — QA & Eval
    adversarial/                 # T5.3 — QA & Eval
data/                            # Spec & Data; T0.1 solo crea los contenedores
  contracts/                     # T1.4
  invoices/
    dev/                         # T1.6
    holdout/                     # T1.6
  golden/                        # T1.7 (dev.json, holdout.json)
  # company.json (T1.1), rules.json (T1.2), fx.json (T1.5) los crea Spec & Data
frontend/                        # T4.x — Frontend; T0.1 solo deja el contenedor con .gitkeep
eval/                            # QA & Eval
  reports/                       # T5.1 — QA & Eval
  # run_eval.py NO se crea en T0.1: es de QA & Eval (T2.8/T5.1)
```

Resolución de ambigüedad de `AGENTS.md §8`: el mapa dice `data/ ... golden.json`, pero T1.7 y `docs/TASK_BOARD.md` usan `data/golden/dev.json` + `data/golden/holdout.json`. **Manda la carpeta `data/golden/`** (dos archivos: dev y holdout separados). Idem `data/invoices/` se parte en `dev/` y `holdout/`.

## 2. No-objetivos de T0.1 (fuera de alcance)

- No crear `backend/app/config.py` (dueño Agent Graph, T3.1).
- No crear `data/company.json`, `rules.json`, `fx.json` ni facturas (Spec & Data, T1.x).
- No inicializar Next.js dentro de `frontend/` (Frontend, T4.x). Solo el contenedor.
- No crear `eval/run_eval.py` ni `eval/reports/*` (QA & Eval).
- No añadir frameworks extra: solo pydantic v2 como dependencia mínima de runtime; pytest/ruff/hypothesis como dev (ver §4).
- No subir `.env` real ni secretos (I6, AGENTS.md §3).

## 3. `.env.example` (solo nombres, valores vacíos o placeholders)

Contenido mínimo: 8 nombres, sin valores reales. El nombre del modelo/extractor
(`OPENCODE_API_KEY`) es marcador hasta que Agent Graph fije `get_llm` en T3.1.

```bash
# Nunca commitear `.env` real (ver `.gitignore` §5 e I6).
# LangSmith (docs/07) — confirmadas
LANGSMITH_TRACING=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=
LANGSMITH_ENDPOINT=
# Modelos vía API (T0.3/T3.1 define nombres finales; marcador, no contrato)
OPENCODE_API_KEY=
# JEV (vía API directa D010; formato exacto se comprueba en T0.3)
JEV_API_KEY=
JEV_BASE_URL=
# Persistencia (SQLite dev / Postgres prod; la URL real solo vive en `.env` local)
DATABASE_URL=
```

## 4. `pyproject.toml` (mínimo)

- `[project]`: `name = "blinka-invoice-agent"`, `requires-python = ">=3.11"`, dependencia runtime única `pydantic>=2`. Dev: `pytest`, `ruff`, `hypothesis`.
- `[tool.ruff]`: `target-version = "py311"`, `line-length = 100`, `src = ["backend/app", "backend/tests", "eval"]`.
- `[tool.ruff.lint]`: `select = ["E", "F", "I", "UP", "B", "SIM"]`.
- `[tool.pytest.ini_options]`: `testpaths = ["backend/tests"]`, `pythonpath = ["backend"]` (para que `import app` funcione desde tests y `eval/`).
- Sin dependencias de FastAPI/LangGraph todavía: llegan con T3.x/T4.x y las añade su dueño.

## 5. `.gitignore` (mínimo)

Ignorar: `.env`, `.venv/`, `venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `build/`, `*.egg-info/`, `node_modules/`, `.next/`, `.DS_Store`.

No ignorar: `data/` (facturas sintéticas y golden son parte del repo, I6), `eval/reports/`, ni `.env.example`.

## 7. Handoff: AC de T0.1 + subtareas T0.1.1–T0.1.9

AC (los 8 criterios que cierran T0.1):

1. Existe el árbol de §1 (`find` lo confirma; vacíos trackeados con `.gitkeep`/`__init__.py`).
2. `pyproject.toml` único en raíz con ruff + pytest + python `>=3.11` (sin doble config).
3. `python -m pytest` arranca y el test de T0.1.2 (`backend/tests/test_repo_scaffold.py`)
   falla si falta una carpeta clave.
4. `python -m ruff check .` corre sin error de configuración.
5. `.env.example` existe con los 8 nombres de §3, valores vacíos/placeholder, sin secretos.
6. `git check-ignore .env` responde (el `.env` real nunca se commitea).
7. Sin código de negocio (ni reglas, ni `decide()`, ni modelos, ni FastAPI/Next.js, ni facturas).
8. Commit + push (D011) y `docs/TASK_BOARD.md` marca T0.1 HECHA con evidencia.

Subtareas listas para despachar (en orden):

- T0.1.1: crear el árbol de §1 con `.gitkeep` en vacíos y `__init__.py` vacío en paquetes.
- T0.1.2: test de scaffold (AI-TDD: falla si falta carpeta clave; luego implementa).
- T0.1.3: `pyproject.toml` mínimo en raíz (§4).
- T0.1.4: `.env.example` con los 8 nombres de §3.
- T0.1.5: `.gitignore` mínimo (§5).
- T0.1.6: `JUDGE_GUIDE.md` placeholder (el contenido real llega en T5.5).
- T0.1.7: verificar pytest + ruff + `git check-ignore .env`.
- T0.1.8: marcar T0.1 HECHA en `docs/TASK_BOARD.md` con evidencia.
- T0.1.9: commit + push `T0.1: scaffold repo structure, ruff, pytest, .env.example`.
