# Spec T9.7 — Prioridades de negocio, conflictos entre pagos y excepciones permitidas

Dueño: **Rules Engine** (regla R22, resolución de prioridad y composición de excepciones en `backend/app/rules/`) y **Frontend** (orden de la cola en `/aprobaciones`, tarjeta «Conflictos detectados» en `/`, editor en `/reglas`). Carril: B. Colabora: **Spec & Data** (esquema en `backend/app/models/rules_config.py`, `RuleCode`, split sintético `f9_7`), **API** (obligaciones pendientes por dueño, campos de prioridad en el listado), **QA & Eval** (property test, `--split f9_7` en `eval/run_motor.py`). Skill de dominio: NINGUNA; proceso: `test-driven-development`, `python-testing-patterns` PARCIAL, `frontend-design` PARCIAL.

Prioridad: **P0** (historia de la demo: «el sistema detecta conflictos entre pagos»). Depende de: **T9.1** (series compiladas desde acuerdos confirmados), **T7.1** (rutas R14) y **T7.2** (series R15–R18). Coordina con T9.6 (la sección nueva vive en la configuración de cada dueño) y T5.13 (R21, `amount_base` real en el ledger).

Estado: contrato para la sesión que **implemente** T9.7. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D065** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Lecturas:

- `AGENTS.md` §2 (I1, I2, I3, I4, I5) y `docs/04_RULES_AND_DECISION_SPEC.md` (severidad `PAGAR < ESCALAR < FRENAR`).
- `backend/app/models/rules_config.py` (`OnFail`, `RouteMatch`, `RouteRequire`, `ApprovalPolicy`, `PaymentSeries`, `RulesConfig`) y `backend/app/models/domain.py` (`RuleCode`, `InvoiceType`, `SEVERITY`).
- `backend/app/rules/checks.py` (`check_r03`, `check_r07`, `check_r14`, `check_r16`, `check_r21`), `backend/app/rules/run_checks.py`, `backend/app/rules/context.py` (`RuleContext`, `LedgerEntry`).
- `backend/app/rules/ledger_queries.py` (`period_paid_total`, `department_spent_for_budget`, `COUNTED_DECISIONS`) y `backend/app/rules/payment_series.py` (`period_key`, `paid_entries_for_series`, `resolve_item_key`).
- `docs/T7_1_SPEC.md` §2–§4, `docs/T7_2_SPEC.md` §2–§3, `docs/T9_1_SPEC.md` §4, `docs/T9_6_SPEC.md` §2 y §4, `docs/T5_13_SPEC.md` §1 (huecos 1, 3 y 5).
- `frontend/app/aprobaciones/AprobacionesScreen.tsx` y `frontend/app/OverviewScreen.tsx`.

## 1. Qué es T9.7

Reparto de responsabilidades (cofundador de Blinka): **el cliente configura** políticas de pago y límites autorizados, aprobadores, **prioridades y restricciones del negocio** y excepciones permitidas; **el sistema** analiza facturas, identifica quién debe aprobar cada operación, **detecta conflictos entre pagos** y pide intervención humana cuando hace falta.

T9.7 añade el criterio de prioridad. Un conflicto existe cuando pagar la factura actual deja el saldo del periodo sin espacio para un pago **ya comprometido y de mayor prioridad** (la nómina tercerizada del día 28, la cuota del proveedor crítico). El sistema no elige entre pagos: escala y explica cuál pago protege y por qué.

**Regla dura (D065):** prioridades y excepciones solo afectan **orden, enrutamiento y escalamiento**. `decide()` sigue siendo función pura de `check_results`; ninguna prioridad ni excepción convierte un no-PAGAR en PAGAR, baja un `on_fail` ni quita aprobaciones.

## 2. Esquema (opcional, con default seguro)

Dos secciones nuevas opcionales en `RulesConfig` (y en `WorkspaceRules` de T9.6), ambas `extra=forbid`:

```json
"business_priorities": {
  "default": "normal",
  "by_vendor": {"Nominex SAS": "critico", "Globex LLC": "alto"},
  "by_category": {"honorarios": "alto", "suscripción": "bajo"},
  "reserves": [
    {"id": "reserva-nomina", "amount": 6000, "protects_from": "normal",
     "reason": "Nómina tercerizada del día 28"}
  ]
},
"allowed_exceptions": [
  {"id": "globex-sobre-limite", "match": {"beneficiary": "Globex LLC", "amount_base_gte": 5000},
   "effect": {"route_to_groups": ["cfo"]},
   "reason": "Contrato marco aprobado por el CFO", "created_by": "cfo@demo.test"}
]
```

- `Priority = Literal["critico", "alto", "normal", "bajo"]`, orden `critico > alto > normal > bajo`.
- Resolución pura `resolve_priority(bp, beneficiary, invoice_type) -> Priority`: `by_vendor` (clave `normalize_beneficiary`) gana sobre `by_category` (valores de `InvoiceType`), y esta sobre `default`. Beneficiario ausente o ilegible → **`bajo`** (supuesto conservador: con menos prioridad, más pagos ajenos quedan protegidos y R22 escala antes).
- `reserves[]` (opcional): `id` único, `amount > 0` en moneda base, `protects_from: Priority`, `reason` no vacío. Significa: una factura con prioridad **igual o menor** que `protects_from` no puede dejar el saldo del periodo por debajo de `amount`. Una reserva nunca autoriza gastar: solo protege.
- Validadores: claves no vacías y únicas tras normalizar; `by_category` solo con valores de `InvoiceType`.
- `OnFail` gana `R22: FailAction = "ESCALAR"`. `RuleCode` suma `"R22"` de forma aditiva (patrón D059). `DecisionRecord` no cambia.

**Default:** sin `business_priorities`, R22 **no se emite**; sin `allowed_exceptions`, R14 se comporta exactamente como en T7.1. `data/rules.json`, `data/f7/rules.json`, goldens y `catalog.json` no se tocan: motor dev 34/34 y f7 16/16, `unsafe_pay=0`, con listas de chequeos idénticas byte a byte.

## 3. Regla R22 «Conflicto de prioridad»

`check_r22(ctx) -> CheckResult | None`, pura, emitida solo si `business_priorities` existe.

**Pagos protegidos** del periodo (mes calendario de `received_at`, la misma base que R03), con prioridad **estrictamente mayor** que la de la factura actual:

1. **Pagos esperados de series confirmadas** (`payment_series`, escritas a mano o compiladas desde acuerdos T9.1): por cada serie cuyo periodo cae en el mes y que **no** tiene pago contado para esa clave de periodo (misma consulta que R16). Monto = `expected_amount.max` (calendario) o `items[].amount` (cuotas/hitos). Fecha = `due_to` del ítem, o el último día del periodo dentro del mes. Prioridad = la de su beneficiario. Se excluye la serie y periodo de la factura actual (la factura **es** ese pago).
2. **Facturas pendientes en ESCALAR** del mismo dueño, sin `aprobada_humano` ni `rechazada_humano`, con `due_date` en el mes (o sin fecha: cuentan, fail-closed). Llegan por un campo nuevo `RuleContext.pending_obligations: tuple[PendingObligation, ...] = ()` (`invoice_id`, `beneficiary`, `invoice_type`, `department`, `amount_base | None`, `due_date | None`). Lo arma el llamador: el API desde las decisiones guardadas del dueño (T5.13 hueco 5: todo lo guardado ya se procesó); el motor dorado desde `pending_seed` de la fila del catálogo. Se excluye la propia factura por `invoice_id` (reprocesos).
3. **Reservas** con `protects_from` ≥ prioridad de la factura: cuentan como un pago protegido de `amount`, nombrado por `id` y `reason`.

**Cálculo** (todo en `amount_base`):

- `saldo_periodo = limits.per_period.amount − period_paid_total(mes) − monto_actual`.
- Si la factura tiene departamento con presupuesto: `saldo_depto = presupuesto − department_spent_for_budget − monto_actual`, comparado solo contra los protegidos del mismo departamento.
- **FALLA** si `saldo_periodo < Σ protegidos` o `saldo_depto < Σ protegidos del depto`. `on_fail = on_fail.R22` (ESCALAR).
- **OK** si no hay protegidos de mayor prioridad, o si alcanzan los saldos. Si R03/R07 ya fallan por la factura sola → OK con «El límite ya lo cubre R03/R07.» (mismo patrón que R21 con R04; evita doble explicación).
- **INDETERMINADO** (ESCALAR, I3): `amount_base` o `received_at` ausentes, un acumulado del ledger con monto no convertible (T5.13), un protegido sin `amount_base`, o una serie protegida en moneda distinta de la base.

**Explicación** (`detail`, español, nombra el pago protegido y la fecha; I5): «Pagar esta factura (prioridad normal) deja USD 1.200 del límite del mes; no alcanza para la cuota "2/3" de Nominex SAS (prioridad crítica) prevista para 2026-03-31 por USD 4.000.» Con varios protegidos se nombra el de mayor prioridad y fecha más próxima, más «y N pagos más». `evidence.clause` = id de serie, `pending:<invoice_id>` o id de reserva; `evidence.quote` = `protected=<monto>;priority=<p>;date=<fecha>`. Plantilla en `backend/app/records/templates.py`: «Escalada: pagar esta factura comprometería {pago} de prioridad {p} del {fecha} (regla R22).»

R22 solo sube severidad. Nunca reserva, pospone ni programa un pago, ni cambia el estado de la factura protegida.

## 4. Excepciones permitidas y composición con R14

Cada excepción: `id` único, `match` (mismos campos que `RouteMatch`, **no vacío**: una excepción global no existe), `effect`, `reason`, `created_by` ∈ aprobadores. Se evalúan **en orden; gana la primera que coincide** (como las rutas). Requiere `approval_policy` (validador: excepciones sin política → error de esquema).

`effect` admite solo:

- `add_groups: list[str]` — suma grupos a los de la ruta.
- `route_to_groups: list[str]` — **redirige**: sustituye los grupos de la ruta (p. ej. «Globex sobre el límite → directo al CFO»).
- `min_approvals: int ≥ 1` (opcional) — solo puede **subir** el requisito.

**Decisión D065 sobre reducir aprobaciones:** una excepción **nunca** reduce `min_approvals` por debajo del de la ruta base (ni de N a 1), nunca cambia `approvals` a `auto` y nunca toca otro chequeo ni su `on_fail`. Motivo: una reducción de firmas es exactamente un permiso para pagar con menos control, y la edición de `rules` es mutable (T5.9); si el cliente quiere menos firmas para un caso, edita la ruta base, que queda versionada y visible como política, no como excepción escondida.

**Composición** con la ruta resuelta por `resolve_route` (pura, `apply_exception(route, exceptions, extraction, amount_base)`):

- `min_efectivo = max(min_ruta, effect.min_approvals or 0, 1)` (`min_ruta = 0` si la ruta es `auto`: una excepción sobre ruta `auto` la vuelve `approvals` con al menos 1).
- `grupos_efectivos = route_to_groups` si existe; si no, `grupos_ruta ∪ add_groups`.
- Validador de carga (igual que T7.1): cada grupo existe en `approver_groups` y `min_efectivo ≤` miembros distintos.
- Aprobaciones requeridas totales siguen siendo `max(base R04, R14 efectivo)` (T7.1 §3). R14 FALLA con `detail` «Ruta "alto-monto" con excepción "globex-sobre-limite": requiere 1 aprobación de cfo.»; `evidence.clause = "<ruta>+<excepción>"`; `quote` canónico como en T7.1. `GET /decisions/{id}/approval` lee esa evidencia congelada sin cambios de contrato.
- Una excepción no cambia R02: Globex sobre el límite sigue FALLA en R02 (ESCALAR en `data/rules.json`); la excepción solo decide **quién** firma. Si el `on_fail` de una regla es FRENAR, ninguna excepción lo baja.

## 5. API y Frontend

- `GET /decisions` gana campos derivados de solo lectura por fila: `priority`, `due_date`, `conflict` (`true` si R22 FALLA) y `protected` (texto del pago protegido). No se guardan en `DecisionRecord`: se calculan desde la extracción y los chequeos congelados.
- `GET /conflicts` (nuevo, solo lectura, por dueño): decisiones abiertas con R22 en FALLA, agrupadas por pago protegido.
- `/aprobaciones`: cola ordenada por **prioridad** (crítico primero) y luego **fecha de vencimiento** ascendente (sin fecha al final); insignia de prioridad y «Protege: cuota 2/3 de Nominex SAS (31-mar)». El orden es presentación; no cambia requisitos ni decisión.
- `/` (resumen): tarjeta **«Conflictos detectados»** con el número y la lista corta (factura → pago protegido → fecha), enlazando a la ficha.
- `/reglas`: secciones «Prioridades del negocio» y «Excepciones permitidas»; texto fijo: «Las prioridades ordenan y escalan; nunca aprueban un pago. Las excepciones cambian quién aprueba, nunca cuántas firmas mínimas.»
- Proxies en `frontend/app/api/` con 502 explícito (T5.9, T6.7). Configuración por dueño cuando T9.6 aterrice.

## 6. Fuera de alcance

Elegir o reprogramar pagos automáticamente; posponer una factura; optimizar el flujo de caja; excepciones que reduzcan firmas, bajen severidad o habiliten PAGAR; prioridades sugeridas por el LLM; notificaciones; tocar `data/rules.json`, dev, holdout, f7, goldens o `catalog.json`.

## 7. Criterios de aceptación

1. `backend/tests/rules/test_business_priorities.py`: resolución proveedor > categoría > default; beneficiario ausente → `bajo`; validadores (clave en blanco, categoría inválida, reserva ≤ 0, ids repetidos).
2. `backend/tests/rules/test_r22_priority_conflict.py`: conflicto con cuota de serie pendiente → FALLA nombrando serie, ítem y fecha; misma serie ya pagada en el mes → no protege; factura de prioridad igual o mayor → no protegida; ESCALAR pendiente de mayor prioridad → protege; reprocesar la propia factura no se protege a sí misma; reserva protege a `normal`/`bajo` y no a `alto`; dato faltante → INDETERMINADO; R03 ya en FALLA → OK «ya lo cubre R03».
3. `backend/tests/rules/test_allowed_exceptions.py`: redirección a `cfo`; `add_groups` suma; `min_approvals` menor que el de la ruta → queda el de la ruta (`max`); excepción sobre ruta `auto` exige ≥ 1; `match` vacío → error; sin `approval_policy` → error; R02 en FALLA sigue en FALLA.
4. **Property test** (≥ 500 casos, semilla fija): para cualquier `business_priorities`, `allowed_exceptions` y contexto válidos, `SEVERITY[decide(con)] ≥ SEVERITY[decide(sin)]` y `aprobaciones_requeridas(con) ≥ aprobaciones_requeridas(sin)`; nunca un no-PAGAR pasa a PAGAR.
5. Split sintético nuevo **`f9_7`** (`data/f9_7/rules.json`, `data/invoices/f9_7/`, `data/golden/f9_7.json`, ≥ 8 casos, mismo formato que f7, con `ledger_seed` y `pending_seed`): (a) normal que deja sin saldo una cuota crítica → ESCALAR R22; (b) mismo caso con la cuota ya pagada → PAGAR; (c) crítica que consume saldo de una normal pendiente → sin R22; (d) ESCALAR alto pendiente protegido → ESCALAR R22; (e) reserva de nómina violada por una `bajo` → ESCALAR R22; (f) excepción Globex sobre el límite → ESCALAR R02+R14 con ruta a `cfo`; (g) proveedor desconocido con prioridad configurada → sigue FRENAR R01; (h) duplicado exacto de proveedor crítico → sigue FRENAR R05. `python eval/run_motor.py --split f9_7` → 100 %, `unsafe_pay=0`.
6. Sin las secciones nuevas: `python eval/run_motor.py` dev 34/34 y `--split f7` 16/16, `unsafe_pay=0`, chequeos idénticos; `pytest -q` 0 failed; `ruff check .` ok; frontend `npx tsc --noEmit && npm run lint && npm test` ok (prueba del orden de la cola y de la tarjeta); `backend/openapi.json` con `GET /conflicts` y los campos nuevos.
7. Tablero T9.7 → HECHA con evidencia; fila en `docs/AI_USAGE_LOG.md`; commit y push con el §8.

## 8. Commit

```text
T9.7: business priorities, payment conflict rule R22 and allowed exceptions
```

## 9. Mensaje para la sesión que implementa

```text
Implementa T9.7 según docs/T9_7_SPEC.md. Decisión D065.
Secciones opcionales business_priorities (critico/alto/normal/bajo por
proveedor y por categoría, reservas) y allowed_exceptions. Regla R22
«Conflicto de prioridad»: si pagar esta factura deja el saldo del mes (base
R03/R07, amount_base) sin espacio para pagos de MAYOR prioridad ya
comprometidos (series confirmadas sin pagar, ESCALAR pendientes, reservas),
ESCALAR nombrando el pago protegido y su fecha. Excepciones solo agregan o
redirigen aprobadores, nunca bajan min_approvals ni severidad. Sin las
secciones, R22 no se emite: dev 34/34, f7 16/16, unsafe_pay=0. decide()
sigue puro; property test obligatorio. Cola de /aprobaciones por prioridad
y vencimiento; tarjeta «Conflictos detectados». Split f9_7 nuevo. Tests
primero. Commit y push:
T9.7: business priorities, payment conflict rule R22 and allowed exceptions
```
