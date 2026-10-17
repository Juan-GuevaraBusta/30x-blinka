# Spec T4.1 — Endpoints HTTP y OpenAPI

Dueño: **API**. Skill de dominio: `api-engineer` (PARCIAL). Proceso de la sesión que implemente: `test-driven-development` y `python-testing-patterns`. No usar `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **implemente** T4.1. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D029**.

Postman: el contrato vive en el repo (`backend/openapi.json` + FastAPI). **No** `postman init`, **no** `postman workspace push`, **no** colección, salvo que el humano lo pida (tablero T4.1).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (I1–I9; I2 el LLM no decide; I8 cero dinero)
- `docs/02_ARCHITECTURE.md` stack FastAPI y aprobación humana
- `docs/04_RULES_AND_DECISION_SPEC.md` §2, §5 (registro inmutable; evento humano no reescribe la decisión)
- `docs/05_PHASES_AND_ROADMAP.md` T4.1
- `docs/DECISIONS_LOG.md` D007, D008, D013, D029
- `backend/app/models/domain.py` (`DecisionRecord`, `HumanEvent`)
- `backend/app/models/rules_config.py` (`RulesConfig`, `extra=forbid`)
- `backend/app/graph/build.py` (`run_invoice`)
- `backend/app/extraction/ingest.py` (`IngestChannel`)

No editar `backend/app/models/`, `backend/app/rules/`, `backend/app/records/`, `backend/app/gate/`, `backend/app/config.py`, `backend/app/graph/`, `data/`. D007: API no toca `config.py`. Si un test exige cambiarlos, **parar**.

## 1. Qué es T4.1

API HTTP que el frontend puede consumir. OpenAPI generado por la app y **commiteado**.

| Método y ruta | Qué hace | Éxito |
|---|---|---|
| `GET /rules` | Reglas vigentes | 200, cuerpo = `RulesConfig` |
| `PUT /rules` | Sustituye reglas si el cuerpo valida | 200, reglas nuevas. Cuerpo inválido o campo extra → **422** y las reglas **no cambian** |
| `GET /decisions` | Lista. Query opcional `decision=PAGAR\|ESCALAR\|FRENAR` | 200, lista (puede ir vacía) |
| `GET /decisions/{id}` | Un registro | 200 o **404** |
| `POST /invoices` | Multipart: archivo + metadatos. Un procesador inyectado devuelve `DecisionRecord` | 201, el registro. Mismo `invoice_id` → **409** |
| `POST /decisions/{id}/approve` | Añade `HumanEvent` `aprobada_humano` | 200. No cambia `decision` ni `severity` |
| `POST /decisions/{id}/reject` | Igual con `rechazada_humano` | 200. Motivo vacío → **422** |
| `GET /metrics` | Lee el último reporte si existe | 200. Sin archivo: `unsafe_pay` y `autonomy_pct` en `null` |
| `GET /openapi.json` | Esquema OpenAPI 3 | 200, las rutas de arriba presentes |
| `GET /health` | Proceso vivo | 200 `{"status":"ok"}` |

Al arrancar, las reglas salen de `data/rules.json` (lectura). `PUT` no escribe ese archivo: vive en un almacén en memoria. Disco y SQLAlchemy son **T4.2**.

`POST /invoices` **no** llama a la red en tests. El procesador es un callable inyectado en `create_app`. El cableado real a `run_invoice` puede existir en una fábrica `create_app_from_env`, pero **ningún test** la usa ni abre sockets.

## 2. Fuera de alcance

- SQLAlchemy, seed, SQLite, Postgres (T4.2). No crear tablas.
- UI Next.js (T4.3–T4.8). No pulir frontend.
- Deploy, CORS de producción, `render.yaml`, bind `0.0.0.0:$PORT` (T4.9).
- Cerrar G3, G4, G5.
- `eval/run_invoices.py` sobre las 34 facturas.
- Auth de usuarios, API keys de cliente, JWT. No hay cuentas en v1.
- Reescribir `decision` al aprobar o rechazar (I2 / `docs/04` §5).
- Rate limit en Redis. El límite de esta tarea es en proceso, por IP.
- Workspace Postman.
- Editar `config.py` para meter `DATABASE_URL` o el rate limit.
- LangChain, Langfuse, RAG.

## 3. Archivos

Crear:

- `backend/app/api/app.py` — `create_app(store, processor, *, clock, rate_limit)` 
- `backend/app/api/store.py` — almacén en memoria: reglas, decisiones, eventos
- `backend/app/api/schemas.py` — cuerpos de approve/reject y métricas. `extra=forbid`
- `backend/app/api/rate_limit.py` — ventana fija por IP
- `backend/openapi.json` — volcado de `app.openapi()` al cerrar la tarea (generado, no a mano)
- `backend/tests/api/test_rules_reject.py`
- `backend/tests/api/test_decisions.py`
- `backend/tests/api/test_invoices.py`
- `backend/tests/api/test_openapi.py`
- `backend/tests/api/test_rate_limit.py`

Modificar:

- `backend/app/api/__init__.py` — exportar `create_app`. Sin efectos al importar.
- `pyproject.toml` — dependencia `fastapi` y, en `dev`, `httpx` (el `TestClient` de Starlette lo usa). Nada más.
- `.env.example` — solo el nombre `API_RATE_LIMIT_PER_MINUTE=60`. Sin secretos.
- Al cerrar: `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`.

No tocar `models/`, `rules/`, `records/`, `gate/`, `config.py`, `graph/`, `data/`.

## 4. Invariantes

- I2. La ruta no llama `decide()` ni a un LLM. El procesador inyectado ya trae el `DecisionRecord`. Un test de `POST /invoices` usa un doble que devuelve un registro fijo.
- I4. Aprobar o rechazar no baja ni sube `decision` / `severity`. Solo crece `human_events`.
- I6. Respuestas y logs de test sin claves. No leer `.env` en pytest.
- I8. `PAGAR` en JSON es la etiqueta del registro, no un pago.
- I9. `GET /metrics` no inventa `unsafe_pay=0`. Sin reporte → `null`.

Aprobar o rechazar solo si `decision == "ESCALAR"`. Si es `PAGAR` o `FRENAR` → **409** y cero eventos nuevos.

## 5. Contrato HTTP

Prefijo: ninguno (`/rules`, no `/api/rules`). JSON UTF-8. Errores FastAPI: `{"detail": ...}`.

### 5.1 Reglas

`PUT /rules` cuerpo = JSON de `RulesConfig`. Validación = `RulesConfig.model_validate` (ya `extra=forbid`).

Casos del test `test_rules_reject.py`:

- Campo `per_payment` negativo o ausente → 422; `GET /rules` sigue igual que antes.
- Clave desconocida `"extra_field": 1` → 422.
- Cuerpo válido (copia de `data/rules.json` con `human_approval_threshold` distinto, p. ej. 2500) → 200; el GET siguiente devuelve 2500.
- El PUT no modifica decisiones ya guardadas.

### 5.2 Decisiones

`GET /decisions?decision=ESCALAR` filtra. Valor distinto de `PAGAR|ESCALAR|FRENAR` → 422.

`GET /decisions/{id}` 404 si no está. El id es el `DecisionRecord.id`, no el `invoice_id`.

### 5.3 Facturas

`POST /invoices` `multipart/form-data`:

| Campo | Regla |
|---|---|
| `file` | obligatorio, 1–2_000_000 bytes. Vacío o mayor → 422 |
| `invoice_id` | str, 1–64, sin espacios |
| `channel` | `pdf_text` \| `image` \| `email` \| `chat` |
| `received_at` | ISO-8601 con zona. Naive → 422 |

Respuesta 201: JSON del `DecisionRecord` que devolvió el procesador, guardado en el almacén.

Mismo `invoice_id` otra vez → 409, sin segunda llamada al procesador (el test cuenta llamadas).

El procesador puede lanzar una excepción de dominio → 422 con `detail` corto, sin traceback ni claves.

### 5.4 Aprobación

`POST /decisions/{id}/approve` y `.../reject`.

Cuerpo:

```json
{"author": "cfo@demo.test", "reason": "Coincide con el presupuesto"}
```

`author` y `reason`: 1–500 caracteres. Vacío, ausente o campo extra → 422.

`at` lo pone el `clock` inyectado (aware UTC). No lo manda el cliente.

404 si el id no existe. 409 si la decisión no es `ESCALAR`.

### 5.5 Métricas

`GET /metrics`:

```json
{"unsafe_pay": null, "autonomy_pct": null, "source": "none"}
```

Si se inyecta un lector que devuelve números, esos números salen tal cual (`source`: `"report"`). T4.1 no parsea `eval/reports/` en disco (aún no hay reporte de G3).

### 5.6 Rate limit

Todas las rutas de §1 excepto que el límite aplica también a `/health` y `/openapi.json`.

- Clave: IP de `request.client.host`. Sin usuario.
- Default: 60 peticiones por minuto (`API_RATE_LIMIT_PER_MINUTE`). En tests el límite se inyecta (p. ej. 2) para no depender del entorno.
- Al pasar: **429**, cuerpo `{"detail":"rate_limited"}`, header `Retry-After: 60`.
- No es un middleware de terceros. Dict + reloj inyectado.

### 5.7 OpenAPI

`GET /openapi.json` incluye los paths de §1. `backend/openapi.json` es el mismo documento, escrito al cerrar (un test puede generarlo y el commit lo incluye). `info.title`: `blinka-invoice-agent`.

## 6. Almacén

`MemoryStore`:

- `rules: RulesConfig` — inicial, argumento de `create_app` (el test pasa un `RulesConfig` mínimo válido o carga el JSON en el test).
- `decisions: dict[str, DecisionRecord]` orden de inserción.
- `put_rules` sustituye solo si el modelo ya validó.
- `add_decision` rechaza `invoice_id` repetido.
- `add_human_event` copia el registro con `model_copy`; no muta el objeto viejo si otro holder lo tiene (el store guarda el nuevo).

Sin hilos reales en tests. Un lock no es obligatorio.

## 7. Qué no afirmar

- Que la UI funciona.
- Que `POST /invoices` procesa el set dev (G3).
- Que hay persistencia tras reiniciar (T4.2).
- Que `unsafe_pay` es 0.
- Que hay auth.

## 8. Criterios de aceptación

1. `python -m pytest -q backend/tests/api/` — 0 failed. Incluye rechazo de reglas, approve con motivo vacío, filtro, 409, OpenAPI y 429.
2. `python -m pytest -q` — 0 failed (no romper 355+ anteriores).
3. `python -m ruff check .` — ok.
4. `backend/openapi.json` en el commit; un test comprueba que coincide con `create_app(...).openapi()` en `paths`.
5. `git diff` sin `.env` ni secretos.
6. Tablero: T4.1 HECHA con el conteo real de pytest. T4.2 y G3/G4 siguen PENDIENTE.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit: `T4.1: HTTP API and OpenAPI contract`.

## 9. Subtareas

- T4.1.1 Store + `create_app` vacío con `/health`. Test 200.
- T4.1.2 `GET/PUT /rules` y `test_rules_reject.py` (422 no persiste).
- T4.1.3 Decisiones, facturas con doble, approve/reject.
- T4.1.4 Métricas null y rate limit 429.
- T4.1.5 OpenAPI commiteado. pytest completo + ruff. Tablero. Commit y push.

## 10. Mensaje para la sesión que implementa

```text
Implementa T4.1 según docs/T4_1_SPEC.md.
Skill: api-engineer. Proceso: test-driven-development y python-testing-patterns.
No uses langfuse ni langchain-rag. No abras workspace Postman.
No edites models/, rules/, records/, gate/, config.py, graph/ ni data/.
Sin red en tests. El POST /invoices usa un doble.
PUT /rules inválido → 422 y no guarda. Aprobar no reescribe decision.
Al terminar: pytest, ruff, openapi.json, commit y push (sección 8.8).
```
