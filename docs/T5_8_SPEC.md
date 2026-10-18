# Spec T5.8 — Serializar la decisión dependiente del ledger para que el límite por periodo se cumpla

Dueño: **API**. Carril: B. Revisa: **Rules Engine** (dueño de `backend/app/rules/ledger_queries.py` y de R03/R07; no implementa, solo revisa el diff antes del commit). Skill de dominio: NINGUNA; proceso: `python-testing-patterns` PARCIAL, `test-driven-development`.

Depende de: ninguna tarea previa bloquea el inicio. **G5 depende también de esta tarea** (además de T5.1, T5.3 y T5.6): «cero pagos fuera de reglas» es descalificante y esta race lo viola.

Estado: contrato para la sesión que **implemente** T5.8. Este archivo no corre el fix ni cierra la tarea.

Decisión que fija este contrato: **D055** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio NINGUNA: no inventar una. Declarar `python-testing-patterns` (PARCIAL) y leerla antes del test de concurrencia.

Lecturas:

- `backend/app/api/production_processor.py` `process_upload` (línea 110): línea 111 lee `prior = settled_ledger_from_store(config.store)` (todo el ledger `PAGAR` ya persistido) y pasa esa foto a `run_invoice`, que evalúa R03/R07 contra ella.
- `backend/app/api/app.py` `post_invoice` (líneas 73–108): línea 102 `record = processor(upload)` (decide con la foto de arriba) y línea 106 `return store.add_decision(record)` (persiste). Entre esas dos líneas no hay bloqueo.
- `backend/app/persistence/sql_store.py` `add_decision` (líneas 47–67): el `try/except IntegrityError` solo protege contra el mismo `invoice_id` repetido (duplicado exacto). No hay ninguna comprobación contra el total del periodo en el momento de escribir.
- `backend/app/rules/ledger_queries.py` `period_paid_total` (líneas 27–33) y `department_spent_for_budget` (líneas 40–59): ambas leen una tupla de `LedgerEntry` ya materializada; no vuelven a consultar nada al momento de persistir.
- `docs/G4_SPEC.md` y D040 (contexto de cómo `run_invoice` llegó a producción).

## 1. El problema

Dos facturas, cada una por debajo del límite de periodo (`limits.per_period`, `data/rules.json`), llegan casi al mismo tiempo. Ambas llaman `process_upload`: ambas leen el mismo `prior` (ninguna ve a la otra, porque ninguna se ha persistido todavía), ambas evalúan R03/R07 con esa foto y ambas obtienen `PAGAR`. Las dos llamadas a `store.add_decision` tienen éxito porque cada una tiene un `invoice_id` distinto — el único chequeo de `IntegrityError` no las frena. El total de las dos juntas puede superar `limits.per_period.amount`, con ambas registradas como `PAGAR`. Eso es exactamente lo que `AGENTS.md` llama «cero pagos fuera de reglas»: descalificante.

## 2. Alcance (tamaño de hackathon)

Serializar la sección crítica (lectura del ledger + decisión + persistencia del `PAGAR`) con un único candado a nivel de proceso:

- Un `threading.Lock()` a nivel de módulo (o inyectado, para poder testear con dos hilos reales) que envuelva, como mínimo, desde `prior = settled_ledger_from_store(...)` hasta el `store.add_decision(record)` correspondiente. El candado puede vivir en `production_processor.py` si se mueve el `add_decision` dentro de `process_upload` (cambiando su firma para que reciba `store` y persista antes de devolver), o puede vivir en `app.py` envolviendo las líneas 102 y 106 juntas. Elegir uno; documentar la elección en el diff.
- El resto de rutas (`GET /decisions`, `GET /rules`, etc.) no necesita el candado: solo la ruta que puede terminar en `PAGAR` con impacto en el ledger (`POST /invoices`).
- Documentar en `README.md` (sección de despliegue, la que ya dejó T4.9) una frase: el proceso está pensado para **un solo worker** (`uvicorn` sin `--workers`); el candado de proceso no sirve entre procesos ni entre réplicas.
- Prueba de concurrencia: dos hilos (`threading.Thread`, no `asyncio` fingido) que llaman `process_upload` (o el endpoint vía `TestClient`, si es más simple) con dos facturas que juntas superan `limits.per_period.amount` pero cada una sola no lo supera. Usar un doble de `GraphDeps`/`run_invoice` que fuerce `PAGAR` cuando el ledger visto está bajo el límite — no depende de LLM real. Verificar: como máximo una queda `PAGAR`; la otra queda `ESCALAR` o `FRENAR` según `on_fail.R03`/`on_fail.R07` de `data/rules.json`. Sin el candado, este test debe poder reproducir el fallo (dejarlo documentado, no como test permanente en rojo).

## 3. Fuera de alcance

- Lock de fila en la base (`SELECT ... FOR UPDATE`) o nivel de aislamiento `SERIALIZABLE` en Postgres: es la alternativa de producción, se anota como nota al pie, no se implementa. Un comentario en el código y una línea en este spec bastan.
- Cambiar R03/R07, `decide()`, el grafo o cualquier regla de negocio.
- Añadir una cola, un worker pool o Redis.
- Tocar `render.yaml` salvo para documentar, si aplica, que el servicio sigue en un solo worker (sin añadir `--workers` ni cambiar el plan).
- Resolver T5.9 (auth) o T5.10 (hash chain); son specs distintos aunque toquen archivos cercanos.

## 4. Criterios de aceptación

1. Prueba de concurrencia nueva (dos hilos reales, facturas que juntas exceden el límite de periodo) pasa: a lo sumo un `PAGAR`.
2. Con el candado presente, repetir la prueba 1 no es intermitente: correrla al menos 20 veces en el mismo `pytest -q` (parametrizar o loop dentro del test) sin fallos.
3. `cd backend && python -m pytest -q` — 0 failed, total ≥ el de T5.7 más los tests nuevos de esta tarea.
4. `python -m ruff check .` — ok.
5. `README.md` documenta la restricción de un solo worker, sin URLs ni valores nuevos inventados.
6. Comentario en el código (donde quede el candado) explica, en una frase, por qué existe y cuál es la alternativa de producción (lock de fila / `SERIALIZABLE`), sin implementarla.
7. Diff no toca `backend/app/rules/`, `backend/app/models/`, `data/rules.json` ni el grafo.
8. `docs/TASK_BOARD.md`: T5.8 pasa a HECHA con la evidencia anterior. G5 sigue PENDIENTE.
9. Fila en `docs/AI_USAGE_LOG.md`, incluyendo que Rules Engine revisó el diff (o que no pudo revisarlo, con el motivo, si aplica).
10. Commit y push con el mensaje del §5.

## 5. Commit

```text
T5.8: serialize ledger-dependent decisions to enforce period limits
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T5.8 según docs/T5_8_SPEC.md. Decisión D055.
Race real: production_processor.py process_upload() línea 111 lee el ledger
persistido (settled_ledger_from_store) antes de decidir; app.py post_invoice
líneas 102 y 106 deciden y persisten sin candado entre medio. sql_store.py
add_decision (líneas 47-67) solo evita invoice_id duplicado, no el total del
periodo. Dos facturas concurrentes, cada una bajo el límite, pueden terminar
ambas PAGAR y juntas superar limits.per_period.
Arregla con un único threading.Lock de proceso que serialice lectura del
ledger + decisión + persistencia del PAGAR, solo en la ruta POST /invoices.
Documenta en README que el deploy espera un solo worker uvicorn. Anota el
lock de fila / SERIALIZABLE como alternativa de producción, sin
implementarla. Añade un test con dos threading.Thread reales que demuestre
a lo sumo un PAGAR cuando dos facturas juntas exceden el límite de periodo.
No toques reglas, modelos ni data/rules.json.
Al terminar: pytest -q, ruff check ., tablero, AI_USAGE_LOG. Commit y push:
T5.8: serialize ledger-dependent decisions to enforce period limits
```
