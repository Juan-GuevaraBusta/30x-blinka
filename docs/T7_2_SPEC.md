# Spec T7.2 — Pagos en serie por proveedor (calendario pactado)

Dueño: **Rules Engine** (`backend/app/rules/`, reglas R15–R18). Carril: B. Colabora: **Spec & Data** (esquema en `backend/app/models/rules_config.py`, `LedgerEntry.due_date`). Skill de dominio: NINGUNA; proceso: `test-driven-development`, `python-testing-patterns` PARCIAL.

Prioridad: **P0**. Depende de: T7.6 (casos de serie en f7). En paralelo con T7.1.

Estado: contrato para la sesión que **implemente** T7.2. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D059** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Lecturas:

- `AGENTS.md` §2 (I1, I3, I4) y `docs/04_RULES_AND_DECISION_SPEC.md` §3–§4 (periodo, duplicados, ledger).
- `backend/app/rules/context.py` (`LedgerEntry`, `RuleContext`), `backend/app/rules/ledger.py`, `backend/app/rules/ledger_queries.py` (`COUNTED_DECISIONS`, `duplicate_match`).
- `backend/app/rules/checks.py` (`check_r03`, `check_r05`, `CHECKS`).
- `backend/app/models/rules_config.py` y `backend/app/models/domain.py` (`RuleCode`).
- `data/contracts/globex-llc.txt` (vigencia, periodicidad y tope ya escritos en texto).
- `docs/T7_1_SPEC.md` §2 (mismo patrón: sección opcional, regla no emitida sin configuración).

## 1. Qué es T7.2

Los clientes de Blinka pagan a muchos proveedores en serie: retainers mensuales, cuotas, hitos. Con cada proveedor nuevo crece el riesgo de pagar fuera del calendario, pagar dos veces el mismo periodo o pasarse del total pactado. T7.2 declara cada serie como dato estructurado y añade reglas deterministas basadas en el ledger que **solo suben severidad**.

## 2. Esquema (opcional, con default seguro)

Sección nueva opcional en `RulesConfig`: `payment_series: list[PaymentSeries] = []`.

```json
"payment_series": [
  {"id": "globex-retainer", "beneficiary": "Globex LLC", "department": "Ingenieria",
   "periodicity": "monthly", "currency": "USD",
   "expected_amount": {"min": 800, "max": 800},
   "start": "2026-01-01", "end": "2026-12-31", "total_cap": 9600},
  {"id": "norteclaro-cuotas", "beneficiary": "Norteclaro SpA", "periodicity": "installments",
   "currency": "USD", "total_cap": 3000,
   "items": [{"key": "1/3", "due_from": "2026-02-01", "due_to": "2026-02-28", "amount": 1000},
             {"key": "2/3", "due_from": "2026-03-01", "due_to": "2026-03-31", "amount": 1000}]}
]
```

- `periodicity`: `monthly`, `biweekly`, `quarterly` (calendario) o `installments`, `milestones` (lista explícita `items`).
- Clave de periodo, función pura `period_key(series, due_date)`: `monthly` = `YYYY-MM`; `quarterly` = `YYYY-Qn`; `biweekly` = índice del bloque de 14 días contado desde `start`; `installments`/`milestones` = `key` del único ítem cuyo `[due_from, due_to]` contiene la fecha.
- Se usa `due_date` de la extracción (R11 ya garantiza que existe; si falta, las reglas de serie dan `INDETERMINADO`).
- Una factura pertenece a una serie si coincide el beneficiario normalizado y, si la serie lo fija, el departamento. Más de una serie coincidente → `INDETERMINADO` (ESCALAR).
- `LedgerEntry` gana `due_date: str | None = None` (aditivo). Fila del ledger de esa serie sin `due_date` → R16 `INDETERMINADO`.
- `OnFail` gana campos opcionales con default: `R15="ESCALAR"`, `R16="FRENAR"`, `R17="FRENAR"`. `RuleCode` suma `R15`–`R18` de forma aditiva (D059).

**Default:** sin `payment_series`, o factura de un proveedor sin serie, R15–R18 **no se emiten**. `data/rules.json` sigue válido; motor dev 34/34, `unsafe_pay=0`.

## 3. Reglas nuevas

| Código | Nombre | Falla si… | Default |
|---|---|---|---|
| R15 | Dentro de la serie pactada | `due_date` fuera de `[start, end]`, sin ítem que la contenga, o monto base fuera de `expected_amount` / del `amount` del ítem | ESCALAR |
| R16 | Periodo ya pagado | el ledger (`COUNTED_DECISIONS`) ya tiene un pago de esa serie con la misma clave de periodo y otro número de factura | FRENAR |
| R17 | Total de la serie | suma pagada de la serie + monto > `total_cap` | FRENAR |
| R18 | Periodo esperado sin factura (informativo) | — siempre `OK`; el `detail` lista periodos anteriores sin pago | — |

- R18 nunca cambia la decisión; solo informa («Falta la factura de 2026-02 de Globex LLC.»).
- Mismo número de factura ya pagado sigue siendo R05 exacto; R16 cubre el caso de número distinto en el mismo periodo.
- Plantillas nuevas en `backend/app/records/templates.py`, en español y citando serie y periodo: «Frenada: el periodo {periodo} de la serie {serie} ya se pagó con la factura {numero} (regla R16).»

## 4. Fuera de alcance

- Generar facturas o pagos programados automáticamente; recordatorios al proveedor.
- Extraer el calendario desde el texto del contrato con LLM (la serie se declara como dato).
- Reservar saldo de periodos futuros; prorrateos.
- Cambiar R01–R13, `decide()` o `DecisionRecord`. Tocar dev/holdout/golden congelados o `catalog.json`.

## 5. Criterios de aceptación

1. `backend/tests/rules/test_payment_series.py`: `period_key` para las cinco periodicidades, incluidos bordes de mes, trimestre y bloque de 14 días; ítem ambiguo → `INDETERMINADO`.
2. Casos f7 (T7.6): pago dentro de la ventana → PAGAR; fuera de ventana → ESCALAR (R15); periodo duplicado → FRENAR (R16); tope total excedido → FRENAR (R17); periodo saltado → R18 informativo sin cambiar la decisión.
3. Property test (semilla fija, ≥ 500 casos): añadir cualquier `payment_series` válida nunca baja la severidad de `decide()` respecto a la misma factura sin series.
4. Sin series, los chequeos de los 34 casos dev son idénticos a los actuales; `python eval/run_motor.py` → 34/34, `unsafe_pay=0`.
5. `cd backend && python -m pytest -q` 0 failed; `python -m ruff check .` ok.
6. `docs/TASK_BOARD.md` T7.2 → HECHA con evidencia; fila en `docs/AI_USAGE_LOG.md`; commit y push con el §6.

## 6. Commit

```text
T7.2: payment series per vendor with ledger-based rules R15-R18
```

## 7. Mensaje para la sesión que implementa

```text
Implementa T7.2 según docs/T7_2_SPEC.md. Decisión D059.
Añade la sección opcional payment_series (monthly, biweekly, quarterly,
installments, milestones; monto esperado o rango; inicio/fin; tope total)
y las reglas R15 (fuera de la serie, ESCALAR), R16 (periodo ya pagado,
FRENAR), R17 (tope total, FRENAR) y R18 (periodo saltado, informativo,
siempre OK). Clave de periodo pura desde due_date; LedgerEntry gana
due_date opcional. Sin series, R15-R18 no se emiten y el motor sigue
34/34, unsafe_pay=0 en dev. Solo pueden subir severidad: property test
obligatorio. Tests primero. Al terminar: pytest, ruff, run_motor dev y f7,
tablero y AI_USAGE_LOG. Commit y push:
T7.2: payment series per vendor with ledger-based rules R15-R18
```
