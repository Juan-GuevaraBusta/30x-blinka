# Spec G2 — Cierre del motor determinista

Dueño del gate: **Orquestador**. Dueños del código: **QA & Eval** (T2.7, T2.8) y **Rules Engine** (T2.1–T2.6). Skill: `verification-before-completion` (TOTAL). Dominio: **NINGUNA** extra (`docs/SKILLS_MAP.md` G2). No usar `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **ejecute** G2. Este archivo no cierra el gate.

Decisión que fija este contrato: **D028**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, **antes** de afirmar éxito:

- `AGENTS.md` (I1–I9; I2: `decide()` pura; I6 secretos)
- `docs/05_PHASES_AND_ROADMAP.md` F2 y G2
- `docs/06_EVAL_AND_TEST_PLAN.md` métricas y pirámide §4 (motor aislado)
- `docs/DECISIONS_LOG.md` D005, D015, D016, D028
- `docs/DATA_MANIFEST.md` (34 dev; caso verificador **fuera** de G2)
- `docs/TASK_BOARD.md` T2.7, T2.8, G2
- `backend/app/motor/golden_runner.py`, `eval/run_motor.py`
- `backend/tests/eval/test_motor_dev.py`
- `backend/tests/gate/test_invariants.py`, `backend/tests/gate/test_final_gate.py`

cwd: raíz del repo. venv: `.venv`. `PYTHONPATH` lo pone `pyproject.toml` (`backend`).

**Sin red.** No `source .env`. No LLM, no JEV, no LangSmith. El runner usa extracción dorada y señales JEV sintéticas perfectas (`_perfect_jev()`).

Prohibido: pegar claves, commitear `.env`, consultar `data/golden/holdout.json` para calibrar, correr `eval/run_invoices.py`.

## 1. Qué es G2

Gate de F2 (`docs/05`): con **extracción verdadera**, el motor acierta el 100 % del set **dev**; `unsafe_pay = 0`; invariantes I1–I4 con prueba verde.

| Vía | Qué prueba | Éxito |
|---|---|---|
| Motor | `python eval/run_motor.py` (split default `dev`) | `total=34 matched=34 autonomy=100.0% unsafe_pay=0` y exit 0 |
| Pytest motor | `python -m pytest -q backend/tests/eval/test_motor_dev.py` | 0 failed |
| Invariantes I1–I4 | `python -m pytest -q backend/tests/gate/test_invariants.py backend/tests/gate/test_final_gate.py` | 0 failed |
| Regresión | `python -m pytest -q` y `python -m ruff check .` | 0 failed; ruff All checks passed |

Código de producto **ya existe** (T2.1–T2.8 HECHO). Esta sesión **corre** comandos frescos y **documenta**. No reescribe reglas para “pasar” el gate.

G2 **no** exige e2e, OCR, API HTTP, UI ni `unsafe_pay` del grafo. Eso es G3 / G4 / G5.

## 2. Fuera de alcance

- Cerrar G3, G4, G5, G6.
- `eval/run_invoices.py` sobre `data/invoices/dev` (G3).
- `python eval/run_motor.py --split holdout` (T5.1 / G5). El holdout no se usa para calibrar (`docs/06`).
- `eval/run_eval.py` (no existe; T5.1).
- Calibrar umbrales JEV (T5.2).
- Editar `data/golden/*`, `data/rules.json`, `data/invoices/` salvo pedido explícito del Orquestador + Spec & Data.
- Editar `backend/app/rules/`, `gate/`, `motor/` para maquillar un fallo. Si el motor no da 34/34: **parar**, anotar, dejar G2 PENDIENTE.
- Llamadas de red, sockets en tests nuevos, LangSmith, OpenCode, JEV.
- Frontend, T4.1, OCR, deploy.
- El caso D005 (violación solo por verificador): vive en adversariales; **no** entra en el 100 % de G2 (`docs/DATA_MANIFEST.md`).

## 3. Archivos

Crear (esta sesión de spec, Orquestador):

- `docs/G2_SPEC.md` (este archivo)

Crear (sesión que ejecuta): **nada de código nuevo**. No hace falta `eval/reports/` aquí (G3/G5).

Modificar al **cerrar** el gate (sesión que ejecuta):

- `docs/DECISIONS_LOG.md` — fila de cierre G2 (**D028** si no hubo parche; **D030** si se tocó producto, solo tras aprobación)
- `docs/TASK_BOARD.md` — **G2 HECHA** con evidencia (comandos + cifras); T2.7 y T2.8 siguen HECHO
- `docs/AI_USAGE_LOG.md` — una fila
- `docs/05_PHASES_AND_ROADMAP.md` — casillas T2.1–T2.8 y nota G2 cerrado (opcional, alineado a G1/D015)
- `docs/OPEN_QUESTIONS_STATUS.md` — una línea: G2 cerrado; G3 sigue PENDIENTE. No reabrir Q6.

Si el motor o los invariantes fallan: mismos archivos, frase **G2 no cerrado**, tablero G2 PENDIENTE.

## 4. Invariantes

- I1. Nunca PAGAR si algún chequeo falla o está indeterminado: cubierto por `test_invariants.py` + `test_final_gate.py` + motor (`unsafe_pay`).
- I2. El LLM no decide. El runner llama `run_deterministic_checks` → `decide(checks)`. Verificar en código si se duda; no hace falta AST nuevo si `test_i2_gate_modules_forbid_llm_and_rules_imports` y `test_gate_with_decide` pasan.
- I3. Fail-closed del **grafo** es T3.10 / G3. G2 no lo reabre. Correr `pytest -q` entero está bien (incluye `test_fail_closed.py`); **no** marcar G3.
- I4. El verificador solo sube severidad: `test_apply_verifier_floor_*` y `test_proposed_frenar_not_lowered_by_verifier`.
- I6. Solo datos sintéticos. No pegar facturas reales.
- I8. Cero dinero. `PAGAR` del motor es etiqueta + ledger simulado.
- I9. `unsafe_pay > 0` impide cerrar G2 (y más adelante el deploy). Aquí el número sale de `MotorReport.unsafe_pay`: PAGAR cuando `expected_decision != PAGAR`.

## 5. Entorno mínimo

No hace falta `.env`. No hay claves.

| Variable | G2 |
|---|---|
| `LLM_*`, `JEV_*`, `LANGSMITH_*` | no usar |
| venv `.venv` | sí |
| Python 3.11+ | sí (`pyproject.toml`) |

## 6. Procedimiento (exacto)

### 6.1 Activar venv

```bash
. .venv/bin/activate
```

No `source .env`.

### 6.2 Motor (evidencia principal)

```bash
python eval/run_motor.py
```

Éxito (línea exacta de forma; números fijos):

```text
split=dev total=34 matched=34 autonomy=100.0% unsafe_pay=0
```

Exit code 0. Si hay líneas `FAIL …`, G2 no cierra.

No pasar `--split holdout`.

### 6.3 Pytest del motor

```bash
python -m pytest -q backend/tests/eval/test_motor_dev.py
```

Éxito: 0 failed. El archivo exige `total == 34`, `matched == total`, `unsafe_pay == 0`.

### 6.4 Invariantes I1–I4

```bash
python -m pytest -q backend/tests/gate/test_invariants.py backend/tests/gate/test_final_gate.py
```

Éxito: 0 failed. Incluye property tests Hypothesis (I1, I4) e integración `decide()` + `final_gate`.

### 6.5 Suite y linter

```bash
python -m pytest -q
python -m ruff check .
```

Éxito: pytest 0 failed (anotar el conteo real, p. ej. `N passed`); ruff `All checks passed`.

Si pytest trae skipped: anotar el número; no bloquea G2 si 0 failed.

### 6.6 Qué anotar (plantilla, sin secretos)

En `docs/DECISIONS_LOG.md`, una fila:

- Fecha/hora local UTC-5
- ID: cierre G2 (**D028**)
- `run_motor.py`: `total/matched/unsafe_pay` copiados de stdout
- pytest: conteo `passed` (y `skipped` si hay)
- ruff: ok / fail
- Frase: “G2 cerrado” o “G2 no cerrado: falta X”
- G3 sigue PENDIENTE

## 7. Qué no afirmar

- Que el grafo e2e acierta 34/34 (G3).
- Que T3.10 (fakes) equivale a G2.
- Autonomía o `unsafe_pay` con extractor LLM.
- Que el holdout está evaluado.
- Que Q6 (Render) quedó resuelta.
- 100 % “porque T2.8 ya estaba HECHO” sin **correr de nuevo** 6.2–6.5 en esta sesión (`verification-before-completion`).

## 8. Criterios de aceptación (cerrar G2)

1. 6.2: `matched=34`, `unsafe_pay=0`, exit 0.
2. 6.3: `test_motor_dev.py` 0 failed.
3. 6.4: invariantes 0 failed.
4. 6.5: `pytest -q` 0 failed y `ruff check .` ok.
5. Cero secretos en git (`git diff` no incluye `.env`).
6. T2.7 y T2.8 siguen HECHO (no reabrir).
7. Fila G2 en el tablero: HECHA; evidencia = fila de `DECISIONS_LOG` + este spec + stdout del runner.
8. G3 (y G4–G6) siguen PENDIENTE.
9. No se tocó `data/golden/holdout.json` ni se corrió el split holdout.
10. No se tocó producto **salvo** bug real aprobado (entonces D030 + pytest/ruff otra vez).
11. Commit y push: `G2: motor golden 34/34; gate closed` **solo** si 1–9 se cumplen. Si falla: `G2: motor gate blocked; gate stays open` y **no** marcar HECHA.

## 9. Subtareas

- G2.1 Correr 6.2. Pegar la línea `split=dev …` en la nota (sin otros dumps).
- G2.2 Correr 6.3 y 6.4. Anotar passed/failed.
- G2.3 Correr 6.5.
- G2.4 Si alguno falla: parar. No editar golden ni umbrales. Documentar y commit de fallo.
- G2.5 Si todo verde: escribir `DECISIONS_LOG`, tablero, `AI_USAGE_LOG` (y opcional `docs/05`).
- G2.6 `git status` limpio de secretos. Commit + push según §8.11.

## 10. Mensaje para la sesión que ejecuta

```text
Ejecuta G2 según docs/G2_SPEC.md.
Skill: verification-before-completion.
Sin red. Sin source .env. Sin holdout. Sin run_invoices.py.
Corre eval/run_motor.py, pytest del motor, pytest de gate I1–I4,
pytest -q y ruff. Cifras frescas en esta sesión.
No cierres G3. No edites golden ni rules si falla: anota y deja G2 abierto.
Al terminar: commit y push con el mensaje de la sección 8.11.
```
