# Spec T4.9 — Despliegue público del API y del frontend

Dueño del servicio backend y de `render.yaml`: **API**. Mitad Vercel bajo `frontend/`: **Frontend**. Skills de dominio (PARCIAL, host SUPUESTO): `render-deploy`, `render-web-services`, `render-postgres`, `render-env-vars`. Vercel: **NINGUNA** (`docs/SKILLS_MAP.md`). No usar `langfuse`, `langchain-rag` ni `supabase` (D004). No usar el MCP de Render: el archivo `render.yaml` lo escribe esta sesión.

Estado: contrato para la sesión que **implemente** T4.9. Este archivo no cierra la tarea ni el gate G4.

Decisión que fija este contrato: **D038**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Declarar en una línea las cuatro skills de Render y leerlas antes de tocar código. Vercel no tiene skill: no inventar una.

Leer también:

- `AGENTS.md` §4 (skills Render, PARCIAL) y §5 (API dueño de `render.yaml`; Frontend dueño del deploy de `frontend/`)
- `docs/DECISIONS_LOG.md` D003 (host SUPUESTO: Render + Postgres gestionado), D007 (API no edita `backend/app/config.py`)
- `docs/05_PHASES_AND_ROADMAP.md` T4.9 y G4
- `docs/T4_2_SPEC.md` (`SqlStore`, `seed_rules`, `DATABASE_URL`)
- `docs/T4_3_SPEC.md` §3 y §8 (proxy same-origin; hoy no hay CORS ni entrypoint commiteado)
- `docs/SKILLS_MAP.md` fila T4.9
- `docs/OPEN_QUESTIONS_STATUS.md` Q6
- `.env.example` (solo nombres)
- `backend/app/persistence/` (`database_url_from_mapping`, `init_database`, `SqlStore`, `seed_rules`)
- `backend/app/api/app.py` (`create_app`, `GET /health`)
- `frontend/app/api/rules/route.ts` y `frontend/.env.example`
- Regla de plataforma Render del IDE: bind `0.0.0.0:$PORT`, filesystem efímero, un servicio por aplicación

D003 sigue **SUPUESTO** hasta que el humano lo confirme. Un deploy que arranque no convierte el supuesto en confirmación. Si el humano elige otro host, parar y no aplicar el Blueprint.

No editar `backend/app/models/`, `backend/app/rules/`, `backend/app/records/`, `backend/app/gate/`, `backend/app/config.py`, `backend/app/graph/`, `data/rules.json`, `backend/openapi.json` (los `paths` quedan iguales). `DATABASE_URL` se lee con `database_url_from_mapping`, fuera de `Settings`.

## 1. Qué es T4.9

Dejar el API y el frontend alcanzables por URL pública, con las reglas en Postgres y el navegador hablando con su propio origen.

| Pieza | Qué hace |
|---|---|
| API | Un proceso escucha `0.0.0.0:$PORT`. Almacén `SqlStore`. `DATABASE_URL` viene del entorno |
| Postgres | Base gestionada en Render. SUPUESTO D003. El disco del servicio web no guarda la base |
| Frontend | Proyecto Vercel de `frontend/`. `API_URL` solo en el servidor, origen público del API |
| Navegador | Sigue en same-origin. Next reenvía a `API_URL`. CORS del API es una allowlist de respaldo |
| Seed | Al arrancar, si la fila de reglas no existe, inserta `data/rules.json`. Si existe, no escribe |

`GET /health` ya responde `{"status":"ok"}` (T4.1). El rate limit por IP de T4.1 sigue en todas las rutas, `/health` incluido. Un 429 es `{"detail":"rate_limited"}`.

## 2. Fuera de alcance

- Cerrar G4. G4 pide, desde una URL pública, editar una regla, **procesar una factura** y **ver la explicación**. Depende de T4.3 (hecha), T4.5 (pendiente) y T4.9. El recorrido de factura queda para el gate.
- Construir T4.4, T4.5, T4.6, T4.7 o T4.8.
- Auth, API keys de cliente, JWT.
- Cablear `run_invoice` o el grafo en el proceso público. `POST /invoices` no forma parte del recorrido de esta tarea.
- Seed de facturas del golden, del holdout o del ledger. El comando de demo es T6.2.
- Correr el holdout, `eval/run_motor.py` o `eval/run_invoices.py` contra el deploy. I9 se juzga en G5.
- Alembic. Sigue `create_all` de `init_database`.
- Editar `config.py`, modelos, motor, `data/rules.json` u OpenAPI.
- LangChain, Langfuse, RAG, Supabase, base vectorial.
- Un segundo servicio web para el frontend dentro de Render. El front es Vercel. Un servicio por aplicación.
- Disco persistente en el web service. Los datos viven en Postgres.
- Pegar secretos, URLs con usuario/clave, o el contenido de `.env`.

## 3. Archivos

Crear (dueño API):

- Módulo de arranque en `backend/app/api/asgi.py`. Al importar `app.api` no se abre un engine ni se lee `.env` (el `__init__` actual no importa este módulo).
- `render.yaml` en la raíz. Lo crea esta sesión. Este spec no lo trae escrito.
- `backend/tests/api/test_asgi_boot.py`. SQLite en `tmp_path`. Cero sockets.

Modificar:

- `pyproject.toml`: solo `uvicorn` y `psycopg[binary]` en `dependencies`. El driver es el que T4.2 dejó para esta tarea: sin DBAPI, `create_engine` no abre Postgres. Nada de Alembic, `asyncpg` ni Gunicorn.
- `frontend/.env.example`: sigue `API_URL=http://127.0.0.1:8000`. Un comentario dice que en Vercel el valor es el origen público del API (`https://…`, sin ruta y sin clave) y que no se commitea.
- `.env.example` (raíz): una línea `CORS_ORIGINS=` vacía, con comentario de allowlist (orígenes exactos, separados por coma). `DATABASE_URL` sigue el ejemplo SQLite. Sin host real y sin clave.
- Al cerrar: sección corta de despliegue en `README.md` (URLs públicas y **nombres** de variables). `docs/TASK_BOARD.md` y `docs/AI_USAGE_LOG.md`.

No tocar `docs/DECISIONS_LOG.md` (la fila D038 la inserta el Orquestador). No tocar `models/`, el motor, ni `data/rules.json`. El seed solo lo lee.

## 4. Invariantes

- I2. El arranque no llama a un LLM ni a `decide()`. Carga reglas y sirve el HTTP de T4.1.
- I6. Cero datos reales. Cero secretos en el repo, en el README, en `render.yaml`, en logs y en el cuerpo de un error. Un fallo de URL dice `missing_database_url` y no imprime `DATABASE_URL`.
- I8. Este deploy no mueve dinero. El recorrido no procesa facturas. Un `PAGAR` futuro seguiría siendo una etiqueta de registro.
- I9. T4.9 no mide `unsafe_pay` ni corre el holdout. Si más adelante `unsafe_pay > 0`, el bloqueo es G5.
- D007. `Settings` no gana una clave `DATABASE_URL`.

El procesador que exige `create_app` es un stub del entrypoint: no llama a la red, no escribe en el store y no devuelve un `DecisionRecord` con `decision=PAGAR`. Una subida recibe error del servidor. Eso no es la pantalla de T4.5.

## 5. Entrypoint

`create_production_app(mapping, *, rules_path, cors_origins) -> FastAPI`.

- `mapping` en producción es `os.environ`. Los tests pasan un dict. No abrir un archivo `.env`.
- URL con `database_url_from_mapping`. Vacía → `MissingDatabaseUrlError` y el proceso no escucha.
- Esquema, solo en este módulo (la función de T4.2 sigue devolviendo el texto tal cual):
  - `sqlite:` se usa tal cual (tests y dev local).
  - `postgres://` y `postgresql://` pasan a `postgresql+psycopg://` (mismo usuario, host, ruta y query).
  - `postgresql+psycopg://` se queda.
  - Otro esquema: error con código `unsupported_database_url`, sin conectar y sin loguear la URL.
- Si el URL de Postgres no trae `sslmode` y el host no es interno de Render (`dpg-…-a`), añadir `sslmode=require`. El URL interno del Blueprint no lleva TLS. El externo sí.
- `create_engine(..., pool_pre_ping=True, pool_size=5, max_overflow=0)`. Render no trae pooler.
- `init_database(engine)`, `SqlStore(engine)`, `seed_rules(store, rules_path)`.
- `rules_path` por defecto: `data/rules.json` desde el directorio de trabajo (raíz del repo en el servicio). Si el archivo no está, el proceso no arranca y no inventa un `RulesConfig`.
- `create_app(store, stub, clock=ahora UTC, rate_limit=…)`. El límite sale de `API_RATE_LIMIT_PER_MINUTE` (entero ≥ 1). Ausente → 60, como `.env.example`. Un valor inválido aborta el arranque.
- CORS según §8, solo si la lista no está vacía.

Comando de arranque (también dentro de `render.yaml`):

```text
uvicorn app.api.asgi:create_production_app --factory --host 0.0.0.0 --port $PORT
```

`PORT` lo inyecta Render (a menudo 10000). El proceso habla HTTP. TLS termina en el borde de Render. No atar `127.0.0.1`. No usar los puertos reservados 18012, 18013 ni 19099.

Health check del servicio: `GET /health` (`healthCheckPath: /health`). 2xx para dar el deploy por vivo.

El factory de uvicorn llama `create_production_app()` sin argumentos y esa entrada lee `os.environ`. Los tests llaman el factory con un mapping y no importan el arranque al importar `app.api`.

## 6. Postgres y variables (SUPUESTO)

`render.yaml` describe **un** web service Python (plan `free`, salvo que el humano pida otro) y **una** base Postgres gestionada (plan `free`). El frontend no va en ese archivo.

- `DATABASE_URL` sale de `fromDatabase` / `property: connectionString` (URL **interna**, misma región). Ningún `value:` con cadena real.
- `buildCommand`: instalar el proyecto (`pip install .` o equivalente desde la raíz, donde está `pyproject.toml`).
- `startCommand`: el de §5.
- `healthCheckPath: /health`.
- Sin disco persistente. El filesystem del web service es efímero: un `sqlite:///` ahí se pierde en cada deploy.
- Secretos (`LANGSMITH_API_KEY`, `LLM_API_KEY`, `JEV_API_KEY` y cualquier clave) con `sync: false` y valor puesto en el Dashboard. El arranque de health y reglas **no** los exige. Si faltan, `/health` y `/rules` igual responden.
- `CORS_ORIGINS` con `sync: false`. El humano pega el origen exacto del front cuando Vercel lo tenga. Sin `*`.
- `API_RATE_LIMIT_PER_MINUTE` puede ir como literal `60`.
- Nombres que el README lista, sin valores: `PORT`, `DATABASE_URL`, `CORS_ORIGINS`, `API_RATE_LIMIT_PER_MINUTE`, y en Vercel `API_URL`.

El servicio free se duerme tras inactividad. El recorrido espera a que despierte. No afirmar uptime continuo.

## 7. Frontend: una sola vía

El navegador sigue en **same-origin**. Ya lo hace `frontend/app/api/rules/route.ts`: el cliente llama `/api/rules` y Next, en el servidor, reenvía a `${API_URL}/rules`.

En producción `API_URL` es el origen público del API (`https://<servicio>.onrender.com`, sin path, sin usuario y sin clave), configurado en el proyecto Vercel. No crear `NEXT_PUBLIC_API_URL`. Ninguna clave de `.env.example` (LangSmith, LLM, JEV) entra al bundle ni a una variable `NEXT_PUBLIC_`.

Motivo: T4.3 ya cerró el proxy, y same-origin evita publicar el API como origen del documento. Un rewrite de Next hacia el mismo `API_URL` vale si sustituye al route handler; no hace falta los dos. El navegador no llama a Render directo.

Vercel no tiene skill en el mapa. Un proyecto para `frontend/`. El API es el otro servicio, en Render.

## 8. CORS mínimo en el API

Aunque la vía del producto es el proxy, el API lleva allowlist por si un navegador llama al origen del API.

- Variable `CORS_ORIGINS`: orígenes exactos separados por coma (`https://<front>.vercel.app`). Sin path, sin `*`, sin credenciales dentro del origen.
- Lista vacía o ausente: no se monta `CORSMiddleware`. El proxy same-origin no la necesita.
- Lista con `*` o con un origen vacío: el proceso no arranca (código `invalid_cors_origins`).
- Orígenes de la lista, métodos `GET`, `PUT`, `POST`, `OPTIONS`, cabecera `Content-Type`. `allow_credentials` en falso. Sin `allow_origin_regex`.
- El recorrido de §9 usa el proxy o `curl`. `curl` no envía `Origin`. La allowlist no es el camino principal.

## 9. Recorrido de aceptación de T4.9

Datos sintéticos (Acme Demo Inc., umbral 3000 de `data/rules.json`). Pocas llamadas: el rate limit sigue en 60/minuto.

1. `GET https://<api>/health` → 200 y `{"status":"ok"}`.
2. `GET https://<api>/rules` **o** `GET https://<front>/api/rules` → 200 y un `RulesConfig`. Si el seed acaba de correr sobre una base vacía, `human_approval_threshold` es 3000.
3. `PUT` del documento completo con el umbral en 2500 (el resto igual al GET). Otro GET muestra 2500. Segundo `PUT` que devuelve el umbral a 3000. Otro GET muestra 3000. El segundo PUT es la reversión: la fila pública queda como el seed.
4. Anotar que **procesar una factura y ver la explicación es G4** y exige T4.5, que sigue PENDIENTE. Ese paso no se ejecuta aquí y no se marca hecho.

El umbral 2500 tiene que sobrevivir a un reinicio del servicio **antes** de revertirlo, si el recorrido puede reiniciar sin costo: así se ve que es Postgres y no el disco efímero. Si reiniciar no es práctico, el GET tras el PUT ya demuestra la escritura; decir cuál de las dos pruebas se hizo.

## 10. Qué no afirmar

- Que G4 está cerrado.
- Que hay auth.
- Que el holdout pasó, o que `unsafe_pay` es 0 en este deploy.
- Que desde la URL pública ya se procesa una factura o se lee la explicación.
- Que el humano confirmó Render (sigue SUPUESTO D003 / Q6).
- Que el navegador llama al API en cross-origin.
- Que `CORS_ORIGINS=*` está permitido.
- Que el seed cargó facturas.
- Que un `PAGAR` de este deploy movió dinero.

## 11. Criterios de aceptación

### DoD de T4.9 (esta tarea)

1. Recorrido §9 anotado en el tablero: URL del API, URL del front, health 200, GET de reglas, PUT 2500 revertido a 3000. Herramienta (`curl`, navegador o las dos).
2. `README.md` con esas dos URLs (https, sin usuario ni clave) y la lista de nombres de §6. Sin valores secretos.
3. `python -m pytest -q backend/tests/api/test_asgi_boot.py` — 0 failed. Cubre: scheme `postgresql://` reescrito sin socket; factory con SQLite en `tmp_path` hace seed, GET y PUT; un segundo `seed_rules` no pisa el PUT; `decisions` vacío tras el seed; `*` en CORS aborta; importar `app.api` no abre engine.
4. `python -m pytest -q` — 0 failed. `python -m ruff check .` — ok.
5. `git status` sin `.env`, sin `*.sqlite` y sin secretos. `render.yaml` sin `value:` de claves ni de `DATABASE_URL`.
6. Diff de `backend/openapi.json` vacío en `paths`. Diff de `config.py`, `models/`, `rules/` y `data/rules.json` vacío.
7. Tablero: T4.9 HECHA con las URLs. T4.4–T4.8 y **G4 siguen PENDIENTE**.
8. Fila en `docs/AI_USAGE_LOG.md`.
9. Commit: `T4.9: public API and frontend deploy wiring`.

### DoD de G4 (otra sesión, no esta)

Desde la URL pública, en el navegador (una captura no basta): editar una regla, procesar una factura y ver la decisión explicada. Skill `verification-before-completion`. Exige T4.3, T4.5 y T4.9. Cerrar G4 en el tablero de esta sesión sería cerrar el gate de más.

## 12. Subtareas

- T4.9.1 `create_production_app` + test SQLite (seed, PUT que sobrevive a otro seed, CORS que rechaza `*`). Sin red.
- T4.9.2 `uvicorn` y `psycopg[binary]` en `pyproject.toml`. Comando §5.
- T4.9.3 `render.yaml` (web + Postgres, `DATABASE_URL` por `fromDatabase`, health `/health`). Secretos en `sync: false`.
- T4.9.4 Vercel: `API_URL` server-side hacia el origen público. El route handler de `/api/rules` sigue. Sin `NEXT_PUBLIC_` de secretos.
- T4.9.5 Recorrido §9, README, tablero, commit y push. G4 queda PENDIENTE.

## 13. Mensaje para la sesión que implementa

```text
Implementa T4.9 según docs/T4_9_SPEC.md.
Skills: render-deploy, render-web-services, render-postgres, render-env-vars. Léelas antes del código.
Vercel: ninguna skill. No uses el MCP de Render. Tú creas render.yaml.
Host SUPUESTO D003 (Render + Postgres). No edites config.py: DATABASE_URL sigue en persistence/.
Entrypoint backend/app/api/asgi.py: 0.0.0.0:$PORT, SqlStore, seed de reglas solo si la fila no existe.
No siembres facturas. No cables run_invoice. El navegador sigue same-origin; CORS es allowlist, nunca *.
No cierres G4. Procesar una factura y ver la explicación exige T4.5.
Al terminar: recorrido §9, README sin secretos, pytest, ruff, commit y push (sección 11.9).
```
