# Spec T7.3 — Pagos variables: fórmula pactada y recálculo determinista

Dueño: **Rules Engine** (recálculo y regla R19 en `backend/app/rules/`). Carril: B. Colabora: **Agent Graph** (extracción de líneas medidas en `backend/app/extraction/` y estado del grafo), **Spec & Data** (modelo nuevo en `backend/app/models/`). Skill de dominio: `langgraph-fundamentals` solo si se toca el grafo; proceso: `test-driven-development`, `python-testing-patterns` PARCIAL.

Prioridad: **P1**. Depende de: T7.6 (casos variables en f7). Puede ir después de T7.1/T7.2.

Estado: contrato para la sesión que **implemente** T7.3. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D059** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Lecturas:

- `AGENTS.md` §2 (I2, I3, I7) y `docs/02_ARCHITECTURE.md` (nodos `extract`, `contract_lookup`, `det_checks`).
- `backend/app/models/domain.py` (`LineItem`, `Extraction`: congelados, D013; no se les añaden campos).
- `backend/app/extraction/extract.py` (prompt y validación de `source_spans` literales) y `backend/app/extraction/contracts.py` (`_validate_quotes`).
- `backend/app/rules/checks.py` `check_r06` y `backend/app/rules/context.py` (`ContractTerms`, `RuleContext`).
- `docs/T7_1_SPEC.md` §2 y `docs/T7_2_SPEC.md` §2 (patrón de sección opcional y `RuleCode` aditivo).

## 1. Qué es T7.3

Muchos proveedores cobran montos variables: horas × tarifa, unidades por tramos, comisión porcentual, con tope. Hoy R06 compara el monto con una tarifa fija. T7.3 guarda la fórmula como términos estructurados, deja que el LLM **solo extraiga** cantidades y tarifas con su cita literal (I7), y recalcula el monto esperado en código. Un cobro por encima de la fórmula se frena o escala.

## 2. Esquema y extracción

Sección nueva opcional en `RulesConfig`: `variable_pricing: list[PricingTerms] = []`.

```json
"variable_pricing": [
  {"beneficiary": "Andesbyte SAS", "currency": "USD", "contract_clause": "4.2",
   "formula": {"kind": "unit_rate", "unit": "hora", "rate": 50, "cap": 6000},
   "tolerance": {"abs": 1.0}},
  {"beneficiary": "Pampaluz Ltda", "currency": "USD", "contract_clause": "4.3",
   "formula": {"kind": "tiered", "unit": "unidad",
               "tiers": [{"up_to": 100, "rate": 10}, {"up_to": null, "rate": 8}]}},
  {"beneficiary": "Rioseco Servicios SAS", "currency": "USD", "contract_clause": "4.4",
   "formula": {"kind": "commission", "pct": 5, "base_label": "ventas"}}
]
```

- `kind`: `unit_rate` (cantidad × tarifa), `tiered` (tramos marginales), `commission` (porcentaje sobre una base declarada en la factura). `cap` opcional en cualquiera.
- Modelo nuevo `MeteredLine` en `backend/app/models/metered.py`: `quantity`, `unit`, `unit_rate | None`, `base_amount | None`, `line_amount | None`, `source_span` (texto literal). No va dentro de `Extraction` (congelado): viaja en el estado del grafo como `metered_lines` y entra a `RuleContext` como campo opcional.
- El extractor pide esas líneas solo si el beneficiario tiene `variable_pricing`. Cada número debe tener `source_span` que aparezca literalmente en el texto normalizado (misma validación que hoy); si una cita no aparece o una cantidad no se puede leer → R19 `INDETERMINADO`.
- `OnFail` gana `R19="FRENAR"` opcional; `RuleCode` suma `R19` (D059).

## 3. Regla R19 «Cuadra con la fórmula pactada»

- `expected_amount(terms, lines)` es función pura (sin LLM, sin red), con el mismo tipo numérico que el resto del motor (`Decimal` si T5.11 ya aterrizó). `tiered` aplica tramos marginales; `cap` limita el total.
- Falla si `monto_base_factura > esperado + tolerancia` (sobrecobro) → `on_fail` R19 (FRENAR por defecto). Monto **menor** que el esperado → `OK` con nota en `detail`. Unidad distinta a la pactada o moneda distinta → `INDETERMINADO`.
- `detail` y `evidence` explican el cálculo: «120 hora × USD 50 = USD 6.000; la factura cobra USD 6.500 (cláusula 4.2).»; `evidence.quote` = la cita literal de la cantidad.
- **R06 no cambia.** Si el contrato del proveedor variable tiene tarifa fija distinta del monto, R06 sigue escalando: R19 nunca convierte esa escalada en PAGAR. Relajar R06 para proveedores variables queda fuera y exigiría una decisión nueva explícita. En la práctica, la factura variable correcta queda en ESCALAR con el cálculo ya hecho para quien aprueba; la sobrefacturada queda en FRENAR.
- Sin `variable_pricing` para el beneficiario, R19 **no se emite**; motor dev 34/34, `unsafe_pay=0`.

## 4. Fuera de alcance

- Que el LLM calcule, compare o decida montos (I2).
- Leer la fórmula del texto del contrato con LLM (se declara como dato; la cláusula se cita).
- Impuestos, descuentos por pronto pago, multimoneda dentro de una misma factura.
- Cambiar R01–R13, `Extraction`, `LineItem` o `DecisionRecord`.

## 5. Criterios de aceptación

1. `backend/tests/rules/test_variable_pricing.py`: `unit_rate`, `tiered` (borde exacto de tramo), `commission`, `cap`; tolerancia; unidad distinta → `INDETERMINADO`.
2. Test de extracción con fake del LLM: cita que no aparece en el texto → R19 `INDETERMINADO`; documento con «ignora las reglas» dentro de una línea sigue tratado como dato (I7, R13 intacto).
3. Casos f7 (T7.6): variable correcto → R19 OK (decisión según el resto de reglas, nunca PAGAR por R19); variable sobrefacturado → FRENAR (R19).
4. Property test (semilla fija, ≥ 500 casos): añadir `variable_pricing` nunca baja la severidad de `decide()`.
5. Motor dev 34/34, `unsafe_pay=0`; `pytest -q` 0 failed; `ruff check .` ok.
6. Tablero T7.3 → HECHA con evidencia; fila en `docs/AI_USAGE_LOG.md`; commit y push con el §6.

## 6. Commit

```text
T7.3: variable pricing terms with deterministic recomputation (R19)
```

## 7. Mensaje para la sesión que implementa

```text
Implementa T7.3 según docs/T7_3_SPEC.md. Decisión D059.
Sección opcional variable_pricing (unit_rate, tiered, commission, cap,
tolerancia) y regla R19: el LLM solo extrae cantidades/tarifas con cita
literal (MeteredLine, fuera de Extraction, que está congelado); el monto
esperado se recalcula en código puro. Sobrecobro → FRENAR; cita ausente o
unidad distinta → INDETERMINADO. R06 no cambia y R19 nunca habilita un
PAGAR. Sin configuración, R19 no se emite: motor dev 34/34, unsafe_pay=0.
Property test de severidad obligatorio. Al terminar: pytest, ruff,
run_motor dev y f7, tablero y AI_USAGE_LOG. Commit y push:
T7.3: variable pricing terms with deterministic recomputation (R19)
```
