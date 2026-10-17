# Spec T4.2 — Persistencia SQLAlchemy y seed reproducible

Dueño: **API**. Skill de dominio: **NINGUNA** (`docs/SKILLS_MAP.md`: SQLAlchemy no tiene skill; no usar `supabase`). Proceso de la sesión que implemente: `test-driven-development` y `python-testing-patterns`. No usar `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **implemente** T4.2. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D031**. D030 sigue libre: `docs/G2_SPEC.md` lo reserva para un parche de producto de G2 que no ocurrió.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (I1–I9; I2 el LLM no decide; I6 sin datos reales; I8 cero dinero)
- `docs/02_ARCHITECTURE.md` fila Persistencia (SQLite en dev, Postgres en prod)
- `docs/04_RULES_AND_DECISION_SPEC.md` §5 (el registro es inmutable; el evento humano se agrega)
- `docs/05_PHASES_AND_ROADMAP.md` T4.2
- `docs/DECISIONS_LOG.md` D007, D008, D013, D029, D031
- `docs/T4_1_SPEC.md` (el HTTP no cambia)
- `backend/app/api/store.py` (`MemoryStore`, `DuplicateDecisionError`)
- `backend/app/api/app.py` (`create_app`; lee `store.rules`, `store.decisions`, `store.get`)
- `backend/app/models/domain.py` (`DecisionRecord`, `HumanEvent`)
- `backend/app/models/rules_config.py` (`RulesConfig`, `load_rules_config`)

No editar `backend/app/models/`, `backend/app/rules/`, `backend/app/records/`, `backend/app/gate/`, `backend/app/config.py`, `backend/app/graph/`, `data/`. D007: API no toca `config.py`. `DATABASE_URL` se lee en `backend/app/persistence/`, no en `Settings`. Si un test exige cambiar esos caminos, **parar**.

No cambiar el comportamiento de `MemoryStore`. Los tests de T4.1 siguen inyectándolo. No hace falta tocar `backend/app/api/app.py` si `SqlStore` cumple el protocolo de §6.

## 1. Qué es T4.2

El mismo contrato HTTP de T4.1, con un almacén SQL que sobrevive a cerrar el engine y abrir otro sobre el **mismo archivo** SQLite.

| Pieza | Qué hace |
|---|---|
| Tablas | Una fila de reglas. Una fila por `DecisionRecord`, con `invoice_id` único y orden de inserción |
| `SqlStore` | Mismos métodos que `MemoryStore`. Cada lectura devuelve modelos nuevos, validados con Pydantic |
| `seed_rules` | Si no hay fila de reglas, inserta `data/rules.json`. Si ya hay fila, no escribe |
| Reinicio | Segundo engine, mismo archivo: la decisión y el evento humano siguen ahí |
| HTTP | `create_app(sql_store, ...)` cumple PUT/GET de reglas y approve sin reescribir `decision` |

Tests usan un archivo SQLite en `tmp_path`. Ningún test abre Postgres, lee `.env` ni crea `blinka.sqlite` en el repo.

`PAGAR` guardado sigue siendo la etiqueta del registro (I8). El seed no inserta decisiones ni facturas.

## 2. Fuera de alcance

- Alembic, migraciones versionadas, historial de reglas. Hay una sola fila vigente. El versionado de la UI es T4.3.
- Driver de Postgres (`psycopg`, `asyncpg`). Un URL `postgres://` o `postgresql://` se acepta como texto y **no** se conecta. El servidor Postgres es T4.9.
- `render.yaml`, CORS, bind `0.0.0.0:$PORT`, crear la base en Render.
- CLI de demo y borrar la base para el ensayo (T6.2). Aquí solo la función `seed_rules`.
- Cablear `run_invoice`, `create_app_from_env` o `uvicorn`. Siguen sin sockets en pytest.
- Cambiar rutas, códigos HTTP o `backend/openapi.json`. Si el diff de `paths` no es vacío, parar.
- Guardar los bytes del PDF. Solo el `DecisionRecord`.
- Persistir el rate limit ni las métricas. Siguen en proceso / `null` (T4.1, I9).
- Cargar las 34 facturas del set dev, ni el ledger de `ledger_seed`.
- Auth, API keys de cliente, JWT.
- Editar `config.py`, `models/`, `rules/`, `records/`, `gate/`, `graph/`, `data/`.
- Borrar o reescribir `MemoryStore`.
- LangChain, Langfuse, RAG, Supabase.
- Cerrar G3, G4, G5.

## 3. Archivos

Crear:

- `backend/app/persistence/__init__.py` — exportar `SqlStore`, `init_database`, `seed_rules`, `database_url_from_mapping`. Al importar: cero engines, cero archivos, cero red.
- `backend/app/persistence/tables.py` — tablas de §5.
- `backend/app/persistence/sql_store.py` — `SqlStore`.
- `backend/app/persistence/seed.py` — `seed_rules`.
- `backend/tests/api/test_sql_store.py`
- `backend/tests/api/test_seed.py`

Modificar:

- `pyproject.toml` — dependencia `sqlalchemy>=2`. Nada más (ni Alembic, ni driver Postgres, ni `aiosqlite`).
- `.env.example` — una línea `DATABASE_URL=sqlite:///./blinka.sqlite`. Sin contraseña, sin host real.
- `.gitignore` — `*.sqlite` y `*.sqlite3`.
- Al cerrar: `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`.

No tocar `MemoryStore`, `app.py`, `openapi.json`, `models/`, `config.py`, `data/`.

## 4. Invariantes

- I2. El store no llama `decide()` ni a un LLM. Persiste el `DecisionRecord` que ya llegó.
- I4. `add_human_event` solo agrega el evento dentro del JSON. `decision` y `severity` del registro guardado no cambian. Un approve sobre `PAGAR` o `FRENAR` sigue en 409 y no escribe (el guardia ya está en `app.py`).
- I6. No leer `.env` en pytest. No loguear `DATABASE_URL` (puede traer clave en T4.9). Tests y respuestas sin claves.
- I8. Insertar un registro `PAGAR` no mueve dinero.
- I9. `GET /metrics` sigue en `null` si no hay lector. El store no inventa `unsafe_pay`.

JSON corrupto en una fila → el store lanza. No devuelve un registro a medias ni un `PAGAR`.

## 5. Tablas

SQLAlchemy 2, `MetaData` propio, `create_all` dentro de `init_database(engine)`. Tipos que SQLite y Postgres comparten. El payload es `Text` (JSON UTF-8), no una columna por campo del dominio.

`rules_document`:

| Columna | Regla |
|---|---|
| `id` | entero, clave primaria, solo el valor `1` |
| `payload` | texto, JSON de `RulesConfig` |

`decision_record`:

| Columna | Regla |
|---|---|
| `id` | texto, clave primaria, igual a `DecisionRecord.id` |
| `invoice_id` | texto, único, igual a `DecisionRecord.invoice_id` |
| `decision` | texto, `PAGAR` \| `ESCALAR` \| `FRENAR` |
| `position` | entero, orden de inserción, empieza en 1, no se reutiliza |
| `payload` | texto, JSON del `DecisionRecord` completo, `human_events` incluidos |

Sin tabla de eventos, sin tabla de archivos, sin tabla de rate limit.

## 6. Protocolo de `SqlStore`

Misma superficie que usa `create_app`. Sesión corta por método: abre, hace el trabajo, commit o rollback, cierra.

- `rules` → `RulesConfig` de la fila `1`. Si no hay fila: error de dominio (`RulesMissing`), no un `RulesConfig` inventado.
- `put_rules(rules)` → sustituye el payload de la fila `1`. La crea si falta. No toca `decision_record`.
- `has_invoice(invoice_id)` → bool.
- `add_decision(record)` → inserta. `id` o `invoice_id` repetido → `DuplicateDecisionError` (la de `app.api.store`). Rollback: la tabla queda como antes.
- `get(decision_id)` → `DecisionRecord` o `None`.
- `add_human_event(decision_id, event)` → lee, `model_copy` con la lista nueva, guarda el payload nuevo. No muta el objeto que el caller ya tenía.
- `decisions` → `dict[str, DecisionRecord]` nuevo, ordenado por `position`. Mutar ese dict no escribe en la base.

Round-trip: `model_dump(mode="json")` después de leer es igual al de antes de guardar. Fechas con zona. `extra` del JSON de más se rechaza al validar (`extra=forbid` ya está en los modelos).

## 7. Seed

```text
seed_rules(store, rules_path: Path) -> RulesConfig
```

- Lee el JSON con `load_rules_config` (o `RulesConfig.model_validate_json`). El path lo pasa el test: `data/rules.json`. No hardcodear otro archivo.
- Si `rules` lanzaría `RulesMissing`, inserta esa config y la devuelve.
- Si ya hay fila, devuelve la guardada y **no** escribe. Un `PUT` con `human_approval_threshold` 2500 sobrevive a un segundo `seed_rules`.
- No inserta decisiones. No borra decisiones. Llamarlo dos veces seguidas deja una sola fila.
- No es un comando de terminal. T6.2 citará el comando de demo.

## 8. URL

```text
database_url_from_mapping(mapping) -> str
```

- Lee la clave `DATABASE_URL` del mapping que le pasan. No llama a `os.environ` y no importa `app.config`.
- Vacía o ausente → error con código `missing_database_url`.
- `sqlite:///...` se devuelve tal cual.
- `postgres://...` y `postgresql://...` se devuelven tal cual, sin `create_engine` y sin red.
- El test de reinicio arma `sqlite:///<tmp_path>/blinka.sqlite`, llama `init_database`, cierra con `engine.dispose()` y abre un segundo engine al mismo path.

`create_engine` solo en tests de SQLite y, en el futuro, en T4.9. Esta tarea no conecta Postgres.

## 9. Pruebas

`backend/tests/api/test_sql_store.py`:

- Round-trip de un `DecisionRecord` (el ejemplo de T4.1 / `make_record`) con `human_events` vacío.
- Mismo `invoice_id` → `DuplicateDecisionError` y una sola fila.
- Dos altas: `list(store.decisions)` conserva el orden de inserción.
- `add_human_event` en `ESCALAR`: el objeto viejo sigue con `human_events` vacío; el leído de la base tiene un evento; `decision` y `severity` iguales.
- `put_rules` no cambia el payload de una decisión ya guardada.
- Reinicio: `dispose()`, segundo engine, `get` devuelve otro objeto con el mismo `model_dump(mode="json")`.
- Payload que no valida → el store lanza; no hay `DecisionRecord`.
- HTTP: `create_app(SqlStore, doble, ...)`. `PUT /rules` con umbral 2500. Cerrar el `TestClient` y `engine.dispose()` antes del segundo engine. Otro `SqlStore` sobre el mismo archivo: `GET /rules` devuelve 2500. Approve de un `ESCALAR` persiste el evento y no cambia `decision`. Approve de un `PAGAR` → 409 y cero eventos en la base.

`backend/tests/api/test_seed.py`:

- Base vacía + `seed_rules(data/rules.json)` → `GET` lógico del store igual al archivo (`human_approval_threshold` 3000).
- Segunda llamada → sigue una fila y el mismo payload.
- Tras `put_rules` con umbral 2500, otro `seed_rules` deja 2500.
- Después del seed, `decisions` está vacío.
- `database_url_from_mapping({})` lanza `missing_database_url`.
- Un mapping con `postgresql://demo.example/blinka` no abre socket (el test no llama `create_engine`).

Los tests de T4.1 quedan verdes sin cambiarlos a SQL.

## 10. Qué no afirmar

- Que la UI persiste.
- Que un proceso `uvicorn` ya usa `SqlStore` (no hay entrypoint en esta tarea).
- Que Postgres está creado o que Render conserva datos.
- Que el PDF se puede volver a leer tras el reinicio.
- Que el seed carga el set dev o el golden.
- Que `unsafe_pay` es 0.
- Que hay auth.

## 11. Criterios de aceptación

1. `python -m pytest -q backend/tests/api/test_sql_store.py backend/tests/api/test_seed.py` — 0 failed. Incluye reinicio en archivo, seed que no pisa un PUT, 409 sin evento y URL de Postgres sin socket.
2. `python -m pytest -q` — 0 failed (no romper los 391 anteriores).
3. `python -m ruff check .` — ok.
4. `git status` sin `.env`, sin `*.sqlite` y sin secretos.
5. `backend/openapi.json` sin cambio de `paths`.
6. Tablero: T4.2 HECHA con el conteo real de pytest. T4.3, T4.9, G3 y G4 siguen PENDIENTE.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit: `T4.2: SQLAlchemy store and reproducible seed`.

## 12. Subtareas

- T4.2.1 Tablas + `init_database` en `tmp_path`. Sin fila de reglas, `rules` lanza `RulesMissing`.
- T4.2.2 Round-trip, duplicado, orden, evento humano, `put_rules` no toca decisiones.
- T4.2.3 Segundo engine sobre el mismo archivo.
- T4.2.4 `seed_rules` idempotente y no pisa un PUT. Cero decisiones.
- T4.2.5 HTTP con `SqlStore` (umbral 2500 y approve). pytest completo + ruff. Tablero. Commit y push.

## 13. Mensaje para la sesión que implementa

```text
Implementa T4.2 según docs/T4_2_SPEC.md.
Skill de dominio: ninguna. No uses supabase, langfuse ni langchain-rag.
Proceso: test-driven-development y python-testing-patterns.
No edites models/, rules/, records/, gate/, config.py, graph/ ni data/.
No cambies MemoryStore ni las rutas de T4.1.
SQLite en tmp_path. Ningún test abre Postgres ni lee .env.
seed_rules solo inserta data/rules.json si la fila no existe. No inserta facturas.
Al terminar: pytest, ruff, commit y push (sección 11.8).
```
