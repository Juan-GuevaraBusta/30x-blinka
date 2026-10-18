# STATUS — estado actual del proyecto

Fotografía al 2026-10-17. La fuente de verdad viva es `docs/TASK_BOARD.md`; esta página es un resumen de una pantalla, no la reemplaza.

## Gates

| Gate | Estado | Decisión de cierre | Si está PENDIENTE, qué falta |
|---|---|---|---|
| G0 | HECHA | `docs/DECISIONS_LOG.md` D027 (G0 cerrado) | — |
| G1 | HECHO | `docs/DECISIONS_LOG.md` D015 | — |
| G2 | HECHA | `docs/DECISIONS_LOG.md` D028 (G2 cerrado) | — |
| G3 | HECHA | `docs/DECISIONS_LOG.md` D039 (G3 cerrado) | — |
| G4 | HECHA | `docs/DECISIONS_LOG.md` D040 (G4 cerrado) | — |
| G5 | PENDIENTE | — | Depende de T5.1, T5.3, T5.6, T5.8, T5.9 (`docs/TASK_BOARD.md`). T5.8 y T5.9 ya HECHA; faltan T5.1, T5.3 y T5.6 |
| G6 | PENDIENTE | — | Depende de T6.1, T6.2, T6.3 (`docs/TASK_BOARD.md`), las tres PENDIENTE |

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

Regenerado desde la columna Estado de `docs/TASK_BOARD.md` (2026-10-17). F0–F4 no tienen tareas PENDIENTE.

- **F5:** T5.1 (eval dev + holdout), T5.2 (calibrar JEV), T5.3 (casos adversariales), T5.4 (lectura ciega), T5.5 (README, `JUDGE_GUIDE.md` y ejemplos de registros), T5.6 (revisión final de afirmaciones), T5.10 (hash-chain de registros), T5.11 (`Decimal` para dinero).
- **F6:** T6.1 (guion de demo), T6.2 (video de respaldo), T6.3 (etiqueta y congelar rama).

## Hecho, por fase (F5–F6)

F0–F4 ya están cerradas por las gates G0–G4 arriba; el detalle tarea por tarea queda en `docs/TASK_BOARD.md`.

- **F5:** T5.7 (unificar import del backend), T5.8 (lock de ledger por periodo), T5.9 (clave de admin + validar aprobador), T5.12 (decodificar streams FlateDecode en PDF).
- **F6:** T6.4 (CI con gate de eval y CodeQL), T6.5 (licencia/seguridad/contribución), T6.6 (página de estado y sincronización del roadmap), T6.7 (navegación global, tablero inicial y decisiones clicables).

Detalle completo de cada tarea, dueño y evidencia: `docs/TASK_BOARD.md`.

---

Esta página es una fotografía al momento de escribirla. La fuente de verdad viva sigue siendo `docs/TASK_BOARD.md`.
