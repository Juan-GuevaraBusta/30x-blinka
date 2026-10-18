# STATUS — estado actual del proyecto

Fotografía al 2026-10-18. La fuente de verdad viva es `docs/TASK_BOARD.md`; esta página es un resumen de una pantalla, no la reemplaza.

## Gates

| Gate | Estado | Decisión de cierre | Si está PENDIENTE, qué falta |
|---|---|---|---|
| G0 | HECHA | `docs/DECISIONS_LOG.md` D027 (G0 cerrado) | — |
| G1 | HECHO | `docs/DECISIONS_LOG.md` D015 | — |
| G2 | HECHA | `docs/DECISIONS_LOG.md` D028 (G2 cerrado) | — |
| G3 | HECHA | `docs/DECISIONS_LOG.md` D039 (G3 cerrado) | — |
| G4 | HECHA | `docs/DECISIONS_LOG.md` D040 (G4 cerrado) | — |
| G5 | PENDIENTE | — | Depende de T5.1, T5.3, T5.6, T5.8, T5.9 (`docs/TASK_BOARD.md`). T5.8, T5.9 y T5.3 ya HECHA; faltan T5.1 y T5.6 |
| G6 | PENDIENTE | — | Depende de T6.1, T6.2, T6.3 (`docs/TASK_BOARD.md`). T6.1 ya HECHA (`docs/DEMO_SCRIPT.md` final); faltan T6.2 y T6.3, y el ensayo grabado |
| G7 | PENDIENTE | — | Depende de T7.6, T7.1, T7.2 (`docs/TASK_BOARD.md`), las tres ya HECHA; falta la corrida de holdout (depende de T5.1) |
| G9 | PENDIENTE | — | Depende de T9.1, T9.2, T9.3 (`docs/TASK_BOARD.md`), las tres ya HECHA; falta el ensayo grabado de la demo semilla y su nota en `docs/DEMO_SCRIPT.md` |

## Métricas citadas, con su fuente

| Métrica | Valor | Fuente |
|---|---|---|
| Motor (extracción verdadera, set dev) | 100 % de decisiones correctas (34/34), `unsafe_pay = 0` | `docs/DECISIONS_LOG.md` D028 (G2 cerrado); `docs/G2_SPEC.md` §6 |
| E2E grafo, set dev | autonomía de línea base 55.9 % (19/34), `unsafe_pay = 0` | `eval/reports/g3_closure_2026-10-17.md`; `docs/DECISIONS_LOG.md` D039 |
| Eval completa (dev + holdout) | aún no existe | `eval/reports/latest.md` todavía no se ha generado en este repo (T5.1, PENDIENTE) |

Ninguna otra cifra de métricas se afirma en esta página sin el archivo que la sostiene.

## URLs públicas

- Frontend: <https://blinka-invoice-agent.vercel.app>
- API backend: <https://blinka-invoice-api.onrender.com>

## CI

- Badge / workflow: <https://github.com/Juan-GuevaraBusta/30x-blinka/actions/workflows/ci.yml>

## Diagrama de arquitectura

- `docs/diagrams/architecture.md`

## Pendiente, por fase

Regenerado desde la columna Estado de `docs/TASK_BOARD.md` (2026-10-18). F0–F4 no tienen tareas PENDIENTE.

- **F5:** T5.1 (eval dev + holdout), T5.4 (lectura ciega), T5.5 (README, `JUDGE_GUIDE.md` y ejemplos de registros), T5.6 (revisión final de afirmaciones).
- **F6:** T6.2 (video de respaldo), T6.3 (etiqueta y congelar rama).
- **F9:** T9.4, T9.5, T9.6 (reemplazada por T9.8), T9.7.

## Hecho, por fase (F5–F9)

F0–F4 ya están cerradas por las gates G0–G4 arriba; el detalle tarea por tarea queda en `docs/TASK_BOARD.md`.

- **F5:** T5.2 (calibrar JEV), T5.3 (casos adversariales), T5.7 (unificar import del backend), T5.8 (lock de ledger por periodo), T5.9 (clave de admin + validar aprobador; `ADMIN_API_KEY` en Render/Vercel y humo público 2026-10-18 en fila T5.9 del tablero), T5.10 (hash-chain de registros), T5.12 (decodificar streams FlateDecode en PDF). T5.11 (`Decimal` para dinero) quedó **DESCARTADA** (P2, riesgo a última hora).
- **F6:** T6.1 (guion de demo final, `docs/DEMO_SCRIPT.md`), T6.4 (CI con gate de eval y CodeQL), T6.5 (licencia/seguridad/contribución), T6.6 (página de estado y sincronización del roadmap), T6.7 (navegación global, tablero inicial y decisiones clicables).
- **F7:** T7.1–T7.6 (política de aprobación N-de-M, series por proveedor, pagos variables, alta auditada de proveedor, pantallas de finanzas, dataset f7).
- **F9:** T9.1 (registro de acuerdos), T9.2 (bandeja de entrada), T9.3 (empresa semilla P.J Gorman + comando de reinicio + paquete de demo), T9.8 (multiempresa, reemplaza T9.6).

Detalle completo de cada tarea, dueño y evidencia: `docs/TASK_BOARD.md`.

---

Esta página es una fotografía al momento de escribirla. La fuente de verdad viva sigue siendo `docs/TASK_BOARD.md`.
