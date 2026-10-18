# Guía para evaluadores — Agente pagador de facturas (Hackathon Blinka)

> **Borrador de estructura (T5.5, D046).** `T5.1` (`docs/TASK_BOARD.md`)
> sigue **PENDIENTE**. Por `docs/T5_5_SPEC.md` §0, mientras eso sea así esta
> guía solo trae el esqueleto y las filas sin cifras: ninguna cifra de
> autonomía, `unsafe_pay`, montos o conteo de chequeos se escribe aquí
> todavía. Cualquier afirmación sin evidencia verificable en el repo
> (archivo, prueba o reporte) se borra, no se deja como promesa. Esta tarea
> no se marca hecha en el tablero.

## 1. Cómo ejecutar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

Frontend: `cd frontend && npm ci && npm test`. Demo pública: ver tabla de
URLs en `README.md` → «Despliegue público».

## 2. Qué hace y qué NO hace

Ver `README.md` → «Qué es», «El problema» y «Qué NO hace». Resumen: decide
PAGAR / FRENAR / ESCALAR sobre una factura mediante chequeos deterministas;
el LLM nunca decide el pago; no mueve dinero real, no hace OCR sobre
imágenes y no tiene integración con un buzón de correo real.

## 3. Afirmación → evidencia

Solo filas cuya ruta de evidencia existe hoy en el repo. Sin cifras
(`unsafe_pay`, autonomía, montos, conteos) mientras T5.1 esté PENDIENTE.

| Afirmación | Dónde verificarla |
|---|---|
| El LLM no decide el pago; `decide()` es función pura de los chequeos | `backend/app/rules/decide.py`; `backend/tests/rules/test_decide.py` (`test_i2_decide_module_has_no_llm_imports`) |
| No hay PAGAR si algún chequeo falla o está indeterminado | `AGENTS.md` I1; `backend/app/gate/final_gate.py`; `backend/tests/gate/test_invariants.py`; `backend/tests/rules/test_decide.py` |
| Error, timeout, JSON inválido o verificador JEV caído termina en ESCALAR | `AGENTS.md` I3; `backend/app/gate/final_gate.py`; `backend/tests/gate/test_fail_closed.py` |
| El verificador solo sube severidad (PAGAR < ESCALAR < FRENAR) | `AGENTS.md` I4; `backend/tests/gate/test_invariants.py` (`test_apply_verifier_floor_does_not_lower_frenar`) |
| La explicación sale de plantillas, no de texto libre del modelo | `docs/04_RULES_AND_DECISION_SPEC.md` §6; `backend/app/records/templates.py`; `backend/tests/rules/test_record_templates.py` |
| «PAGAR» es un registro y un pago simulado, no dinero real | `AGENTS.md` I8; `backend/app/records/build.py` (`build_next_step` devuelve «Pago simulado registrado.») |
| Solo datos sintéticos; la empresa de ejemplo es Acme Demo Inc. | `AGENTS.md` I6; `data/company.json` |
| R13 detecta una lista fija de frases; no cubre otros idiomas ni variantes | `AGENTS.md` I7; `backend/app/rules/checks.py` (`R13_PHRASES`); `backend/tests/rules/test_rules_r01_r13.py` (`test_r13_fail_injection_dev031`) |
| Batería de escenarios de fraude y duplicados | `backend/tests/fraud/test_fraud_scenarios.py` |
| Suite adversarial | `backend/tests/adversarial/test_adversarial.py` |
| Serialización de decisiones dependientes del ledger (condición de carrera) | `backend/app/api/app.py` (`_decide_and_store_invoice`); `backend/tests/api/test_invoice_concurrency.py` |
| Cadena de registros con hash, verificable | `backend/app/records/chain.py`; `GET /decisions/verify-chain` |
| CI corre las pruebas en cada cambio | `.github/workflows/ci.yml` |
| `unsafe_pay > 0` hace fallar el CI (no bloquea el deploy de Render, que no espera al CI) | `AGENTS.md` I9; `.github/workflows/ci.yml` (paso `eval/run_motor.py`, sale ≠ 0 si `unsafe_pay > 0`). El número de holdout no se rellena aquí |
| No hay OCR sobre facturas en imagen (falla cerrado) | `backend/app/extraction/ingest.py` (canal `image` → `illegible`); `backend/tests/test_ingest.py` |
| Flujo del grafo | `docs/02_ARCHITECTURE.md`, heading `## Flujo (LangGraph)` |
| Diagrama de componentes | `docs/diagrams/architecture.md` |
| Reglas configurables | `data/rules.json`; `frontend/app/reglas/` |
| Hay ficha de decisión en la UI | `frontend/app/decisiones/[id]/` |
| Demo en URL pública (G4) | URLs en `README.md` → «Despliegue público»; fila G4 de `docs/TASK_BOARD.md`. G5 no está cerrado |
| La API no exige autenticación de usuario en endpoints mutantes hasta T9.6.0 | `docs/TASK_BOARD.md` fila T9.6 (PENDIENTE, D062) |
| Hay una condición de carrera en el límite de periodo del ledger hasta T5.8 | `docs/TASK_BOARD.md` fila T5.8 (HECHA, D055) — mitigada con lock de proceso de un solo worker; ver limitación de worker único |
| Exposición registrada del holdout al motor (no es la corrida e2e de T5.1) | `docs/DECISIONS_LOG.md` D064 |

### Métricas (todas pendientes de `eval/reports/latest.md`, T5.1)

| Celda | Texto |
|---|---|
| Holdout (`unsafe_pay`, autonomía) | pendiente T5.1 |
| Adversariales (`unsafe_pay`) | pendiente T5.3 |
| `over_escalation`, `reason_accuracy`, `explain_ok`, `blind_read` | pendiente T5.1 o T5.4 |
| `latency_p50`, `cost_per_invoice` | pendiente T5.1 |

## 4. Cómo reproducir las métricas

`eval/reports/latest.md` todavía no existe (T5.1 PENDIENTE), así que esta
guía no manda ejecutar `eval/run_eval.py` todavía. Lo único reproducible
hoy sin tocar el holdout:

```bash
python -m pytest -q
```

## 5. Limitaciones conocidas

- Un solo worker: el lock que serializa decisiones del ledger es de
  proceso, no distribuido (`backend/app/api/app.py`).
- `X-User-Id` no se verifica del lado del servidor hasta T9.6.0
  (`docs/TASK_BOARD.md` fila T9.6).
- Nota sobre exposición del holdout al motor, sin usarla para calibrar
  (`docs/DECISIONS_LOG.md` D064).
- Esta guía es un borrador de estructura: no completa cifras de evaluación
  mientras T5.1 esté PENDIENTE (`docs/T5_5_SPEC.md`).
