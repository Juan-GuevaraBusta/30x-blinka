# Spec T5.2 — Calibrar umbrales JEV solo con dev

Dueño: **QA & Eval**. Skill: **NINGUNA** (`docs/SKILLS_MAP.md`: calibrar es la regla de `docs/06`, no una skill). Depende de **G3**, cerrado en D039, y de **T5.7** (D055), el arreglo del import de `backend` en `eval/run_invoices.py`. T5.1 corre el holdout después y no reajusta umbrales. Esta tarea no lo abre.

Estado: contrato para la sesión que **implemente** T5.2. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D043**. La fila de umbrales finales es otra, con el siguiente ID libre del log. No se reutiliza D043.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar números:

- `AGENTS.md` (I1 nunca PAGAR si un chequeo falla o está indeterminado; I2 el LLM no decide y `decide()` es pura; I3 fail-closed; I6 solo datos sintéticos; I9 `unsafe_pay > 0` bloquea el despliegue)
- `docs/06_EVAL_AND_TEST_PLAN.md` sección «Regla de calibración»
- `docs/PARAMETERS.md` tabla «Umbrales JEV» (siguen PROPUESTO)
- `docs/04_RULES_AND_DECISION_SPEC.md` §1, §3 (R09, R13) y §7
- `docs/05_PHASES_AND_ROADMAP.md` fila T5.2
- `docs/TASK_BOARD.md` filas T5.2 y T5.7, y nota de G3
- `docs/DECISIONS_LOG.md` D007, D009, D017, D021, D039, D055
- `docs/T5_7_SPEC.md` (el arreglo del import de `backend`; T5.2 depende de esa tarea)
- `eval/reports/g3_closure_2026-10-17.md` (línea base; no reescribir el informe)
- `data/rules.json` objeto `jev_thresholds`
- `backend/app/models/rules_config.py` (`JevThresholds`, `load_rules_config`)
- `backend/app/rules/checks.py` (`check_r09`, `check_r13`)
- `backend/app/gate/invariants.py` (`jev_allows_pagar`)
- `backend/app/graph/folder_batch.py` (`build_runtime_graph_deps` carga `data/rules.json`)
- `backend/app/jev/run.py` (`ids_below_threshold`; no guarda números)
- `backend/tests/test_rules_config.py` (`EXPECTED_JEV`)
- `backend/tests/test_jev_run.py` y `backend/tests/rules/test_rules_r01_r13.py` (cargan el `rules.json` vivo)

Declarar en una línea: skill NINGUNA. No leer `langgraph-fundamentals`, `langchain-rag`, `langfuse` ni `python-testing-patterns` para esta tarea.

No abrir `data/golden/holdout.json` ni `data/invoices/holdout/`. No leer `.env` para copiar claves al log, al spec o al commit.

G3 está cerrado. G5 sigue PENDIENTE. Esta tarea no lo cierra.

## 1. Qué es T5.2

Ajustar los seis umbrales de probabilidad JEV que ya viven en `data/rules.json`, midiéndolos solo contra el set de desarrollo. El objetivo es la autonomía del e2e (decisión obtenida == `expected_decision` en `data/golden/dev.json`). La seguridad no se baja para subir esa cifra: `unsafe_pay` sigue en 0.

Línea base a citar, la de G3 (D039), y ninguna otra: autonomía **55.9%** (19/34), `unsafe_pay = 0`. De las 15 facturas con decisión distinta a la esperada, 11 son `PAGAR`→`ESCALAR` (sobre-escalado) y 4 son `FRENAR`→`ESCALAR` (severidad insuficiente, no sobre-escalado); esta tarea no llama a las 15 por igual «sobre-escalado». El motor de G2 (100 % con extracción verdadera) no es esta medida: `eval/run_motor.py` inyecta señales con probabilidad 0.99 (`_perfect_jev`) y no ve las probabilidades vivas de JEV.

| Pieza | Qué hace |
|---|---|
| Knob | Los seis floats de `jev_thresholds` en `data/rules.json` |
| Medición | E2E del grafo sobre `data/invoices/dev` (34 facturas), comparado con `data/golden/dev.json` |
| Antes | Misma corrida con los números actuales, antes de moverlos |
| Después | La misma corrida con el candidato aceptado |
| Entrega | Una fila **nueva** en `docs/DECISIONS_LOG.md` con los seis números finales y la frase «El holdout no se usó.», y `eval/reports/t5_2_calibration.md` con la tabla por factura y el antes/después |

`docs/05` escribe en la misma línea «reportar holdout sin ajustar». El tablero parte el trabajo: T5.2 calibra en dev; T5.1 reporta el holdout una sola vez y no reajusta. Aquí se calibra. El holdout no se reporta.

## 2. Fuera de alcance

- Abrir, citar o contar el holdout. Si más tarde el holdout muestra un PAGAR indebido, `docs/06` manda corregir el diseño, no el umbral de ese caso, y generar un holdout nuevo. Eso es nota para después. No es trabajo de T5.2.
- Arreglar el import de `eval/run_invoices.py` (`ModuleNotFoundError: No module named 'backend'`, G3, exit 1). Es de T5.7 (D055). Este spec no redefine el comando ni parchea `backend/app/extraction/__init__.py`.
- Crear `eval/run_eval.py` o `eval/reports/latest.md` (T5.1).
- Cerrar G5. Reabrir G3. Desplegar. Mover dinero (I8).
- Tocar `human_approval_threshold` (3000, D009), `limits`, `on_fail`, beneficiarios, presupuestos o `fx.json`.
- Añadir un umbral a J5. El modelo lo prohíbe (`extra=forbid`; «J5 is not a payment threshold»).
- Editar modelos congelados (`backend/app/models/`), `backend/openapi.json`, `frontend/`, `docs/04`, el golden, o las facturas, para forzar una métrica.
- Editar `backend/app/config.py`. No hay umbrales ahí. D007: API no lo edita; el dueño es Agent Graph. Esta tarea no le pide un campo nuevo.
- Editar `backend/app/jev/`, `backend/app/rules/`, `backend/app/gate/` o `backend/app/graph/`. Si la autonomía solo sube cambiando ese código, **parar** y pedir al dueño. El knob de esta tarea es el JSON.
- Usar `langfuse` o una base vectorial (D004).
- Calibrar mirando un PAGAR indebido para «hacer que esa factura pague».

## 3. Archivos

El grafo lee las reglas en disco: `build_runtime_graph_deps` llama `load_rules_config(data_root / "data" / "rules.json")` y pasa `deps.rules.jev_thresholds` al `GateInput`. No hay un segundo archivo de umbrales. `backend/app/config.py` no los tiene. `ids_below_threshold` no copia números; hace `getattr(thresholds, jev_id)`.

Knob vivo, objeto `jev_thresholds` de `data/rules.json`, clase `JevThresholds`:

| Campo | Valor hoy | Quién lo lee para decidir |
|---|---|---|
| `J1` | 0.9 | R09 y `jev_allows_pagar` (obligatoria para PAGAR) |
| `J2` | 0.9 | Igual que J1 |
| `J3` | 0.85 | Igual que J1 |
| `J4` | 0.85 | Igual que J1 |
| `J6` | 0.85 | Solo el gate, y solo si la señal viene en el registro. R09 no la mira. R06 no la mira |
| `J7` | 0.5 | R13, si la señal está, y el gate si la señal está |

J5 no es un campo. Una señal ausente de J1–J4 deja R09 en `INDETERMINADO` (I3); no se rellena con una probabilidad inventada. La comparación real es estricta: `probability < umbral` falla; igual al umbral pasa.

`decide()` sigue siendo función pura de los chequeos (I2). JEV no emite `PAGAR`. El gate puede convertir un PAGAR propuesto en ESCALAR si `jev_allows_pagar` es falso (I1). Para un noul, `answer` es `True` solo cuando la probabilidad es ≥ 0.5 (D017). Bajar un umbral a 0.5 o menos no fabrica un PAGAR: el gate sigue exigiendo `answer is True`.

Modificar, y solo esto:

- `data/rules.json`: los seis floats de `jev_thresholds`. El resto del documento queda igual. `data/` es de Spec & Data; este contrato autoriza ese único cambio y pide anotarlo en `docs/AI_USAGE_LOG.md`.
- `backend/tests/test_rules_config.py`: la constante `EXPECTED_JEV`, para que el test del archivo vivo coincida con los seis números elegidos. El resto de asserts de ese archivo (5000, 3000, `on_fail`, ausencia de J5) no se tocan.
- `docs/PARAMETERS.md`: las seis filas J1, J2, J3, J4, J6 y J7 (valor y estado). J5 sigue «Sin umbral». El resto de la tabla no se toca. Misma autorización de archivo ajeno, misma nota en el log de uso.
- Al cerrar: una fila nueva en `docs/DECISIONS_LOG.md`, la fila T5.2 de `docs/TASK_BOARD.md`, y una línea en `docs/AI_USAGE_LOG.md`.

Crear:

- `eval/reports/t5_2_calibration.md`. La tabla por factura del §5 paso 4 (las facturas con decisión distinta a la esperada, con la regla o señal JEV causante) y la tabla antes/después de cada candidato aceptado o descartado. Es evidencia de desarrollo, no se confunde con `eval/reports/latest.md` (T5.1) ni con el holdout.

No tocar `backend/app/`, `frontend/`, `backend/openapi.json`, `data/golden/`, `data/invoices/`, `eval/run_invoices.py`. Un `SqlStore` que ya tenga fila de reglas no se actualiza solo (el seed no pisa un PUT). Esta tarea no hace PUT al API público ni cambia el seed.

Los tests que cargan `data/rules.json` y afirman «0.5 queda bajo J1 y bajo J2» y «0.1 queda bajo J6 y bajo J7» no se reescriben. Un candidato que los ponga en rojo se descarta y se restauran los números anteriores. En la práctica: J1 y J2 siguen estrictamente por encima de 0.5; J6 y J7 siguen estrictamente por encima de 0.1; los seis siguen en (0, 1] y, para no romper las señales de prueba a 0.99, en (0, 0.99].

## 4. Invariantes

- I1. Un candidato con algún PAGAR cuyo `expected_decision` no es PAGAR se tira. No se baja el umbral para que esa factura pase. No se edita el golden.
- I2. No se cambia `decide()`, ni se pide al modelo una decisión, ni se explica el pago con texto del LLM. Los umbrales solo cambian cuándo una probabilidad cuenta como «bajo umbral» para R09, R13 y el gate.
- I3. Error, timeout, señal ausente de J1–J4, campo obligatorio ausente o probabilidad por debajo del umbral siguen en ESCALAR. No se inventan señales para completar un PAGAR.
- I6. Solo `data/invoices/dev` y `data/golden/dev.json`. Empresa de ejemplo: Acme Demo Inc. Sin claves en el log ni en el commit.
- I9. La corrida de después tiene `unsafe_pay = 0`. Esta tarea no despliega y no afirma que el holdout cumpla I9. Eso es G5.

Si el antes fresco ya trae `unsafe_pay > 0`, **parar**. No se calibra un pago indebido. Se anota y se deja T5.2 abierta.

## 5. Protocolo de calibración

Cada corrida es el e2e del grafo sobre las 34 facturas de desarrollo, con las reglas leídas de `data/rules.json`. El conteo usa la misma definición que G3 y que `MotorReport`: `unsafe_pay` es el número de facturas con decisión `PAGAR` cuando `expected_decision` no es `PAGAR`; la autonomía es el porcentaje de facturas cuya decisión coincide con la esperada (19/34 = 55.9 % en el cierre de G3). El conteo se hace en la sesión sobre el JSON que escribió el entrypoint y sobre `data/golden/dev.json`. No se commitea un scorer nuevo.

Entrypoint: `python eval/run_invoices.py`. El default de carpeta ya es `data/invoices/dev`. No pasar otra carpeta. No pasar `data/invoices/holdout`.

G3 registró ese comando con exit 1 por el import de `backend`. T5.2 requiere T5.7 (D055) HECHA; si `python eval/run_invoices.py` sale distinto de 0, **parar**, sin describir aquí un comando distinto y sin parchear el import. Mientras ese import siga roto, T5.2 no calibra a ciegas y no sustituye la medida por `eval/run_motor.py`.

`eval/run_invoices.py` imprime `processed` y la ruta de salida. No imprime `unsafe_pay`. El conteo del párrafo anterior es parte de la sesión; el archivo de salida de la corrida no se commitea si cae en la raíz del repo (`decisions.json`).

Pasos:

1. Citar la línea base de G3: autonomía 55.9 % (19/34), `unsafe_pay = 0`. No sustituirla por otra cifra del motor.
2. Correr el antes, con los seis números actuales, sobre dev. Anotar autonomía y `unsafe_pay` de **esta** sesión. Si difieren de 55.9 % (19/34), se escriben los dos: el de G3 y el de esta sesión. El e2e con LLM no es determinista; no se promedia una cifra inventada.
3. Si el antes tiene `unsafe_pay > 0`, parar (§4).
4. Leer los registros del antes y construir, antes de proponer ningún umbral, una tabla por factura con cada una de las que tiene decisión distinta a la esperada: `invoice_id`, decisión esperada, decisión obtenida, y la regla o señal JEV que causa el `ESCALAR` (R09 por probabilidad bajo J1–J4, R13 por probabilidad bajo J7, el gate por J6 o J7, o «no es JEV» si la causa es otra). Esa tabla se escribe en `eval/reports/t5_2_calibration.md`. Un umbral solo es candidato para una fila si la causa es una probabilidad JEV bajo el umbral y la fila es `expected_decision` PAGAR que salió ESCALAR. Un ESCALAR por R02, R04, R06, campo ausente, señal J1–J4 ausente, `error_tecnico` o el verificador queda en la tabla marcado «no es JEV» y no se arregla moviendo `jev_thresholds`.
5. Proponer el menor cambio que cubra esas probabilidades ya observadas: bajar solo el campo que la tabla señala, dentro de los límites del §3. Un campo por candidato. No hay búsqueda en grilla. No se sube un umbral para «ser más estricto» si eso baja la autonomía sin un PAGAR indebido que corregir: la línea base ya tiene `unsafe_pay = 0`.
6. Recalcular sin red, sobre el JSON del antes, qué facturas cambiarían con el candidato: para cada fila de la tabla del paso 4 marcada como candidata, leer la probabilidad JEV ya guardada en `jev_signals` de ese JSON y aplicar el candidato con la misma comparación estricta del código vivo (`probability < umbral`). Esta repetición es local y determinista, no llama al grafo ni a la red, y predice qué facturas pasarían de incorrectas a correctas.
7. Solo si esa predicción offline muestra una mejora sin ningún nuevo `PAGAR` indebido, correr **una** vez el e2e de confirmación sobre las mismas 34 de dev con el candidato ya escrito en `data/rules.json`. Aceptar el candidato solo si: `unsafe_pay` es 0 en esa corrida; cada factura que pasó de incorrecta a correcta en la corrida de confirmación tenía, en el JSON del antes, una probabilidad observada entre el umbral viejo y el umbral nuevo (si no, la mejora no se explica por el cambio de umbral y el candidato se descarta); y no aparece ningún `PAGAR` indebido nuevo. Si aparece un PAGAR indebido, restaurar los seis números previos. No editar la etiqueta, no bajar más para que esa factura pague, no abrir el holdout para comprobar.
8. Repetir 4–7 solo mientras la tabla del antes siga señalando otro campo y el candidato anterior haya sido aceptado. Si ningún candidato aceptable sube la autonomía, los números finales son los del inicio (siguen válidos). Igual se escribe la fila del log y la tabla de `eval/reports/t5_2_calibration.md`.
9. Actualizar `EXPECTED_JEV` y las seis filas de `docs/PARAMETERS.md` a esos números finales. Pytest del loader y de `backend/tests/test_jev_run.py` y `backend/tests/rules/test_rules_r01_r13.py` en verde. Si un test de «0.5 bajo umbral» o «0.1 bajo umbral» falla, el candidato no vale: restaurar y no reescribir el test.

La frase de `docs/06` queda aquí como nota, no como paso: si más adelante el holdout muestra un PAGAR indebido, se corrige el diseño, no el umbral de ese caso, y se genera un holdout nuevo. T5.1 no reajusta.

## 6. Qué anotar en la fila del log

Una fila nueva en `docs/DECISIONS_LOG.md`. ID = el número D más alto que ya exista en el log, más uno, en el momento de implementar. Nunca se rellena un hueco de un ID saltado o retirado. **No es D043.**

Columnas, en el estilo del archivo:

- Decisión: los seis números finales (`J1` … `J7`, sin J5), si quedaron iguales a los PROPUESTO o cuáles se movieron, la autonomía y el `unsafe_pay` del antes y del después de esta sesión, la cita de la línea base G3 (55.9 %, 19/34, `unsafe_pay = 0`), y la frase exacta **«El holdout no se usó.»**
- Alternativas: bajar umbrales hasta pagar un caso que el golden no etiqueta PAGAR; calibrar con el holdout; meter los números en `config.py`.
- Motivo: I1 e I3. La autonomía puede subir. Un PAGAR indebido en dev no se calibra.
- Impacto: `data/rules.json`, `docs/PARAMETERS.md`, `docs/T5_2_SPEC.md`, `eval/reports/t5_2_calibration.md`, T5.1 (corre el holdout después, sin reajustar).
- Revierte a: volver a los seis valores PROPUESTO de esta tabla si un candidato aceptado se demuestra inseguro en dev.

En `docs/TASK_BOARD.md`, fila T5.2: HECHA, con la evidencia de la fila nueva y la frase de que el holdout no se usó. T5.1, T5.3 y G5 siguen PENDIENTE.

En `docs/AI_USAGE_LOG.md`, una línea: skill NINGUNA; que se tocaron `data/rules.json` y las seis filas JEV de `docs/PARAMETERS.md` (archivos de Spec & Data, autorizados por este contrato); que no se abrió el holdout.

En `docs/PARAMETERS.md`, estado de esas seis filas: **CALIBRADO EN DEV (T5.2)**. J5 no cambia.

## 7. Qué no afirmar

- Que el holdout se midió, se ajustó o salió con `unsafe_pay = 0`.
- Que G5 está cerrado, o que I9 ya cubre el holdout.
- Una autonomía distinta de la medida de esta sesión, o una línea base de G3 distinta de 55.9 % (19/34) con `unsafe_pay = 0`.
- Que el motor al 100 % demuestra estos umbrales. Esa corrida no usa las probabilidades vivas.
- Que el LLM decidió el pago, o que J5 tiene umbral.
- Que `backend/app/config.py` guarda estos números, o que se creó otro archivo de configuración.
- Que el import de `eval/run_invoices.py` quedó arreglado aquí.
- Que un PUT en el API público o el Postgres de Render ya tiene los números nuevos.
- Que se movió dinero.
- Que se reescribieron modelos, OpenAPI, el golden o `decide()`.

## 8. Criterios de aceptación

1. Los seis números finales están en `data/rules.json` y coinciden con `EXPECTED_JEV` y con las seis filas de `docs/PARAMETERS.md`. Ningún otro campo de `rules.json` cambió.
2. El antes y la corrida de confirmación de cada candidato aceptado están anotados en `eval/reports/t5_2_calibration.md`, con la tabla por factura del §5 paso 4. En la corrida de confirmación, `unsafe_pay = 0`, y cada factura que pasó de incorrecta a correcta tenía una probabilidad observada entre el umbral viejo y el umbral nuevo. La fila del log cita 55.9 % (19/34) y `unsafe_pay = 0` como línea base de G3, y contiene la frase «El holdout no se usó.»
3. Diff vacío en `data/golden/`, `data/invoices/holdout/`, `data/golden/holdout.json`, `backend/app/`, `backend/openapi.json`, `frontend/` y `.env`.
4. `python -m pytest -q backend/tests/test_rules_config.py backend/tests/test_jev_run.py backend/tests/rules/test_rules_r01_r13.py` en verde. `python -m ruff check .` en verde. No hace falta la suite entera si esos módulos cubren el JSON vivo; si se corre `pytest -q` y algo ajeno falla, se anota y no se parchea fuera de este contrato.
5. El ID de la fila nueva no es D043. D043 sigue siendo este spec.
6. Tablero: T5.2 HECHA. T5.1 y G5 siguen PENDIENTE.
7. `git status` sin `.env`, sin `decisions.json` de la corrida, sin secretos, sin archivos del holdout.
8. Commit: `T5.2: calibrate JEV thresholds on the dev set`. Si los seis números no se movieron porque ningún candidato seguro subió la autonomía, el mismo mensaje vale: el cuerpo del commit lo dice. Push a la rama de seguimiento.

## 9. Subtareas

- T5.2.1 Antes en dev, con el entrypoint del §5. Anotar autonomía y `unsafe_pay`, y construir la tabla por factura en `eval/reports/t5_2_calibration.md`. Si el comando documentado sigue en exit 1 por el import de `backend`, requiere T5.7 (D055) HECHA; parar si `python eval/run_invoices.py` sale distinto de 0. Si el antes trae un PAGAR indebido, parar.
- T5.2.2 Candidatos solo sobre `jev_thresholds`, un campo cada vez, a partir de la tabla. Recalcular sin red sobre el JSON del antes qué facturas cambiarían, y solo si mejora sin PAGAR indebido, correr una vez la confirmación. Descartar el candidato si la corrida de confirmación deja `unsafe_pay > 0` o si una factura mejorada no tenía la probabilidad observada entre el umbral viejo y el nuevo.
- T5.2.3 Escribir los números finales en `data/rules.json`, `EXPECTED_JEV` y las seis filas de `docs/PARAMETERS.md`. Pytest de esos tres módulos en verde.
- T5.2.4 Fila nueva del log (ID = máximo existente + 1, no D043), `eval/reports/t5_2_calibration.md` con la tabla final, tablero, `docs/AI_USAGE_LOG.md`, commit y push.

## 10. Mensaje para la sesión que implementa

```text
Implementa T5.2 según docs/T5_2_SPEC.md.
Skill: NINGUNA. No uses langfuse ni langchain-rag.
D043 es este spec. La fila de umbrales es un ID nuevo (el D más alto
existente + 1, nunca un hueco), no D043, e incluye la frase «El holdout no se usó.»
El knob es data/rules.json → jev_thresholds (J1, J2, J3, J4, J6, J7).
No hay umbrales en config.py. No añadas J5. No edites modelos, OpenAPI,
frontend, golden, jev/, rules/ ni gate/.
Solo dev (data/golden/dev.json y data/invoices/dev). No abras el holdout.
Línea base a citar: G3 autonomía 55.9% (19/34), unsafe_pay=0; de las 15
facturas distintas al golden, 11 son PAGAR→ESCALAR y 4 son FRENAR→ESCALAR
(no llames a las 15 "sobre-escalado").
Antes de proponer un umbral, construye en eval/reports/t5_2_calibration.md
la tabla por factura (regla o señal JEV causante) de esas facturas.
Para cada candidato: recalcula sin red sobre el JSON del antes qué
facturas cambiarían; solo si mejora sin PAGAR indebido, corre una vez la
confirmación. Acepta solo si unsafe_pay sigue en 0 y cada factura mejorada
tenía su probabilidad observada entre el umbral viejo y el nuevo.
Si aparece un PAGAR indebido, restaura el umbral; no calibres para pagarlo.
Si python eval/run_invoices.py sigue fallando el import de backend,
requiere T5.7 (D055) HECHA y para. No redefinas el comando.
No uses run_motor.py como medida: inyecta probabilidad 0.99.
Al terminar: fila nueva en el log, commit y push (sección 8.8).
```
