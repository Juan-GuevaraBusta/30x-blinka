# Spec G4 — Demo pública: regla, factura y explicación

Dueño del gate: **Orquestador**. Dueño del cableado del procesador en producción: **API** (con apoyo de **Agent Graph** para `run_invoice`). Deploy Render/Vercel: **API** + **Frontend** según `docs/T4_9_SPEC.md`. Skill del gate: `verification-before-completion` (TOTAL). Deploy: `render-deploy`, `render-web-services`, `render-postgres`, `render-env-vars` (PARCIAL; host SUPUESTO D003). Vercel: **NINGUNA**. No usar `langfuse`, `langchain-rag` ni `supabase` (D004).

Estado: contrato para la sesión que **cierre** G4. Este archivo no cierra el gate.

Decisión que fija este contrato: **D040**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, **antes** de afirmar éxito:

- `AGENTS.md` (I1–I8; I2 el LLM no decide el pago; I6 solo datos sintéticos; I8 cero dinero; I9 no se mide aquí)
- `docs/05_PHASES_AND_ROADMAP.md` F4 y fila **G4**
- `docs/TASK_BOARD.md` fila G4 y T4.3, T4.5, T4.8, T4.9
- `docs/T4_3_SPEC.md` §7 (recorrido `/reglas`)
- `docs/T4_5_SPEC.md` §6–§7 (qué cuenta como «explicación» en `/decisiones/[id]`)
- `docs/T4_8_SPEC.md` §7 (metadatos de subida; factura de demo)
- `docs/T4_9_SPEC.md` §6–§11 (deploy, variables, recorrido §9 de infra)
- `docs/DECISIONS_LOG.md` D003, D007, D038, D039
- `docs/SKILLS_MAP.md` fila G4
- `backend/app/api/asgi.py` (`_stub_processor` hoy)
- `backend/app/graph/build.py` (`run_invoice`)
- `backend/app/graph/folder_batch.py` (`build_runtime_graph_deps`, ledger)
- `data/invoices/catalog.json` fila `dev-001`
- `frontend/app/api/` (proxies same-origin ya existentes)

Declarar en una línea la skill `verification-before-completion` y seguirla: **ninguna** afirmación de cierre sin recorrido fresco en URL pública.

D003 (Render + Postgres + Vercel) sigue **SUPUESTO** hasta confirmación del humano. Un deploy que arranca no confirma el host.

## 1. Qué es G4

Gate de F4 (`docs/05`): desde **URLs públicas https** del frontend (y del API como respaldo de health), una persona puede:

| Paso | Pantalla | Qué demuestra |
|---|---|---|
| A | `/reglas` | Editar y **persistir** una regla (`PUT` vía proxy) |
| B | `/subir` | **Procesar** una factura sintética del corpus (`POST /invoices` → 201) |
| C | `/decisiones/[id]` | **Ver la decisión explicada**: extracción, al menos un chequeo con regla/resultado/detail, `summary` (y `next_step` si viene en el registro) |

Los tres pasos son **un solo recorrido** en el navegador. Una captura no basta. Anotar herramienta (Playwright, navegador manual, o ambas) y las dos URLs en el tablero.

**Precondiciones de código (ya HECHA en el tablero):** T4.3, T4.5, T4.8. **Precondición de infra:** T4.9 commiteada **y** servicios desplegados con recorrido §9 de `docs/T4_9_SPEC.md` verificado (health, reglas en Postgres).

**Bloqueo conocido hoy:** `create_production_app` usa `_stub_processor` → `POST /invoices` en producción falla. G4 **exige** sustituir ese stub por un procesador que invoque el grafo (`run_invoice`) o, si el humano lo rechaza por costo/latencia, un adaptador documentado en D040 bis que aún produzca un `DecisionRecord` completo vía el mismo camino que G3 (preferido: grafo real con `phase="demo"`).

G4 **no** cierra G5 ni G6. No exige `/aprobaciones`, `/metricas` ni holdout.

## 2. Fuera de alcance

- Cerrar G5, G6, G3 (ya cerrado).
- Correr holdout o calibrar JEV (T5.2).
- Afirmar `unsafe_pay = 0` en el deploy público (I9 y reporte = G5).
- Seed del golden en Postgres como datos fijos de demo (solo reglas al arranque, como T4.9).
- Auth, API keys de cliente, JWT, rate limit nuevo.
- Editar `backend/app/models/`, `backend/openapi.json` (`paths`), `data/rules.json`, `backend/app/config.py` (D007).
- Cambiar copy o layout de T4.3/T4.5/T4.8 salvo un enlace de navegación mínimo si el recorrido lo exige (preferir no tocar frontend).
- Langfuse, RAG, Supabase, base vectorial.
- Demo de aprobación humana, métricas con reporte real, o subida holdout.
- Pegar secretos, `.env`, o URLs con credenciales en el repo, README o tablero.

## 3. Archivos

### Crear (sesión que cierra G4)

- Módulo puente en `backend/app/api/` (nombre sugerido: `invoice_pipeline.py` o `production_processor.py`): construye `GraphDeps` con **`store.rules`** (no un `rules.json` desincronizado tras un `PUT`), ledger derivado de decisiones `PAGAR` ya en `SqlStore`, `Settings()` desde el entorno, `run_invoice` con `phase="demo"`, checkpointer en memoria (`MemorySaver`) por proceso.
- Tests en `backend/tests/api/` (p. ej. `test_production_processor.py`): sin red; doble de `get_llm` / transporte o `run_invoice` mockeado; al menos un caso feliz que devuelve `DecisionRecord` y un caso que mapea error a `InvoiceRejected` o 422 sin traceback en el cuerpo.

### Modificar

- `backend/app/api/asgi.py`: sustituir `_stub_processor` por el procesador del módulo puente. **Dueño API.** No mover lógica del grafo a `asgi.py`; solo cableado.
- `README.md`: URLs públicas https (sin secretos), frase de que G4 exige las claves LLM/JEV en el Dashboard de Render si se usa el grafo real.
- Al cerrar el gate: `docs/DECISIONS_LOG.md` (cierre G4), `docs/TASK_BOARD.md` (**G4 HECHA**), `docs/AI_USAGE_LOG.md`, opcional casilla G4 en `docs/05_PHASES_AND_ROADMAP.md`.

### No tocar (salvo bug bloqueante del recorrido)

- `frontend/app/reglas/**`, `frontend/app/decisiones/**`, `frontend/app/subir/**` (ya implementados).
- `backend/app/graph/` salvo el Orquestador coordine un cambio mínimo con Agent Graph (preferir cero).
- `eval/reports/` (G5).

## 4. Invariantes

- I2. `decide()` no se llama desde la UI. El procesador HTTP usa el grafo; el pago lo fija el motor dentro del grafo.
- I3. Fallo de red, JSON inválido o timeout en el grafo → registro ESCALAR (fail-closed), no `PAGAR` por defecto.
- I6. Factura de demo = `dev-001` del catálogo y archivo en `data/invoices/dev/`. No subir facturas reales. No loguear claves ni `DATABASE_URL`.
- I8. «PAGAR» en pantalla es etiqueta; G4 no mueve dinero.
- I9. G4 no sustituye el gate de evaluación. `/metricas` puede seguir en vacío sin lector.

El procesador **no** puede devolver `decision=PAGAR` con un doble fijo tipo `make_record` del test API: eso invalidaría el claim «procesar una factura» frente a jueces si se documenta como grafo. Si el humano impone doble por tiempo, anotar en el cierre G4 que el procesador **no** era el grafo (y G4 queda débil para demo).

## 5. Infraestructura mínima (T4.9 + G4)

Completar primero lo pendiente de T4.9 en vivo:

| Pieza | Requisito |
|---|---|
| API Render | `GET /health` → 200; `SqlStore`; seed de reglas |
| Postgres | Umbral 3000 tras seed; `PUT` sobrevive reinicio (probar una vez si es práctico) |
| Vercel `frontend/` | `API_URL` = origen https del API, solo servidor |
| `CORS_ORIGINS` | Origen exacto del front (opcional si todo pasa por proxy) |
| Secretos Render | `LLM_API_KEY`, modelos según `.env.example`; `JEV_API_KEY` o plan B; `LANGSMITH_*` opcional para traza |

Esperar cold start del plan free antes del recorrido.

## 6. Procesador de facturas en producción

### 6.1 Contrato

Entrada: `InvoiceUpload` (ya validado en `app.py`). Salida: `DecisionRecord` listo para `store.add_decision`.

- `channel` del formulario debe ser uno de `pdf_text` \| `image` \| `email` \| `chat` (ya validado por `InvoiceMeta`).
- `received_at` con zona (`AwareDatetime`).
- `thread_id` único por envío (p. ej. `invoice_id` si no hay colisión, o UUID).
- `phase="demo"` en `run_invoice`.
- Reglas y FX: reglas = `store.rules`; FX desde `data/fx.json` en el filesystem del despliegue (el repo en la imagen Render).
- Ledger: entradas `PAGAR` de registros ya persistidos en el store (mismo espíritu que `folder_batch`).

### 6.2 Errores

- `GraphError`, validación o rechazo de negocio → `InvoiceRejected` con código corto (sin stack en JSON).
- Error inesperado → no devolver 201 con cuerpo inventado; preferir 422/500 con mensaje genérico en español vía capa HTTP existente.

### 6.3 Pruebas sin red

- Test que `create_production_app` + POST simulado (TestClient multipart) con procesador mockeado persiste en SQLite `tmp_path`.
- `python -m pytest -q backend/tests/api/test_asgi_boot.py` sigue verde.
- `python -m pytest -q` y `ruff check .` sin regresiones.

No abrir sockets en tests nuevos.

## 7. Recorrido de aceptación de G4

**Origen:** URL pública del frontend (`https://<proyecto>.vercel.app`). Datos sintéticos Acme Demo Inc.

Factura recomendada (misma que T4.8 §7, alineada al catálogo):

| Campo | Valor |
|---|---|
| Archivo | `data/invoices/dev/dev-001_normal_pay.pdf` |
| `invoice_id` | `dev-001` |
| `channel` | `pdf_text` |
| `received_at` | `2025-12-22T10:00:00Z` |

Usar un `invoice_id` **nuevo** si `dev-001` ya existe en Postgres del deploy (p. ej. `dev-001-g4-<fecha>`) y anotarlo en el tablero. El recorrido exige **un** 201 exitoso, no un id fijo.

### 7.1 Editar regla (paso A)

1. Abrir `https://<front>/reglas`.
2. Cambiar `human_approval_threshold` a **2500**. Guardar. Respuesta 200 vía `/api/rules`.
3. Recargar. El umbral sigue en **2500**.
4. (Limpieza) Devolver el umbral a **3000** y guardar, o dejar constancia en la nota del gate si se dejó en 2500.

Comprobar que las peticiones del navegador van a `/api/rules`, no a `:8000` directo desde el documento.

### 7.2 Procesar factura (paso B)

1. Abrir `https://<front>/subir`.
2. Adjuntar el PDF, rellenar metadatos, enviar.
3. Respuesta **201**. En pantalla se leen `decision`, `summary` e `id` del cuerpo.
4. El enlace a `/decisiones/` + `id` debe abrir la ficha (paso C), no 404.

Si 409 `duplicate_invoice`, cambiar `invoice_id` y repetir una vez.

### 7.3 Ver explicación (paso C)

1. Abrir `https://<front>/decisiones/<id>` del paso B.
2. Se ve al menos: un campo de **extracción** no nulo, un **chequeo** con regla y resultado (`OK` / `FALLA` / `INDETERMINADO`), y el **summary** (explicación guardada).
3. Traza: enlace solo si `trace.url` es http(s); si no, texto «sin traza». Las dos salidas son válidas.

### 7.4 Opcional (no bloquea G4)

- Listar en `/decisiones` el filtro que coincida con la `decision` del paso B.
- `GET https://<api>/health` como humo paralelo.

## 8. Qué no afirmar

- Que G5 o G6 están cerrados.
- Que `unsafe_pay` es 0 en producción.
- Que el holdout pasó.
- Que hay auth.
- Que `/metricas` muestra un reporte commiteado en `eval/`.
- Que el procesador local con `make_record` cuenta como G4 (solo cuenta el recorrido en **URL pública** con persistencia Postgres).
- Que el humano confirmó Render (sigue SUPUESTO hasta nota explícita).
- Que «Pagada» movió dinero.

## 9. Criterios de aceptación

1. **Recorrido §7** ejecutado en URL pública del front, con evidencia en `docs/TASK_BOARD.md`: URLs https, herramienta, `invoice_id` usado, decisión del 201, y que la ficha mostró chequeo + summary.
2. T4.9 §9 completado en las mismas URLs (health + reglas PUT/GET) o referenciado en la fila G4 si se hizo en la misma sesión.
3. `POST /invoices` en el API desplegado devuelve 201 con registro persistido (comprobar con segundo GET `/decisions/{id}` o reabriendo la ficha).
4. `python -m pytest -q` — 0 failed; `python -m ruff check .` — ok.
5. `git status` sin `.env`, secretos ni artefactos locales de demo.
6. Diff de `backend/openapi.json` (`paths`) vacío salvo cambio aprobado por Orquestador.
7. `docs/DECISIONS_LOG.md`: fila **G4 cerrado** (referencia D040).
8. `docs/TASK_BOARD.md`: **G4 HECHA**; T4.3–T4.9 siguen HECHA; G5/G6 PENDIENTE.
9. Fila en `docs/AI_USAGE_LOG.md`.
10. Commit sugerido: `G4: wire public demo path for rules upload and explanation`. Push a la rama de seguimiento.

## 10. Subtareas

- **G4.1** Completar deploy T4.9 §9 (Render + Vercel, variables, README URLs).
- **G4.2** Módulo procesador + cableado en `asgi.py`; tests sin red.
- **G4.3** Recorrido §7 en navegador/Playwright contra URL pública; anotar evidencia.
- **G4.4** Cerrar gate en tablero, decisión de cierre, log, commit y push.

## 11. Mensaje para la sesión que implementa

```text
Cierra G4 según docs/G4_SPEC.md.
Skill: verification-before-completion (léela; evidencia antes de afirmar).
Primero T4.9 §9 en vivo si falta (skills Render PARCIAL; sin MCP Render salvo que el humano lo pida).
Sustituye _stub_processor en asgi.py por run_invoice (phase=demo) con reglas del SqlStore y ledger del store.
No uses el doble make_record del test API como procesador de producción.
Recorrido en URL pública: /reglas (PUT 2500), /subir (dev-001 o id nuevo), /decisiones/[id] con chequeos y summary.
No cierres G5. No corras holdout. No pegues secretos.
Al terminar: pytest, ruff, tablero, DECISIONS_LOG, AI_USAGE_LOG, commit y push (sección 9.10).
```
