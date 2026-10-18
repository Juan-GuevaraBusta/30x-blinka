# Guía para evaluadores — Tachyon (Hackathon 30x · reto Blinka)

> **Estado (T5.5/T5.6, D046/D047).** `T5.1` está **HECHA**
> (`docs/TASK_BOARD.md`). Las cifras de esta guía citan `eval/reports/latest.md`
> (corrida oficial dev + holdout) y `eval/reports/post_t51_dev.md` (rerun de
> dev tras el arreglo de R06/J6, decisión **D068**). El holdout se corrió
> **una sola vez, antes** de ese arreglo. `unsafe_pay = 0` en dev, holdout,
> adversariales y motor. Cualquier afirmación sin evidencia verificable en
> el repo (archivo, prueba o reporte) se borró o quedó marcada «no
> afirmado» (T5.6, ver nota de auditoría al final de `docs/T5_6_SPEC.md`).

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

Solo filas cuya ruta de evidencia existe hoy en el repo y que, abierta en
esta sesión, dice lo que la fila afirma (T5.6).

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
| La identidad del usuario no se verifica contra un JWT en el servidor (límite conocido, sin tarea de cierre programada) | `docs/TASK_BOARD.md` fila T9.8 (HECHA, D067): «Identidad sigue sin verificar el JWT (límite conocido)»; `docs/T9_8_SPEC.md` §5 |
| El LLM extractor es `openai/gpt-4o-mini`, el verificador `anthropic/claude-sonnet-5` y el JEV `typesafe/jev-router` (dev y holdout) | `eval/reports/latest.md`, sección «Versiones» |
| El grafo es conservador: en la corrida oficial, 0/11 facturas esperadas en PAGAR llegan a PAGAR (las 11 escalan); tras D068 sube a 2/11, con 6 de las 9 restantes escaladas por J6 bajo umbral y 3 por PNG sin OCR | `eval/reports/latest.md` (matriz esperado × obtenido, dev); `eval/reports/post_t51_dev.md`; `docs/DECISIONS_LOG.md` D068 |
| Dev oficial (T5.1): n=34, `unsafe_pay=0`, autonomía 55.9 % (19/34) | `eval/reports/latest.md` |
| Dev tras el arreglo de R06/J6 (D068): `unsafe_pay=0`, autonomía 61.8 % (PAGAR 2/11) | `eval/reports/post_t51_dev.md`; `docs/DECISIONS_LOG.md` D068 |
| Holdout (T5.1): n=10, `unsafe_pay=0`, autonomía 30.0 % — corrida única, **antes** del arreglo D068; no se repitió | `eval/reports/latest.md`; `docs/DECISIONS_LOG.md` D068 |
| Adversariales: 8/8 casos no-PAGAR, `unsafe_pay=0` | `eval/reports/adversarial.md` |
| Motor determinista (extracción verdadera, sin LLM): dev 34/34, f7 16/16, `unsafe_pay=0` | `eval/reports/metrics_summary.json` |
| Hay una condición de carrera en el límite de periodo del ledger hasta T5.8 | `docs/TASK_BOARD.md` fila T5.8 (HECHA, D055) — mitigada con lock de proceso de un solo worker; ver limitación de worker único |
| Exposición registrada del holdout al motor (no es la corrida e2e de T5.1) | `docs/DECISIONS_LOG.md` D064 |

### Métricas (fuente: `eval/reports/latest.md` y `eval/reports/post_t51_dev.md`)

| Split | n | `unsafe_pay` | Autonomía | `over_escalation` | `reason_accuracy` | `explain_ok` |
|---|---|---|---|---|---|---|
| dev (oficial, `latest.md`) | 34 | 0 | 55.9 % (19/34) | 100.0 % | 14.7 % | 100.0 % |
| dev (tras D068, `post_t51_dev.md`) | 34 | 0 | 61.8 % (PAGAR 2/11) | 81.8 % | 47.1 % | 100.0 % |
| holdout (`latest.md`, única, antes de D068) | 10 | 0 | 30.0 % | 100.0 % | 10.0 % | 100.0 % |

| Celda | Texto |
|---|---|
| Adversariales (`unsafe_pay`) | 0; 8/8 no-PAGAR — `eval/reports/adversarial.md` |
| `blind_read` | pendiente T5.4 |
| `latency_p50`, `cost_per_invoice` | pendiente T5.1: no está en `eval/reports/latest.md` |

## 4. Cómo reproducir las métricas

El resultado oficial, ya comprometido en el repo, es `eval/reports/latest.md`
(dev + holdout, corrido una sola vez) y `eval/reports/post_t51_dev.md`
(rerun de solo-dev tras D068). No se vuelve a correr el holdout: su cifra
oficial sigue siendo la de antes del arreglo.

```bash
python -m pytest -q
python eval/run_motor.py --split dev
python eval/run_motor.py --split f7
python eval/run_eval.py --output /tmp/latest-dev-check.md
```

El último comando reproduce solo la corrida de **dev** (sin `--include-holdout`)
en un archivo temporal, para no sobrescribir el reporte oficial del repo.

## 5. Limitaciones conocidas

- Un solo worker: el lock que serializa decisiones del ledger es de
  proceso, no distribuido (`backend/app/api/app.py`).
- `X-User-Id` no se verifica contra un JWT del lado del servidor (límite
  conocido, sin tarea de cierre programada; `docs/TASK_BOARD.md` fila T9.8,
  HECHA, D067).
- Nota sobre exposición del holdout al motor, sin usarla para calibrar
  (`docs/DECISIONS_LOG.md` D064).
- La corrida e2e del holdout (T5.1, `eval/reports/latest.md`) se hizo una
  sola vez, antes del arreglo de R06/J6 (D068); no se repitió, así que su
  autonomía (30.0 %) es anterior a ese arreglo.
- El grafo es conservador: la mayoría de las facturas esperadas en PAGAR
  escalan, sobre todo por la señal JEV J6 bajo umbral o por facturas en
  imagen PNG sin OCR (`eval/reports/post_t51_dev.md`, D068).
- `latency_p50` y `cost_per_invoice` no están en ningún reporte comprometido
  hoy; no se afirman.
