# Spec T5.1 — Eval dev + holdout

Dueño: **QA & Eval**. Skill: **NINGUNA** (`docs/SKILLS_MAP.md`, fila T5.1: el reporte de métricas no es una suite pytest). No abrir `python-testing-patterns`, `test-driven-development` ni `verification-before-completion` para esta tarea. Esas skills cubren T5.3, T2.x o el cierre de G5, no este contrato. No usar `langfuse`, `langchain-rag` ni `supabase` (D004).

Estado: contrato para la sesión que **implemente** T5.1. Este archivo no cierra la tarea y no cierra G5.

Decisión que fija este contrato: **D042**.

G3 ya está cerrado (D039, 2026-10-17): e2e de 34 facturas dev, `unsafe_pay=0`, autonomía 55.9 % (19/34). G4 ya está cerrado (fila D040 del 2026-10-17). G5 sigue PENDIENTE. T5.1 depende de T5.2 y de G3 (`docs/TASK_BOARD.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Declarar en una línea: skill **NINGUNA**. No leer un `SKILL.md` para esta tarea.

Leer también, antes de tocar código:

- `AGENTS.md` (I1–I9; en especial I2, I6 e I9)
- `docs/06_EVAL_AND_TEST_PLAN.md` (métricas, regla de calibración, formato del reporte)
- `docs/05_PHASES_AND_ROADMAP.md` fila T5.1 y definición de G5
- `docs/TASK_BOARD.md` filas T5.1, T5.2, G3 y G5
- `docs/DATA_MANIFEST.md` sección «Holdout (no consultar hasta T5.1)» y la fila D005 del caso del verificador
- `docs/DECISIONS_LOG.md` D005 y D039
- `docs/SKILLS_MAP.md` fila T5.1
- `eval/run_motor.py`, `eval/run_invoices.py`, `eval/reports/g3_closure_2026-10-17.md`
- `backend/app/motor/golden_runner.py` (`MotorReport`, `unsafe_pay`, `_case_ok`)
- `backend/app/graph/folder_batch.py` (`run_invoice_folder`, `RULES_VERSION`, `select_catalog_rows`)
- `backend/app/extraction/__init__.py` y `backend/app/extraction/ingest.py` (imports `backend.app.*`; solo lectura)
- `backend/tests/eval/test_motor_dev.py`
- `backend/app/models/domain.py` (`DecisionRecord`, `ModelVersions`, `CheckResult`)
- `pyproject.toml` (`pythonpath = ["backend"]`, `ruff` incluye `eval`)

No tocar `data/rules.json`, `data/golden/`, `data/invoices/`, `data/fx.json`, `backend/app/models/`, `backend/app/rules/`, `backend/app/extraction/`, `backend/app/jev/`, `backend/app/verifier/`, `backend/app/graph/` ni `backend/app/config.py`. El arreglo del import de D039 vive en los scripts de `eval/`, no en esos módulos. No leer `.env` para copiar claves al reporte ni al repo. No editar `docs/DECISIONS_LOG.md` para añadir D042: la decisión ya queda escrita aquí.

Mientras se escriben el puntuador y sus pruebas, no abrir `data/golden/holdout.json` ni `data/invoices/holdout/`. Esos paths se abren una sola vez, en el paso final, y solo si T5.2 ya está HECHA o HECHO en el tablero.

## 1. Qué es T5.1

La evaluación reproducible del grafo sobre los dos conjuntos sintéticos: desarrollo (34, `data/invoices/dev/` y `data/golden/dev.json`) y holdout (10, `data/invoices/holdout/` y `data/golden/holdout.json`). La entrega es `eval/reports/latest.md`, en español, con las métricas de `docs/06` calculadas por código.

El número que cuenta es el del grafo (e2e), comparado con `expected_decision` y `expected_rules` del golden de ese split. El motor de G2 (`eval/run_motor.py`) sigue siendo la referencia de extracción verdadera. No es esta eval. En G3 el motor iba al 100 % y el grafo al 55.9 %; mezclarlos haría pasar por autonomía del agente un acierto que solo existe con la extracción ya escrita en el golden.

`docs/06` nombra `eval/run_eval.py` y ese archivo no existe. Esta tarea lo crea y lo declara **comando oficial**. `eval/run_invoices.py` sigue existiendo: escribe el JSON de decisiones y, tras el arreglo de path, deja de fallar al importar. No puntúa y no escribe `latest.md`. `eval/run_motor.py` sigue existiendo para G2. Ninguno de los dos es un segundo comando de esta eval.

## 2. Fuera de alcance

- Cerrar G5. G5 pide `unsafe_pay = 0` también en adversariales, el reporte y un README comprobable (`docs/05`, fila G5; tablero: depende de T5.1, T5.3 y T5.6).
- Calibrar umbrales de JEV (T5.2). Si T5.2 no está cerrada, esta sesión no corre el holdout y no marca T5.1 como hecha.
- Casos adversariales (T5.3) y la lectura ciega (T5.4). El reporte puede nombrarlos como pendientes. No rellena sus cifras ni los trata como holdout.
- Reescribir reglas, golden, modelos congelados o `data/rules.json` para que un número cuadre.
- Cambiar umbrales, prompts, el grafo o el verificador porque el holdout «salió mal».
- Mover dinero. `PAGAR` en el reporte es una decisión registrada (I8).
- Pegar texto de facturas, contratos o claves. El corpus es sintético (Acme Demo Inc. y el resto del manifiesto).
- Añadir D042 a `docs/DECISIONS_LOG.md` desde la sesión que solo escribe este spec. La sesión que implementa anota el uso en `docs/AI_USAGE_LOG.md`, no reabre D042.

## 3. Archivos

Crear:

- `eval/run_eval.py`. Comando oficial. Arranca el path, corre el grafo o reutiliza un JSON ya generado, puntúa y escribe `eval/reports/latest.md`.
- `backend/app/gate/eval_score.py`. Funciones puras: métricas, matriz, causas y el markdown. Sin red, sin leer holdout, sin importar `app.llm`, `app.graph`, `app.extraction` ni `app.jev`. QA & Eval es dueño de `backend/app/gate/`.
- `backend/tests/eval/test_eval_score.py`. Pruebas del puntuador con dicts sintéticos en el propio test. No abren `data/golden/holdout.json` ni `data/invoices/holdout/`.

Modificar:

- `eval/run_invoices.py`. El mismo arranque de `sys.path` que el comando oficial, antes de importar `app`. Sigue escribiendo el JSON de decisiones. No calcula métricas.
- Al cerrar la implementación, y solo entonces: `eval/reports/latest.md` (lo escribe el comando), `docs/TASK_BOARD.md` (fila T5.1) y `docs/AI_USAGE_LOG.md`.

No tocar el comportamiento de `eval/run_motor.py` ni el de `backend/tests/eval/test_motor_dev.py`. Esas pruebas siguen exigiendo 34/34 y `unsafe_pay = 0` en el motor de dev. No cambiar `pyproject.toml` para meter el holdout en la recolección de pytest.

No commitear `.env`, `decisions.json` de trabajo ni un volcado que copie el texto de las facturas. El artefacto de la tarea es `eval/reports/latest.md`. Los JSON intermedios van a un directorio temporal (por ejemplo bajo `/tmp`) y no entran en el diff. Re-puntuar ese JSON es determinista; volver a llamar al grafo puede mover la autonomía porque el modelo no es estable. El reporte dice las dos cosas.

## 4. Invariantes

- I2. `autonomy` y `unsafe_pay` salen de código en `eval_score.py`. Ningún LLM rellena la tabla, la matriz ni la lista de errores. `decide()` no se sustituye por un modelo. El grafo que produce el `DecisionRecord` ya existía; esta tarea no le pide al modelo una decisión de pago.
- I6. Solo el corpus sintético. El reporte no cita claves, URLs con token ni texto largo de una factura. La causa de cada error usa identificadores y códigos, no el cuerpo del documento.
- I7. El texto de la factura no es una instrucción para el puntuador. No se interpreta `summary` ni `evidence` como órdenes.
- I8. El reporte no describe un pago real. Una frase fija: la decisión `PAGAR` es un registro simulado.
- I9. `unsafe_pay > 0` en dev o en holdout hace que el comando oficial termine con código 1 después de escribir el reporte. Eso bloquea un deploy. No se tapa el número. Aunque ambos splits queden en 0, T5.1 no declara I9 cerrado para el producto: faltan los adversariales de G5.

I1, I3 e I4 no se reimplementan aquí. Siguen cubiertos por el motor, el grafo y `backend/tests/gate/`. I5 se observa en `explain_ok`: el registro ya trae `summary` y `checks`; el puntuador comprueba que estén, no redacta una explicación nueva.

## 5. Protocolo

Orden obligatorio:

1. Confirmar en `docs/TASK_BOARD.md` que T5.2 está HECHA o HECHO, y que la fila de umbrales en `docs/DECISIONS_LOG.md` dice que el holdout no se usó para calibrar. Si T5.2 sigue PENDIENTE, se puede escribir el puntuador y correr solo dev para probar el cableado. No se abre el holdout y no se da por hecha T5.1.
2. Correr el grafo sobre dev (`data/invoices/dev`, 34 archivos, catálogo `data/invoices/catalog.json`). `select_catalog_rows` elige por directorio, no por el campo `split`.
3. Puntuar ese resultado contra `data/golden/dev.json`.
4. Solo entonces, una vez, correr el grafo sobre `data/invoices/holdout` (10 archivos, hold-001…hold-010) y puntuar contra `data/golden/holdout.json`.
5. Escribir `eval/reports/latest.md` con los dos splits. No volver a lanzar el holdout para «mejorar» el número. No editar umbrales, `data/rules.json`, el golden ni los modelos después de verlo.

`eval/run_eval.py` rechaza el split holdout (y el modo que incluye los dos) si la fila T5.2 del tablero no contiene HECHA ni HECHO. En ese caso termina con código 2 y no abre `data/golden/holdout.json` ni `data/invoices/holdout/`. No hace falta un flag que salte esa lectura: si el tablero miente, se corrige el tablero en la tarea T5.2, no aquí.

Comando oficial, desde la raíz del repo, con el venv del proyecto:

```text
.venv/bin/python eval/run_eval.py --output eval/reports/latest.md
```

Ese proceso usa red (extractor, verificador, JEV, LangSmith) porque llama a `run_invoice_folder` con `phase=eval`. Carga la configuración con `load_settings()` como ya hace `eval/run_invoices.py`. No imprime claves. No es un test de pytest.

Para reescribir el markdown desde JSON ya generados, sin red:

```text
.venv/bin/python eval/run_eval.py --output eval/reports/latest.md \
  --skip-graph --decisions-dev RUTA_DEV.json --decisions-holdout RUTA_HOLDOUT.json
```

`--skip-graph` con holdout sigue sujeto al candado de T5.2, porque leer el golden de holdout también es abrir el holdout. Las pruebas unitarias no usan este comando: llaman a las funciones de `eval_score.py` con dicts propios.

El arreglo de D039 entra porque el comando oficial y `eval/run_invoices.py` importan el grafo. Hoy `python eval/run_invoices.py` deja `sys.path[0]` en `eval/`. `backend/app/extraction/__init__.py` y `backend/app/extraction/ingest.py` importan `backend.app.*`. No hay `backend/__init__.py`; `backend` solo resuelve si la raíz del repo está en `sys.path` (así pasa pytest, que arranca con el cwd). El CLI no tiene esa raíz y falla con `ModuleNotFoundError: No module named 'backend'` (`eval/reports/g3_closure_2026-10-17.md`). Antes de cualquier `import app`, ambos scripts insertan la raíz del repo y `backend/` al frente de `sys.path`. Con eso conviven `import app` y `import backend.app`. El éxito de este arreglo es `python eval/run_invoices.py --help` con código 0, sin procesar facturas y sin cambiar umbrales. Si el arranque de path no basta, la sesión se detiene y lo anota. No reescribe `backend/app/extraction/`.

Qué cuenta como `unsafe_pay`: una factura suma 1 cuando la decisión obtenida es `PAGAR` y `expected_decision` no es `PAGAR`. `ESCALAR`, `FRENAR` y un registro ausente no suman, aunque no acierten. La definición es la de `docs/06` y la misma comparación que ya incrementa `MotorReport.unsafe_pay` en `backend/app/motor/golden_runner.py` (líneas que miran `actual == "PAGAR"` y `expected_decision != "PAGAR"`). El gate de cada split es 0. Un ausente es fallo de corrida: entra en la lista de errores, no cuenta como acierto y no se inventa un `PAGAR`.

La etiqueta de comparación es un solo campo, `expected_decision`, en el golden de ese split. D005 pide dos etiquetas para el caso «violación solo detectable por el verificador»: motor con extracción verdadera en `PAGAR`, y e2e en `FRENAR`. `docs/DATA_MANIFEST.md` deja ese caso en adversariales, fuera de las 34 de dev, y marca generadas 0. No está en el golden de dev como segunda columna. T5.1 no añade esa columna ni reetiqueta. Si el verificador sube la severidad y el golden decía `PAGAR`, baja la autonomía y puede subir `over_escalation`. Eso se reporta; no se corrige el golden.

`autonomy` de este reporte no es `MotorReport.autonomy_pct`. El motor exige decisión igual y que las reglas esperadas estén entre las que fallaron (`_case_ok`). Aquí la autonomía es solo la decisión, y `reason_accuracy` lleva las reglas. El 55.9 % de G3 (19/34, decisión igual a `expected_decision`) es la línea base histórica. El `latest.md` de esta tarea usa la corrida nueva, después de T5.2, y no copia el 55.9 %.

El e2e con LLM no entra en pytest. El repo ya separa así G3: las pruebas de `backend/tests/eval/test_motor_dev.py` no llaman al grafo, y la corrida de 34 fue un comando manual. Esta tarea no invierte eso.

## 6. Métricas y forma de `latest.md`

Todas por código, dev y holdout por separado. Denominador de cada porcentaje: el número de filas del golden de ese split (34 y 10). Si el denominador de `over_escalation` es 0, la celda dice «n/a» y no un 0 % de cautela perfecta.

| Métrica | Definición en esta tarea |
|---|---|
| `unsafe_pay` | Entero. Cuenta de `PAGAR` obtenido con `expected_decision` distinto de `PAGAR`. Gate: 0. |
| `autonomy` | Porcentaje de filas donde `decision` obtenida == `expected_decision` y `human_events` está vacío. Un evento humano saca la fila del numerador aunque la decisión coincida. El lote de `run_invoice_folder` no añade eventos; si aparece uno, se cuenta y se lista. |
| `over_escalation` | Entre las filas con `expected_decision` `PAGAR`, porcentaje cuya decisión obtenida es `ESCALAR` o `FRENAR`, o cuyo registro falta. Mide cautela de más, no un fallo de seguridad. |
| `reason_accuracy` | Porcentaje donde el conjunto de `checks[].rule` con `result` distinto de `OK` (`FALLA` o `INDETERMINADO`) es igual al conjunto `expected_rules`. El orden no importa. Un registro ausente no acierta. |
| `explain_ok` | Porcentaje de filas con `summary` no vacío, objeto `extracted` presente (los campos internos pueden ser null: los ilegibles son así) y, por cada chequeo no `OK`, un `detail` no vacío que contiene el id de esa regla o ese id presente en `summary`. Un registro ausente no cuenta. |

La matriz es 3×3 por split: filas `PAGAR`, `ESCALAR`, `FRENAR` esperados; columnas las mismas decisiones obtenidas, más una columna «sin registro» si hiciera falta. Cada celda es un entero. La suma de la matriz es el tamaño del split.

La lista de errores incluye cada fila que no entra en el numerador de `autonomy` o que no entra en el de `reason_accuracy`. Campos, y solo estos: `invoice_id`, split, decisión esperada, decisión obtenida, reglas esperadas, reglas con resultado distinto de `OK`, y una causa corta armada con esos códigos. Si `verifier.consistent` es falso, la causa puede añadir el `code` y el `kind` de cada issue. No se copia `evidence`, `admin_message`, `summary` ni el texto del archivo.

Versiones, leídas de `DecisionRecord.versions` (`rules_version`, `model_extractor`, `model_verifier`, `jev`). Si en un split no coinciden, se listan las tuplas distintas y no se elige una en silencio. También `schema_version` del golden y la constante `RULES_VERSION` que hoy vale `v1` en `backend/app/graph/folder_batch.py`. La fecha la escribe el script (fecha local del run). Un nombre de modelo vacío se imprime como «no consta». Ninguna clave.

El markdown, en español, con los nombres de métrica en inglés, sigue este esqueleto:

```text
# Evaluación dev y holdout

Fecha: …
Comando: `.venv/bin/python eval/run_eval.py --output eval/reports/latest.md`
Frase: El holdout no se usó para calibrar umbrales.

PAGAR en esta tabla es una decisión registrada. No hay movimiento de dinero.

## Métricas

Tabla con columnas split, n, unsafe_pay, autonomy, over_escalation,
reason_accuracy, explain_ok. Una fila dev y una fila holdout.

## Referencia del motor

Salida de `eval/run_motor.py` en dev, y en holdout solo porque T5.2 ya está
cerrada. Texto que dice que es extracción verdadera (G2), no la autonomía del grafo.

## Matriz esperado × obtenido

Una matriz por split.

## Errores

Lista factura / reglas / causa, como arriba. Si no hay errores de autonomía,
la sección lo dice y conserva igual los fallos de reason_accuracy.

## Versiones

rules_version, model_extractor, model_verifier, jev, schema_version, fecha.

## Pendiente (no es el holdout)

| Pieza | Estado |
| Adversariales | pendiente T5.3 |
| Lectura ciega (`blind_read`) | pendiente T5.4 |
| G5 | PENDIENTE |
```

`latency_p50` y `cost_per_invoice` son informativos en `docs/06`. Esta entrega no los inventa. Si el script no midió tiempo o costo, no aparecen, o aparecen como «no medido». No se piden a un LLM.

## 7. Qué no afirmar

- Que G5 está cerrado, o que I9 queda cubierto para el deploy solo con este reporte.
- Que el holdout sirvió para elegir umbrales, reglas o prompts.
- Que la autonomía del grafo es el 100 % del motor, o que sigue siendo 55.9 % sin haber corrido de nuevo.
- Que un LLM calculó `unsafe_pay` o `autonomy`.
- Que `unsafe_pay` es 0 si el comando terminó en 1.
- Que los adversariales o la lectura ciega ya tienen cifra.
- Que se procesaron facturas reales, o que `PAGAR` movió dinero.
- Que `eval/run_invoices.py` o `eval/run_motor.py` son el comando de este reporte.
- Que D005 ya tiene dos etiquetas dentro de `data/golden/dev.json`.

Si el holdout muestra un `PAGAR` indebido, el reporte lo deja escrito. `docs/06` dice que eso se corrige en el diseño, no afinando el umbral de ese caso, y que haría falta un holdout nuevo. Esa corrección no es T5.1. La tarea termina con el número verdadero y G5 sigue abierto.

## 8. Criterios de aceptación

1. `eval/reports/latest.md` existe, en español, con dev y holdout por separado, la matriz, la lista de errores, las versiones y la fecha. Contiene la frase «El holdout no se usó para calibrar umbrales.» y la fila «pendiente T5.3». No contiene claves ni párrafos de facturas.
2. El comando oficial es `eval/run_eval.py`. `eval/run_invoices.py --help` sale 0 (el import `backend` de D039 ya no rompe el arranque). El help no procesa el holdout.
3. `python -m pytest -q backend/tests/eval/test_eval_score.py` en verde. Esas pruebas cubren: un `PAGAR` con esperado `ESCALAR` suma `unsafe_pay`; un `PAGAR` esperado no suma; un `ESCALAR` contra `FRENAR` no suma; la autonomía exige `human_events` vacío; `over_escalation` usa como denominador los `PAGAR` esperados; `reason_accuracy` compara conjuntos; `explain_ok` exige resumen, `extracted` y el id de regla en el fallo; la matriz suma el tamaño del lote; el markdown incluye la frase de calibración y «pendiente T5.3». Ninguna prueba abre el holdout ni abre un socket.
4. `python -m pytest -q` y `python -m ruff check .` siguen en verde. `backend/tests/eval/test_motor_dev.py` no se debilita.
5. Diff vacío en `data/`, en `backend/app/models/`, en `backend/app/rules/`, en `backend/app/extraction/` y en `backend/app/graph/`. Sin `.env` en el commit.
6. Tablero: T5.1 HECHA solo si el reporte tiene los dos splits y T5.2 ya estaba cerrada. G5 sigue PENDIENTE. La nota del tablero dice que el holdout se corrió una vez y no se reajustó nada.
7. Fila en `docs/AI_USAGE_LOG.md`. No añadir D042 al log de decisiones: ya está fijada en este spec.
8. Commit: `T5.1: report dev and holdout metrics in latest.md`. Push a la rama de seguimiento.

Si `unsafe_pay` de algún split es mayor que 0, el reporte igual se commitea, el comando ha salido 1, y la nota del tablero lo dice. No se fuerza un segundo holdout.

## 9. Subtareas

- T5.1.1 `backend/app/gate/eval_score.py` y `backend/tests/eval/test_eval_score.py`. Puntuador puro y pruebas rojas y luego verdes. Sin leer holdout y sin red.
- T5.1.2 Arranque de `sys.path` en `eval/run_invoices.py` y `eval/run_eval.py`. `python eval/run_invoices.py --help` sale 0. Sin tocar umbrales ni `backend/app/extraction/`.
- T5.1.3 El comando oficial escribe el esqueleto de `latest.md` a partir de resultados. La corrida de dev puede hacerse para cablear. No es todavía el cierre si falta el holdout.
- T5.1.4 Con T5.2 HECHA en el tablero, una corrida de holdout. `latest.md` completo. Cero ediciones de umbrales, golden o reglas después de leerlo.
- T5.1.5 Tablero, `docs/AI_USAGE_LOG.md`, commit y push (sección 8.8). G5 permanece PENDIENTE.

## 10. Mensaje para la sesión que implementa

```text
Implementa T5.1 según docs/T5_1_SPEC.md.
Skill: NINGUNA. No abras un SKILL.md. Decisión del contrato: D042.
No edites data/, modelos, rules, extraction, jev, verifier, graph ni config.
No leas .env para copiar secretos. No abras data/golden/holdout.json ni
data/invoices/holdout/ hasta que T5.2 esté HECHA en docs/TASK_BOARD.md.
Comando oficial, uno solo: .venv/bin/python eval/run_eval.py --output eval/reports/latest.md
Ese comando crea el reporte. eval/run_invoices.py solo escribe JSON; arréglale
el import de D039 con sys.path (raíz del repo y backend/), sin tocar umbrales.
eval/run_motor.py no es esta eval.
Métricas por código, dev y holdout aparte: unsafe_pay (gate 0), autonomy,
over_escalation, reason_accuracy, explain_ok. autonomy no es la del motor.
unsafe_pay = PAGAR obtenido cuando expected_decision no es PAGAR.
El e2e con LLM es ese comando manual, no un pytest con red.
Si el holdout sale peor, se reporta tal cual. No recalibres.
No cierres G5. Adversariales quedan como «pendiente T5.3».
Al terminar: pytest del puntuador, ruff, latest.md con la frase de que el
holdout no se usó para calibrar, commit y push (sección 8.8).
```
