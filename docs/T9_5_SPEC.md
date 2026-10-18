# Spec T9.5 — Línea de tiempo del proveedor: último pago, próximo esperado, cadencia y horas extra

Dueño: **Frontend** (`frontend/app/ajustes/proveedores/[nombre]/`). Carril: B. Colabora: **API** (endpoint de solo lectura `GET /vendors/{vendor_key}/timeline` y persistencia aditiva de líneas medidas), **Rules Engine** (cálculo puro de la línea de tiempo en `backend/app/rules/vendor_timeline.py`). Skill de dominio: `frontend-design` (TOTAL en UI); proceso: `test-driven-development` en el cálculo.

Prioridad: **P1**. Depende de: T9.1 (acuerdo compilado) y T7.5 (vista de proveedor, HECHA). Se luce con T9.3 (historial semilla). No bloquea G9.

Estado: contrato para la sesión que **implemente** T9.5. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D061** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Declarar `frontend-design` y leerla. Lecturas:

- `docs/T9_1_SPEC.md` §2 y §4 (acuerdo y compilación), `docs/T7_2_SPEC.md` §2 (`period_key`), `docs/T7_3_SPEC.md` §2–§3 (`MeteredLine`, R19).
- `backend/app/rules/payment_series.py`, `backend/app/rules/variable_pricing.py`, `backend/app/rules/ledger_queries.py` (`COUNTED_DECISIONS`).
- `frontend/app/ajustes/proveedores/[nombre]/VendorDetailScreen.tsx` (calendario de T7.5) y `frontend/lib/` (proxies, 502).

## 1. Qué es T9.5

El equipo de finanzas quiere ver, por proveedor y en español llano: cuándo se le pagó por última vez, cuándo se espera la próxima factura, si la cadencia va al día según el acuerdo y, para acuerdos por horas, cuántas horas extra se han facturado frente a lo pactado. Todo sale del ledger y del acuerdo compilado; la pantalla no calcula decisiones.

## 2. Cálculo (función pura, Rules Engine)

`vendor_timeline(agreement, compiled, ledger, today) -> VendorTimeline` (`today` se inyecta; sin reloj interno):

- `last_payment`: última entrada en `COUNTED_DECISIONS` del proveedor (fecha, número, monto, periodo).
- `next_expected`: siguiente clave de periodo (o siguiente cuota/hito sin pagar) con su ventana; `null` si el acuerdo terminó.
- `cadence`: por periodo desde `valid_from` hasta `today`: `pagado`, `pendiente_aprobacion`, `frenado`, `sin_factura`, `fuera_de_calendario`. Resumen: `al_dia` | `atrasado` (algún periodo vencido `sin_factura`) | `cobro_fuera_de_calendario`.
- `hours` (solo `hourly`): por periodo, horas facturadas, incluidas, extra, tope de extras y si se superó; montos esperados con la misma función `expected_amount` de R19.
- Totales: pagado frente a `total_cap`.

## 3. API (solo lectura)

- `GET /vendors/{vendor_key}/timeline` → `VendorTimeline`. Proveedor sin acuerdo activo → 200 con `agreement=null` y solo `last_payment`.
- Las líneas medidas hoy viajan en el estado del grafo y no se guardan. Se agrega persistencia **aditiva** fuera de `DecisionRecord` (tabla `decision_metered_lines`, por `decision_id`), solo para mostrar; la fuente de verdad del cálculo sigue siendo R19 en el registro. Decisiones previas sin líneas → horas «sin dato».

## 4. Pantalla

En `/ajustes/proveedores/[nombre]`, sobre el calendario existente:

- Tarjetas: «Último pago: 2026-02-05, USD 800 (INV-GX-2026-0205)», «Próxima factura esperada: marzo 2026», «Cadencia: al día» o «Atrasado: febrero sin factura».
- Para horas: tabla por mes «Horas facturadas / incluidas / extra (máx. 16)» con aviso «Se facturaron 20 h extra; el acuerdo permite 16.»
- Barra de total pagado frente al tope del acuerdo, con texto, no solo color.
- Enlace a cada decisión. Textos desde plantillas fijas, nunca desde LLM. Sin acuerdo: «Este proveedor no tiene un acuerdo registrado.» con enlace a `/ajustes/acuerdos/nuevo`.

## 5. Fuera de alcance

Predicción con modelos, alertas por correo, editar el acuerdo desde esta vista, gráficos complejos, cualquier botón de pagar.

## 6. Criterios de aceptación

1. `backend/tests/rules/test_vendor_timeline.py`: retainer al día, retainer con mes sin factura, cuotas con una fuera de calendario, horas con extras dentro y fuera del tope; `today` fijo.
2. API: timeline de proveedor sin acuerdo → `agreement=null`; con historial semilla de T9.3 coincide con lo esperado.
3. Frontend: vitest para tarjetas, tabla de horas y estado sin acuerdo; 502 → «No se pudo conectar con el servidor»; 375 px sin desplazamiento horizontal; `npx tsc --noEmit && npm run lint && npm test` ok.
4. `pytest -q` 0 failed; `ruff check .` ok; motor dev 34/34 `unsafe_pay=0`; `backend/openapi.json` incluye el endpoint.
5. Tablero T9.5 → HECHA (o PARCIAL con lo que faltó); fila en `docs/AI_USAGE_LOG.md`; commit y push con el §7.

## 7. Commit

```text
T9.5: vendor timeline with cadence and overtime checks from ledger
```

## 8. Mensaje para la sesión que implementa

```text
Implementa T9.5 según docs/T9_5_SPEC.md. Decisión D061.
Función pura vendor_timeline(agreement, compiled, ledger, today): último
pago, próximo esperado, cadencia por periodo y horas extra frente a lo
pactado (misma expected_amount de R19). GET /vendors/{vendor_key}/timeline
de solo lectura; líneas medidas en tabla aditiva solo para mostrar. En
/ajustes/proveedores/[nombre], tarjetas y tabla de horas en español llano,
sin botón de pagar. Tests primero. Commit y push:
T9.5: vendor timeline with cadence and overtime checks from ledger
```
