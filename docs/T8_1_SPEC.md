# Spec T8.1 — Trazas LangSmith etiquetadas por `owner_id`

Dueño: Agent Graph (grafo) + API (processor HTTP). Skill de dominio: **NINGUNA** en LangSmith. Proceso: `test-driven-development` y `python-testing-patterns` (TOTAL); `api-engineer` (PARCIAL, cableado HTTP; sin Postman ni workspace). No usar `langfuse`, `migrate-to-langfuse`, `langchain-rag`, `frontend-design`, `langgraph-fundamentals` (el grafo no cambia de nodos ni aristas).

Estado: contrato para la sesión que implemente T8.1.

Decisión que fija este contrato: **D060**.

## 0. Para el agente que implementa

Leer antes de tocar código:

1. `AGENTS.md` (I1–I9; I2 el LLM no decide; I3 fail-closed del pago ≠ fallo de traza; I6 sintéticos; I8 cero dinero)
2. `.cursor/rules/commit-push-after-progress.mdc` (commit + push tras cada avance)
3. `docs/07_OBSERVABILITY_LANGSMITH.md`
4. `docs/T3_8_SPEC.md` (T3.8 ya existe; no se reabre)
5. `docs/SUPABASE_SETUP.md` (header `X-User-Id`, sin JWT)
6. Este archivo

Declarar al empezar cada bloque: `Skill: test-driven-development — T8.1 owner_id en traza`.

## 1. Qué es T8.1

Hoy:

- `GET /decisions` y `GET /decisions/{id}` ya recortan por `owner_id`.
- `POST /invoices` sí conoce `owner_id` (`require_user_id`) y lo usa al persistir.
- `Processor = Callable[[InvoiceUpload], DecisionRecord]` **no** recibe el dueño.
- `run_invoice` manda a LangSmith metadata `invoice_id`, modelos, `phase` y tags `["invoice", phase]`. Sin dueño.
- Una sola `LANGSMITH_API_KEY` y un solo `LANGSMITH_PROJECT` de proceso. Eso **se queda**.

Después:

- El processor de producción recibe `owner_id`.
- `run_invoice(..., owner_id=...)` lo copia a metadata y tags **solo si** viene no vacío.
- CLI / eval (`run_invoice_folder`) no pasan dueño: comportamiento de T3.8 intacto.
- `TraceRef` no cambia. No hay `tenant_id`. No se inventa URL.
- El frontend no cambia (salvo un test si algún tipo de processor se reexportara; no es el caso).

## 2. Fuera de alcance

- Clave LangSmith por usuario, `NEXT_PUBLIC_*` de LangSmith, o llamar a LangSmith desde el browser (T4.5 lo prohíbe).
- Endpoint nuevo que liste runs de LangSmith.
- Pantalla `/trazas` o incrustar el UI de LangSmith.
- Cambiar `LANGSMITH_PROJECT` por usuario.
- Añadir `owner_id` a `DecisionRecord` / `TraceRef` / `backend/app/models/` (el dueño ya vive en SQL).
- Recortar `verify-chain`, `/metrics`, o el ledger global (`settled_ledger_from_store`). Anótalos en `docs/AI_USAGE_LOG.md` como seguimiento; no los arregles aquí.
- CORS `X-User-Id` en `allow_headers` (el proxy de Next ya reenvía; el browser no pega al API).
- JWT de Supabase. El API sigue confiando el header (KISS de `docs/SUPABASE_SETUP.md`).
- Nodos nuevos, `Command`, `add_edge`, `decide()`, reglas, dinero.
- Cerrar G5/G6/G7. No tocar holdout. No leer `.env`.
- `git config`, `--force`, `--amend` de un commit ya pusheado, secretos.

## 3. Archivos

Crear:

- `docs/T8_1_SPEC.md` — este contrato.

Modificar (Agent Graph):

- `backend/app/graph/build.py` — `run_invoice` acepta `owner_id: str | None = None`
- `backend/tests/test_tracing.py` — metadata/tags con y sin dueño

Modificar (API):

- `backend/app/api/production_processor.py` — `Processor` y `process_upload` reciben `owner_id`
- `backend/app/api/app.py` — `_decide_and_store_invoice` pasa `owner_id` al processor; el alias `Processor` queda igual que el de production
- Tests que construyen `def processor(upload)` — segundo argumento `owner_id: str`
- `backend/tests/api/test_production_processor.py` — asserting `kwargs["owner_id"]`
- Un test HTTP nuevo en `backend/tests/api/` que, con tracer falso inyectado, compruebe que el `X-User-Id` llega a `open_config`

Modificar (Orquestador, al cerrar):

- `docs/07_OBSERVABILITY_LANGSMITH.md` — añadir `owner_id` a la lista de metadatos (HTTP; ausente en CLI)
- `docs/TASK_BOARD.md` — fila T8.1 HECHA
- `docs/DECISIONS_LOG.md` — D060
- `docs/AI_USAGE_LOG.md` — una fila
- `docs/SKILLS_MAP.md` — fila T8.1

No editar: `frontend/`, `data/`, `eval/` salvo si un import de tipo rompe, `backend/app/models/`, `backend/app/rules/`, `backend/app/config.py` (D007), `render.yaml`.

## 4. Invariantes

- I2. La traza no pide decisión al modelo.
- I3. Fallo de tracer: decisión intacta, `trace` vacío, sin `error_tecnico`.
- I6. Ids sintéticos (`usr_synth_001`). Prohibido pegar UUID reales, emails, `LANGSMITH_API_KEY` o texto de factura en metadata de tests que se impriman.
- I8. Etiquetar la traza no mueve dinero.
- T3.8: no inventar `tenant_id`. El campo se llama `owner_id`, el mismo del SQL y del header.

## 5. Contrato de API interna

```python
def run_invoice(
    deps: GraphDeps,
    *,
    raw: bytes,
    channel: IngestChannel,
    invoice_id: str,
    received_at: datetime,
    checkpointer: BaseCheckpointSaver,
    thread_id: str,
    tracer: TraceSession | None = None,
    phase: Literal["dev", "eval", "demo"] = "dev",
    owner_id: str | None = None,
) -> DecisionRecord: ...
```

Tras armar `metadata` y `tags = ["invoice", phase]`: si `owner_id` no es `None` y `owner_id.strip()` no está vacío, copiar el string tal cual a `metadata["owner_id"]` y añadirlo como último tag. `None`, `""` y solo espacios no añaden clave ni tag.

```python
Processor = Callable[[InvoiceUpload, str], DecisionRecord]
```

`process_upload(config, upload, owner_id)` reenvía `owner_id=owner_id` a `run_invoice`. `_decide_and_store_invoice` llama `processor(upload, owner_id)`.

## 6. Tests

Dobles locales. Cero red. No leer `.env`. Id sintético `usr_synth_001`.

1. **Grafo.** Con `owner_id="usr_synth_001"`: `metadata["owner_id"]` y tag final igual. Sin argumento / `None` / `""`: sin clave `owner_id`; `tags == ["invoice", phase]`.
2. **Processor.** `kwargs["owner_id"]` llega a `run_invoice` desde `process_upload`.
3. **HTTP.** `POST /invoices` con `X-User-Id: usr_synth_001` y tracer falso: `open_config` recibe `owner_id` en metadata y tags.

## 7. Criterios de aceptación

1. CLI/eval sin `owner_id` deja metadata/tags como T3.8.
2. HTTP pasa el header hasta `open_config`.
3. Fallo de tracer no cambia decisión (T3.8 intacto).
4. `python -m pytest -q` y `python -m ruff check .` verdes.
5. Commit + push tras cada bloque. Tablero T8.1 HECHA con conteo real.
