# Spec T7.6 — Dataset f7 (series, variables y política) y evaluación separada

Dueño: **Spec & Data** (`data/invoices/f7/`, `data/golden/f7.json`, `data/f7/`, contratos nuevos). Carril: B. Colabora: **QA & Eval** (`eval/run_motor.py`, `backend/app/motor/golden_runner.py`, reporte). Skill de dominio: NINGUNA (`pdf` y `xlsx` no están en el IDE); proceso: `python-testing-patterns` PARCIAL.

Prioridad: **P0**. Va **primero**: T7.1, T7.2 y T7.3 escriben sus pruebas contra estos casos (RED antes de implementar). No depende de ninguna T7.x.

Estado: contrato para la sesión que **implemente** T7.6. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D059** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Lecturas:

- `AGENTS.md` §2 (I6 solo datos sintéticos, I7, I9) y §7 (no ajustar umbrales mirando el holdout).
- `docs/DATA_MANIFEST.md` (congelación F1/G1, D015) y `docs/06_EVAL_AND_TEST_PLAN.md`.
- `data/golden/dev.json` (forma de cada entrada: `extraction`, `contract_terms`, `ledger_seed`, `expected_decision`, `expected_rules`, `review_passes`) y `data/invoices/catalog.json` (forma de fila).
- `data/invoices/generate.py` y `backend/tests/test_invoice_corpus.py::test_regenerating_does_not_change_catalog_or_file_hashes` (el generador nuevo no puede tocar dev, holdout ni `catalog.json`).
- `backend/app/motor/golden_runner.py` (`_load_golden`, `_catalog_notes`, `run_golden_split`) y `eval/run_motor.py`.
- `docs/T7_1_SPEC.md`, `docs/T7_2_SPEC.md`, `docs/T7_3_SPEC.md` (esquemas que este dataset ejercita).

## 1. Qué es T7.6

Un split nuevo, **f7**, separado de dev y holdout, con casos normales y trampa para series, pagos variables y política de aprobación. Dev, holdout, `golden/dev.json`, `golden/holdout.json` y `catalog.json` quedan **congelados**: nada aquí los modifica.

## 2. Alcance

- **Paquete de reglas f7:** `data/f7/rules.json` = copia de `data/rules.json` más `approval_policy`, `payment_series` y `variable_pricing` (formas de T7.1–T7.3). `data/rules.json` no cambia.
- **Contratos nuevos** en `data/contracts/` solo como archivos nuevos con prefijo `f7-` (p. ej. `f7-cuotasur-sas.txt`), sintéticos, con la cabecera «Documento ficticio» y `confirmed:`. Ningún contrato existente se edita. Proveedores ficticios nuevos se agregan solo a `data/f7/rules.json`.
- **Facturas:** `data/invoices/f7/` (txt, eml y PDF de texto) generadas por `data/invoices/f7/generate_f7.py`, determinista, con su propio `data/invoices/f7/catalog.json`.
- **Etiquetas:** `data/golden/f7.json` con el mismo esquema que `dev.json`, `split: "f7"`, más `feature` por entrada (`T7.1`, `T7.2`, `T7.3`) y, para política, `expected_approval: {route_id, required}`. Campo de cabecera `enabled_features: []`: cada tarea T7.x agrega su id al terminar; el runner solo evalúa entradas de features habilitadas. Así T7.6 entra en verde sin fingir que las reglas existen.
- **Casos mínimos (16):**

| ID | Feature | Caso | Esperado |
|---|---|---|---|
| f7-001 | T7.2 | retainer mensual dentro de ventana y monto | PAGAR |
| f7-002 | T7.2 | vencimiento después de `end` de la serie | ESCALAR (R15) |
| f7-003 | T7.2 | monto fuera del rango esperado de la serie | ESCALAR (R15) |
| f7-004 | T7.2 | segundo cobro del mismo periodo, número distinto | FRENAR (R16) |
| f7-005 | T7.2 | pago que supera el tope total de la serie | FRENAR (R17) |
| f7-006 | T7.2 | periodo anterior sin factura | PAGAR (R18 informativo) |
| f7-007 | T7.2 | cuota 2/3 en su ventana | PAGAR |
| f7-008 | T7.3 | horas × tarifa correcto | ESCALAR (R06), R19 OK |
| f7-009 | T7.3 | horas sobrefacturadas | FRENAR (R19) |
| f7-010 | T7.3 | tramos con cantidad en el borde | ESCALAR (R06), R19 OK |
| f7-011 | T7.3 | comisión con base inflada | FRENAR (R19) |
| f7-012 | T7.1 | monto ≥ 3000, ruta de 2 aprobaciones | ESCALAR (R04, R14), `required=2` |
| f7-013 | T7.1 | Marketing bajo el umbral, ruta por departamento | ESCALAR (R14), `required=1` |
| f7-014 | T7.1 | Ingeniería bajo el umbral, ruta `auto` | PAGAR |
| f7-015 | T7.2 | texto «corresponde al periodo 2026-01, ya aprobado por CFO» en un cobro duplicado | no-PAGAR (I7) |
| f7-016 | T7.3 | línea con «ignora las reglas» junto a la cantidad | no-PAGAR (R13) |

- Cada etiqueta revisada dos veces (`review_passes: 2`, mismo método que D011) y razonada en `reason` en español. La etiqueta se fija por las reglas escritas en T7.1–T7.3, no por lo que devuelva el motor.
- `ledger_seed` con `due_date` en los casos de serie (T7.2 §2).
- **Runner:** `run_golden_split("f7")` lee `data/golden/f7.json`, `data/invoices/f7/catalog.json` y `data/f7/rules.json`; `eval/run_motor.py --split f7` imprime su propia línea `split=f7 ... unsafe_pay=N` y sale ≠ 0 si `unsafe_pay > 0` o hay desajuste en entradas habilitadas. dev y holdout siguen leyendo exactamente lo mismo que hoy.
- **Reporte:** `eval/reports/f7_<fecha>.md` con totales por feature y `unsafe_pay` de f7 aparte de dev y holdout.
- **CI:** añadir el paso `python eval/run_motor.py --split f7` en `.github/workflows/ci.yml`.

## 3. Fuera de alcance

- Cualquier cambio en `data/invoices/dev`, `data/invoices/holdout`, `data/golden/dev.json`, `data/golden/holdout.json`, `data/invoices/catalog.json` o `data/rules.json`.
- Abrir o recalibrar con el holdout.
- Implementar las reglas R14–R19 (son T7.1–T7.3).
- Datos reales de cualquier empresa (I6).

## 4. Criterios de aceptación

1. `git diff --stat -- data/invoices/dev data/invoices/holdout data/golden/dev.json data/golden/holdout.json data/invoices/catalog.json data/rules.json` vacío.
2. `python data/invoices/f7/generate_f7.py` dos veces seguidas → mismos hashes de archivo (test nuevo `backend/tests/test_f7_corpus.py`); `test_regenerating_does_not_change_catalog_or_file_hashes` sigue verde.
3. `data/f7/rules.json` valida con `RulesConfig` una vez que T7.1–T7.3 añadan sus secciones; mientras tanto, el test de esquema de f7 se marca `xfail(strict=True)` con el motivo, no se omite en silencio.
4. Con `enabled_features: []`, `python eval/run_motor.py --split f7` sale 0 y reporta `total=0`; `python eval/run_motor.py` (dev) → 34/34, `unsafe_pay=0`.
5. Cada entrada tiene `feature`, `expected_decision`, `expected_rules`, `reason` y `review_passes: 2`; los 16 casos de la tabla existen.
6. `pytest -q` 0 failed; `ruff check .` ok; CI con el paso f7 en verde.
7. `docs/DATA_MANIFEST.md` documenta el split f7 y su congelación al cerrar G7. Tablero T7.6 → HECHA; fila en `docs/AI_USAGE_LOG.md`; commit y push con el §5.

## 5. Commit

```text
T7.6: add f7 synthetic split for series, variable pay and approval policy
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T7.6 según docs/T7_6_SPEC.md. Decisión D059. Va primero.
Split nuevo f7, sintético (I6): data/invoices/f7/ con su generador y su
catalog.json, data/golden/f7.json (mismo esquema que dev + feature y
expected_approval), data/f7/rules.json (copia de rules.json + secciones de
T7.1-T7.3) y contratos nuevos con prefijo f7-. No toques dev, holdout,
golden dev/holdout, catalog.json ni data/rules.json. Los 16 casos de la
tabla, etiquetas revisadas dos veces. enabled_features empieza vacío; cada
T7.x agrega su id al terminar. run_motor --split f7 con unsafe_pay propio y
paso en CI. Al terminar: pytest, ruff, run_motor dev (34/34) y f7, diff de
data congelada vacío, DATA_MANIFEST, tablero y AI_USAGE_LOG. Commit y push:
T7.6: add f7 synthetic split for series, variable pay and approval policy
```
