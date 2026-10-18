# Spec T5.6 — Revisión final de afirmaciones

Dueño: **Docs & Judge**. Skill: `verification-before-completion` (TOTAL). Ruta que la sesión que implemente debe leer antes de tocar archivos:

`~/.cursor/plugins/cache/cursor-public/superpowers/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/verification-before-completion/SKILL.md`

Esa ruta es una caché local de Cursor y solo existe en la máquina donde se instaló. Si la sesión que implementa corre en otra máquina o en otro IDE y el archivo no está ahí, se aplica la misma regla que esta tarea audita: ninguna afirmación sin abrir el archivo citado. La sesión no inventa el contenido de la skill ni sigue adelante como si la hubiera leído; anota en `docs/AI_USAGE_LOG.md` que la skill estuvo ausente en esa máquina y continúa el resto del checklist sin ese paso.

Depende de **T5.5**. Si T5.5 sigue PENDIENTE en `docs/TASK_BOARD.md`, esta tarea se detiene: no se rellena la tabla afirmación→evidencia en su lugar.

Estado: contrato para la sesión que **implemente** T5.6. Este archivo no borra afirmaciones, no cierra T5.6 y no cierra **G5**.

Decisión que fija este contrato: **D047**.

`docs/05_PHASES_AND_ROADMAP.md` describe T5.6 como «revisión final de afirmaciones: borrar lo que no tenga evidencia» y G5 como `unsafe_pay = 0` en dev, holdout y adversariales, reporte commiteado y README verificable. G5 exige T5.1, T5.3 y T5.6. Cumplir este spec deja la guía honesta; el cierre de G5 es del Orquestador y pide además `eval/reports/latest.md`.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Antes de editar, leer y declarar en una línea la skill `verification-before-completion` (TOTAL). Luego abrir el `SKILL.md` de la ruta de arriba.

Lecturas:

- `AGENTS.md` (I6 solo datos sintéticos; I8 cero dinero; I9 es el gate de `unsafe_pay` en la evaluación)
- `docs/SKILLS_MAP.md` fila T5.6
- `docs/05_PHASES_AND_ROADMAP.md` fila T5.6 y el párrafo **G5**
- `docs/TASK_BOARD.md` filas T5.5, T5.6 y G5
- `JUDGE_GUIDE.md` y `README.md` tal como estén **después** de T5.5
- `docs/03_JUDGE_REVERSE_ENGINEERING.md` (la tabla afirmación→evidencia es el artefacto que un juez recorre)
- `docs/DECISIONS_LOG.md` fila D039
- `eval/reports/g3_closure_2026-10-17.md` (solo si una fila habla de `unsafe_pay` en el e2e de dev)
- `render.yaml` (para la fila de I9 y el deploy)

Cómo se aplica la skill en esta tarea: ninguna afirmación de éxito sin evidencia fresca. La evidencia es abrir, en esta sesión, el archivo citado y comprobar que dice lo que la fila dice. Un corrido anterior, un «debería», el relato de otro agente o una fila del tablero que dice POR COMPLETAR no bastan. Si el path no existe, o el archivo no dice eso, la fila se borra o se baja a «no afirmado». No se marca T5.6 HECHA sin haber abierto cada archivo que las filas conservadas citan.

## 1. Qué es T5.6

Una pasada de auditoría sobre el texto que un juez leería: la tabla **Afirmación → evidencia** de `JUDGE_GUIDE.md` y las afirmaciones de producto de `README.md`.

Cada fila se contrasta con un archivo del repo. Si el path no existe, o el archivo no dice eso, se **borra** la fila o se baja a **«no afirmado»**. No se inventa el archivo. No se escribe evidencia falsa. No se edita código de producto para hacer verdadera una frase. Si una frase es falsa, se quita.

«No afirmado» significa: el proyecto no sostiene ese hecho. La celda de evidencia dice por qué (path ausente, o el archivo abierto no lo dice). No es un éxito disfrazado y no lleva un path inventado.

## 2. Checklist de la auditoría

Recorrer **cada** fila de la tabla afirmación→evidencia de `JUDGE_GUIDE.md`, en orden:

1. Copiar el path o los paths de la columna de evidencia.
2. Comprobar que el path existe en el repo (archivo, no un directorio vacío ni un enlace roto).
3. Abrir el archivo en esta sesión y leer si el texto sostiene la afirmación de esa fila. Un archivo vecino no sustituye al citado.
4. Si el path no existe, o el archivo no dice eso: borrar la fila, o dejarla como «no afirmado» con el motivo en una frase.
5. Si se conserva la fila, la columna de evidencia sigue apuntando a ese archivo, que ya se abrió.

La misma pasada sobre `README.md`: cada frase que afirme un hecho del producto (fase, métricas, holdout, `unsafe_pay`, deploy, I9, URL pública, «el repo está vacío», «el deploy aún no existe») tiene un archivo que la sostiene, o se borra, o se baja a «no afirmado».

Una tabla vacía es un resultado válido. Una fila que parece promesa («pendiente», «cuando exista», un path que no está) no se deja como si fuera evidencia.

## 3. Qué cuenta como evidencia

Cuenta:

- Un archivo que existe en la ruta citada.
- El texto de ese archivo, leído en esta sesión, dice el hecho de la fila.
- Una cifra (autonomía, `unsafe_pay`, totales) solo si ese mismo archivo la trae escrita.

No cuenta:

- El nombre del archivo sin abrirlo.
- Que «en su momento» un comando salió bien, si esta fila habla de un resultado y el reporte citado no lo trae.
- Crear el archivo que falta para que la fila quede bien.
- Copiar una cifra de D039 o del cierre G3 a una fila de holdout, de adversariales o de deploy.
- Marcar G5, T5.1 o T5.3 como hechos desde esta tarea.

## 4. Reglas de cifras y de I9

Estas reglas mandan sobre el texto que T5.5 haya dejado.

**Holdout.** Cifras de holdout solo si `eval/reports/latest.md` existe y las trae. Al escribir este spec, ese archivo no está: en `eval/reports/` solo está `g3_closure_2026-10-17.md`. Si `latest.md` sigue ausente cuando se audite, no se afirma holdout. No se crea `latest.md` aquí. No se toca `data/invoices/holdout/` ni el golden de holdout.

**`unsafe_pay = 0` en el e2e de dev.** Solo con cita a `eval/reports/g3_closure_2026-10-17.md` o a la fila D039 de `docs/DECISIONS_LOG.md`. Ese alcance es el e2e del grafo sobre las 34 facturas de dev (`unsafe_pay = 0`, autonomía 55.9 %). No se extiende a holdout, a adversariales ni al deploy.

**I9 y el deploy.** I9, en `AGENTS.md`, dice que `unsafe_pay > 0` en la evaluación bloquea el despliegue. Eso es la regla del proyecto. Afirmar que **el deploy ya está bloqueado por ese gate** exige que el pipeline de deploy ejecute el eval. Al escribir este spec, `render.yaml` arranca `uvicorn` y no llama a `eval/`; no hay workflow en `.github/`. Si al auditar sigue igual, la fila dice que **no está cableado**. No se edita `render.yaml` ni se añade un workflow para hacer verdadera la frase de `docs/06_EVAL_AND_TEST_PLAN.md` («el pipeline de eval se ejecuta antes de cada deploy»). Si al auditar `docs/TASK_BOARD.md` muestra la fila T6.4 como HECHA (`docs/T6_4_SPEC.md`, D055), la fila de `JUDGE_GUIDE.md` puede decir que el gate de eval (`unsafe_pay`) **sí está cableado en CI de GitHub Actions**, citando `.github/workflows/ci.yml`, pero sigue diciendo que **no está cableado en el despliegue de Render**, salvo que la auditoría encuentre evidencia de que Render espera a esa CI (al escribir este spec, no la hay). No se mezclan las dos afirmaciones en una sola frase.

## 5. Fuera de alcance

- Cerrar G5, T5.1, T5.2, T5.3 o T5.4. Escribir `eval/reports/latest.md` o `eval/reports/blind_read.md`.
- Tocar holdout, `data/`, `eval/` (código o reportes), `backend/`, `frontend/`, `render.yaml`, tests o cualquier código de producto para «hacer verdadera» una frase.
- Leer `.env` ni pegar claves.
- Rellenar la guía si T5.5 no la escribió. T5.5 es quien arma README, `JUDGE_GUIDE.md` y `docs/examples/records/`.
- Borrar afirmaciones en esta sesión de spec. La auditoría es de la sesión que implementa T5.6.
- Afirmar que el deploy público paga, o que un `PAGAR` registrado mueve dinero (I8).

## 6. Foto al escribir el spec (2026-10-17)

Esto no es el resultado de la auditoría. T5.5 puede reescribir README y `JUDGE_GUIDE.md` antes. La sesión que implementa abre los archivos de nuevo. Si estas frases siguen, fallan el checklist:

| Dónde | Frase | Por qué está débil ahora |
|---|---|---|
| `README.md`, Estado | Fase actual F0; G0 abierto hasta T0.3/T0.4 | `docs/TASK_BOARD.md` tiene G0–G4 HECHA. Ningún archivo sostiene que G0 siga abierto |
| `README.md`, Despliegue | «Sustituir las URLs de ejemplo cuando exista el deploy» y la columna «URL de ejemplo» | Las mismas URLs están en la fila G4 del tablero como deploy público del 2026-10-17. La frase dice que el deploy aún no existe |
| `JUDGE_GUIDE.md`, tabla | Fila `*(pendiente T5.5)*` con evidencia `—` | No hay path. No es evidencia |
| `README.md`, Cómo usarlo | «Copia el repo vacío» | El árbol tiene `backend/`, `frontend/`, `data/` y `eval/`. Ningún archivo describe el repo actual como vacío |

## 7. Criterios de aceptación

1. T5.5 está HECHA. Si no, T5.6 sigue PENDIENTE y no hay diff de la guía.
2. Cada fila que quede en la tabla de `JUDGE_GUIDE.md` apunta a un archivo que existe y que, abierto en esta sesión, dice lo que la fila dice. El resto está borrado o en «no afirmado».
3. `README.md` no conserva las frases de la foto del §6 salvo que un archivo abierto las sostenga tal cual. Una frase falsa se quita; no se reescribe el producto para sostenerla.
4. No hay cifra de holdout si `eval/reports/latest.md` no existe o no la trae.
5. Si se menciona `unsafe_pay = 0`, la cita es el reporte G3 o D039, y el alcance es el e2e de dev. Holdout, adversariales y deploy quedan fuera de esa cifra.
6. La fila de I9, si existe, dice que el gate de eval no está cableado al deploy, mientras `render.yaml` no ejecute el eval.
7. Diff de código de producto vacío. Diff de `data/` y de `eval/` vacío. `.env` fuera del commit.
8. La nota del §8 está escrita, con cada fila borrada o bajada y el motivo.
9. `docs/TASK_BOARD.md`: solo la fila T5.6 pasa a HECHA y apunta a esa nota. G5 sigue PENDIENTE.
10. Una línea en `docs/AI_USAGE_LOG.md`.
11. Commit y push con el mensaje del §9.

## 8. Dónde queda la nota

La lista de filas borradas o bajadas se escribe **al final de este archivo**, bajo el encabezado `## Nota de auditoría`. La sesión que implementa solo añade esa sección. Cada ítem: afirmación, archivo de origen (`JUDGE_GUIDE.md` o `README.md`), qué se hizo (borrada o «no afirmado») y por qué (path ausente, o el archivo abierto no lo dice).

`docs/TASK_BOARD.md`, fila T5.6, cita `docs/T5_6_SPEC.md` «Nota de auditoría». No se duplica la lista en el tablero.

## 9. Commit

Mensaje:

```text
T5.6: remove claims that lack a cited file
```

Push a la rama de seguimiento. Sin `--force`. Sin `.env`.

## 10. Mensaje para la sesión que implementa

```text
Implementa T5.6 según docs/T5_6_SPEC.md. Decisión D047.
Skill: verification-before-completion (TOTAL). Léela en
~/.cursor/plugins/cache/cursor-public/superpowers/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/verification-before-completion/SKILL.md
y no marques HECHO sin abrir el archivo citado.
Depende de T5.5. Si T5.5 sigue PENDIENTE, para.
Recorre cada fila de la tabla afirmación→evidencia de JUDGE_GUIDE.md y las
afirmaciones de producto del README. Si el path no existe, o el archivo no dice
eso, borra la fila o bájala a «no afirmado». No inventes el archivo ni escribas
evidencia falsa. No edites código de producto para hacer verdadera una frase.
Cifras de holdout solo si eval/reports/latest.md existe y las trae.
unsafe_pay=0 del e2e de dev solo con cita a
eval/reports/g3_closure_2026-10-17.md o a D039. No lo extiendas a holdout,
adversariales ni deploy.
I9: si el pipeline de deploy no ejecuta el eval, la fila dice que no está
cableado. No toques holdout. Este spec no cierra G5.
Al terminar: diff de JUDGE_GUIDE.md y README.md, más la «Nota de auditoría»
al final de docs/T5_6_SPEC.md (filas borradas y por qué). Commit y push:
T5.6: remove claims that lack a cited file
```

## Nota de auditoría (2026-10-18)

Auditoría ejecutada con T5.1 y T5.5 ya HECHA (cifras de evaluación ya
rellenadas). Se recorrió cada fila de la tabla afirmación → evidencia de
`JUDGE_GUIDE.md` y cada frase citable de `README.md`:

- Se verificó, archivo por archivo, que cada ruta citada en `JUDGE_GUIDE.md`
  existe en el repo (comando `test -e` sobre cada path de la tabla; todas
  presentes: `backend/app/rules/decide.py`, `backend/app/gate/final_gate.py`,
  `backend/app/records/chain.py`, `.github/workflows/ci.yml`,
  `backend/app/extraction/ingest.py`, `docs/02_ARCHITECTURE.md`,
  `eval/reports/latest.md`, `eval/reports/post_t51_dev.md`,
  `eval/reports/adversarial.md`, `eval/reports/metrics_summary.json`, entre
  otras). Se abrió el contenido citado de los archivos de mayor riesgo
  (`verify-chain` en `backend/app/api/app.py`, `build_next_step` en
  `backend/app/records/build.py`, `test_r13_fail_injection_dev031`,
  `illegible` en `ingest.py`, el paso de eval en `ci.yml`, y `render.yaml`
  para la fila I9) y coincide con lo que la fila afirma.
- **Fila corregida** (`JUDGE_GUIDE.md`, afirmación sobre identidad de
  usuario): decía «hasta T9.6.0», citando `docs/TASK_BOARD.md` fila T9.6
  (PENDIENTE, D062). `docs/TASK_BOARD.md` muestra T9.6 como **REEMPLAZADA
  por T9.8** (D067), y T9.8 está **HECHA** con la nota «Identidad sigue sin
  verificar el JWT (límite conocido)». Motivo: la fila citaba una tarea que
  ya no está vigente con ese estado. Se corrigió la cita a T9.8
  (HECHA, D067) y se quitó el número de tarea inexistente «T9.6.0»,
  dejándola como límite conocido sin tarea de cierre programada. La misma
  corrección se aplicó a la fila equivalente en «5. Limitaciones
  conocidas» de `JUDGE_GUIDE.md`.
- Ninguna otra fila se borró: todas las rutas restantes existen y, al
  abrirlas, sostienen la afirmación de su fila.
- `README.md`: no se encontraron frases de la foto del §6 (fase F0, «URL de
  ejemplo», «repo vacío», fila `*(pendiente T5.5)*`); el README ya no las
  tenía antes de esta auditoría.
- **Discrepancia encontrada y no corregida en esta pasada**: la sección
  «Cuenta de prueba para jueces» del `README.md` dice que la cuenta trae
  «la política de aprobación (4 rutas)». `docs/AI_USAGE_LOG.md` (entrada
  2026-10-18 09:50) registra que esa cifra se corrigió a **2 rutas**,
  verificado contra `backend/scripts/_demo_fixtures.py`. Esta auditoría no
  tocó esa sección por instrucción explícita de mantenerla intacta; queda
  anotada aquí como afirmación no verificada para una próxima pasada.
- Sin cifras de holdout fuera de las ya citadas de `eval/reports/latest.md`
  (etiquetadas como corrida única, anterior a D068). `unsafe_pay = 0` solo
  se afirma con cita a `eval/reports/latest.md`, `post_t51_dev.md`,
  `eval/reports/adversarial.md` o `eval/reports/metrics_summary.json`,
  según el alcance de cada fila. La fila I9 sigue diciendo que el gate de
  eval está cableado en CI (`.github/workflows/ci.yml`) pero no en el
  despliegue de Render (`render.yaml` no ejecuta `eval/`).
- Sin ediciones de `backend/`, `data/`, `eval/`, `frontend/` ni `render.yaml`.
  Sin lectura de `.env`.
