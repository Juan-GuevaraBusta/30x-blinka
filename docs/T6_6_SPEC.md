# Spec T6.6 — Página de estado única y sincronización del roadmap con el tablero

Dueño: **Orquestador**. Carril: B. Skill de dominio: NINGUNA. Proceso: ninguno adicional.

Depende de: ninguna. Puede hacerse en cualquier momento; cuanto más tarde, más filas del tablero hay que reflejar en `docs/STATUS.md`, así que conviene hacerla cerca del final de F5/F6.

Estado: contrato para la sesión que **implemente** T6.6. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D055** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio NINGUNA.

Lecturas:

- `docs/TASK_BOARD.md` completo (fuente de verdad del estado de cada tarea y gate)
- `docs/05_PHASES_AND_ROADMAP.md` completo (las casillas `[ ]`/`[x]` de F0–F6, hoy desincronizadas: por ejemplo T0.2–T0.5 siguen `[ ]` aunque el tablero las marca HECHA, y T1.1–T4.10 siguen `[ ]` aunque el tablero las marca HECHA/HECHO)
- `docs/03_JUDGE_REVERSE_ENGINEERING.md` línea 84 (confirmado en esta sesión: `| Fail-closed ante error | backend/tests/test_fail_closed.py |` — esa ruta no existe; el archivo real es `backend/tests/gate/test_fail_closed.py`, D026, `docs/TASK_BOARD.md` fila T3.10)
- `docs/HANDOFF_PROMPT_PIPELINE_SMOKE_AND_G4.md` línea 8 (confirmado en esta sesión: `Repo: /Users/juanluisguevarabustamante/Developer/personal/hackathons/30x-blinka`, una ruta absoluta de una máquina específica)
- `docs/DECISIONS_LOG.md` (para citar los cierres de gate con su ID: D027 G0, D015/D028 G1/G2, D039 G3, D040 G4)
- No tocar `README.md` ni `JUDGE_GUIDE.md`: son de T5.5/T5.6 (Docs & Judge), explícitamente fuera de esta tarea.

## 1. Qué es T6.6

Tres correcciones de consistencia documental, sin tocar código ni datos:

| Entrega | Qué hace |
|---|---|
| `docs/STATUS.md` (nuevo) | Una página corta: qué gates están cerrados (con su decisión), qué métricas existen y de qué reporte salen (citando archivo), qué sigue pendiente |
| `docs/05_PHASES_AND_ROADMAP.md` | Las casillas `[ ]`/`[x]` de F0–F6 pasan a coincidir con el estado real de `docs/TASK_BOARD.md` |
| `docs/03_JUDGE_REVERSE_ENGINEERING.md` | La fila que cita `backend/tests/test_fail_closed.py` pasa a citar la ruta real, `backend/tests/gate/test_fail_closed.py` |
| `docs/HANDOFF_PROMPT_PIPELINE_SMOKE_AND_G4.md` | La ruta absoluta de una máquina se sustituye por una referencia relativa al repo (o se elimina la línea si el prompt no necesita la ruta para funcionar en otra máquina) |

## 2. `docs/STATUS.md`

Estructura mínima, en español:

- **Gates**: una fila por G0–G6, con su estado (HECHA/PENDIENTE), la decisión que lo cerró (ej. G0→D027, G1→D015, G2→D028, G3→D039, G4→D040) y, si está PENDIENTE, qué tareas le faltan (leído de la columna «Depende de» de `docs/TASK_BOARD.md` en el momento de escribir esta página — no copiar el texto de este spec, que puede quedar desactualizado).
- **Métricas citadas, con su fuente**: `unsafe_pay` y autonomía del motor (G2, `docs/DECISIONS_LOG.md` D028), del e2e dev (G3, `eval/reports/g3_closure_2026-10-17.md`, D039), y de `eval/reports/latest.md` si ya existe al escribir esta página (T5.1). Ninguna cifra sin la ruta del archivo que la sostiene, en el mismo espíritu que `docs/T5_6_SPEC.md`.
- **Pendiente**: lista corta de lo que sigue PENDIENTE en el tablero al momento de escribir, agrupado por fase (F5: …; F6: …), sin copiar la tabla entera del tablero — un enlace a `docs/TASK_BOARD.md` para el detalle.
- Una frase al final: esta página es una fotografía al momento de escribirla; la fuente de verdad viva sigue siendo `docs/TASK_BOARD.md`.

`docs/STATUS.md` no reemplaza al tablero ni al roadmap: es un resumen de una pantalla para alguien que solo tiene cinco minutos.

## 3. Sincronizar `docs/05_PHASES_AND_ROADMAP.md`

Recorrer cada tarea listada en F0–F6 (`- [ ] **T_._** …`) y, para cada una, mirar su fila en `docs/TASK_BOARD.md`:

- Estado `HECHA`, `HECHO` o `VERIFICADA` en el tablero → casilla `- [x]` en el roadmap.
- Estado `PENDIENTE`, `EN CURSO` o `BLOQUEADA` → casilla sigue `- [ ]`.
- Esta tarea también añade, en el mismo pase, las líneas de T5.7–T5.11 y T6.4–T6.6 en F5/F6 si Task B (registro en el tablero, mismo D055) todavía no las dejó escritas ahí — comprobar primero si ya están, para no duplicar líneas.
- Los gates (`**G0:** …`) no llevan casilla propia en este archivo (son párrafos, no items de lista); no se les añade una. Dejar su texto igual salvo que el estado real del gate contradiga la fecha o el motivo ya escrito — en ese caso, corregir solo la frase que sea falsa, citando la fila del tablero o la decisión que lo cerró.

No reordenar tareas, no añadir tareas nuevas que no estén ya en `docs/TASK_BOARD.md`, no borrar la sección «Líneas de corte» ni «Riesgos de tiempo».

## 4. Fuera de alcance

- Tocar `README.md`, `JUDGE_GUIDE.md`, `docs/examples/records/` o `docs/DEMO_SCRIPT.md` (T5.5/T5.6/T6.1, dueño Docs & Judge).
- Auditar afirmaciones del README o de `JUDGE_GUIDE.md` contra archivos (eso es T5.6, ya con su propio contrato en `docs/T5_6_SPEC.md`).
- Cambiar código, tests, `data/` o `eval/`.
- Corregir cualquier otra inconsistencia de `docs/03_JUDGE_REVERSE_ENGINEERING.md` más allá de la ruta citada en el §0 — si se encuentra otra, anotarla en `docs/STATUS.md` como pendiente de revisión, no corregirla aquí sin que el spec la haya autorizado explícitamente.
- Reescribir el prompt completo de `docs/HANDOFF_PROMPT_PIPELINE_SMOKE_AND_G4.md`: solo la línea de la ruta absoluta.
- Cerrar G5 o G6, o marcar como hecha cualquier tarea que no sea T6.6 en el tablero.

## 5. Criterios de aceptación

1. `docs/STATUS.md` existe, con las tres secciones del §2, cada cifra citando su archivo fuente, y ninguna afirmación sobre un gate que el tablero no sostenga ese día.
2. `docs/05_PHASES_AND_ROADMAP.md`: cada tarea con estado HECHA/HECHO/VERIFICADA en `docs/TASK_BOARD.md` tiene su casilla en `[x]`; ninguna tarea PENDIENTE/EN CURSO/BLOQUEADA aparece como `[x]`. Las líneas de T5.7–T5.11 y T6.4–T6.6 están presentes en F5/F6 (propias o ya puestas por Task B).
3. `docs/03_JUDGE_REVERSE_ENGINEERING.md` línea con «Fail-closed ante error» cita `backend/tests/gate/test_fail_closed.py`. El archivo citado existe en esa ruta (comprobado en esta sesión).
4. `docs/HANDOFF_PROMPT_PIPELINE_SMOKE_AND_G4.md` ya no contiene una ruta absoluta de una máquina específica (`/Users/...`); el prompt sigue siendo utilizable (una referencia relativa al repo, o la línea retirada si no hace falta).
5. Diff limpio: `docs/STATUS.md` (nuevo), `docs/05_PHASES_AND_ROADMAP.md`, `docs/03_JUDGE_REVERSE_ENGINEERING.md`, `docs/HANDOFF_PROMPT_PIPELINE_SMOKE_AND_G4.md`, más `docs/TASK_BOARD.md` y `docs/AI_USAGE_LOG.md` al cerrar. Sin tocar `README.md`, `JUDGE_GUIDE.md`, código ni `data/`.
6. `docs/TASK_BOARD.md`: T6.6 pasa a HECHA, con la ruta de `docs/STATUS.md` como evidencia.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit y push con el mensaje del §6.

## 6. Commit

```text
T6.6: add status page and sync roadmap with task board
```

## 7. Mensaje para la sesión que implementa

```text
Implementa T6.6 según docs/T6_6_SPEC.md. Decisión D055.
Crea docs/STATUS.md: gates G0-G6 con su decisión de cierre, métricas con su
archivo fuente (G2/D028, G3/eval/reports/g3_closure_2026-10-17.md/D039,
latest.md si ya existe), y pendientes por fase, enlazando TASK_BOARD.md.
Sincroniza las casillas [ ]/[x] de docs/05_PHASES_AND_ROADMAP.md con el
estado real de docs/TASK_BOARD.md (HECHA/HECHO/VERIFICADA -> [x]; el resto
sigue [ ]). Verifica que T5.7-T5.11 y T6.4-T6.6 ya están listadas ahí (Task
B del registro general), sin duplicarlas si ya están.
Corrige docs/03_JUDGE_REVERSE_ENGINEERING.md línea 84: la ruta
backend/tests/test_fail_closed.py no existe; es
backend/tests/gate/test_fail_closed.py.
Corrige docs/HANDOFF_PROMPT_PIPELINE_SMOKE_AND_G4.md línea 8: quita la ruta
absoluta /Users/juanluisguevarabustamante/... y sustitúyela por algo
repo-relativo o retírala si no es necesaria.
No toques README.md, JUDGE_GUIDE.md, docs/DEMO_SCRIPT.md, código ni data/.
Al terminar: tablero y AI_USAGE_LOG. Commit y push:
T6.6: add status page and sync roadmap with task board
```
