# Spec T3.9 — CLI: carpeta de facturas → `decisions.json`

Dueño: Agent Graph. Skill de dominio: **NINGUNA**. Proceso: `test-driven-development` y `python-testing-patterns`. No usar `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que implemente T3.9.

Decisión que fija este contrato: **D025**.

## 0. Para el agente que implementa

Leer: `AGENTS.md` (I2, I6, I8), `docs/T3_7_SPEC.md`, `docs/T3_8_SPEC.md`, `docs/DECISIONS_LOG.md` D023–D025, este archivo.

No leer `.env`. No llamar a la red en tests. No llamar `get_llm` ni al cliente real de LangSmith en tests. No editar `models/`, `rules/`, `records/`, `gate/`, `data/`. No añadir nodos al grafo. No cerrar G0 ni G3. No implementar T3.10.

## 1. Qué es T3.9

Una CLI recorre una carpeta de facturas, para cada archivo llama `run_invoice` (T3.7–T3.8) y escribe un `decisions.json` con los `DecisionRecord` resultantes. La CLI **no** decide el pago: solo orquesta el grafo.

Metadatos de cada factura (`channel`, `received_at`, `ledger_seed`, id) salen de `data/invoices/catalog.json`. Orden de proceso: `received_at`, desempate por `id` (igual que T2.8).

Trazas: `tracer = make_langsmith_session(load_settings())`. Sin clave o con tracing apagado → `NullTrace` y `trace.langsmith_run_id` / `trace.url` quedan `None`.

## 2. Archivos

Crear:

- `backend/app/graph/folder_batch.py` — `run_invoice_folder`, `select_catalog_rows`, `build_runtime_graph_deps`
- `eval/run_invoices.py` — entrada CLI
- `backend/tests/test_invoice_folder_cli.py`

Modificar:

- `backend/app/graph/__init__.py` — reexportar `run_invoice_folder`, `FolderBatchError`, `FolderRunReport`
- `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`, `docs/DECISIONS_LOG.md` (D025)

## 3. CLI

```bash
python eval/run_invoices.py [INVOICES_DIR] -o decisions.json
```

Argumentos:

| Flag | Default | Uso |
|---|---|---|
| `INVOICES_DIR` | `data/invoices/dev` | Carpeta con archivos de factura |
| `-o` / `--output` | `decisions.json` | Ruta del JSON de salida |
| `--data-root` | auto (layout del paquete) | Raíz con `data/` |
| `--catalog` | `data/invoices/catalog.json` | Catálogo relativo a data-root |
| `--phase` | `dev` | `dev` \| `eval` \| `demo` (metadata LangSmith) |

Cada archivo en la carpeta debe tener fila en el catálogo con `path` que apunte a ese archivo. Archivo sin catálogo → `FolderBatchError("unknown_invoice_file")` y exit code 2.

## 4. Salida `decisions.json`

```json
{
  "schema_version": 1,
  "generated_at": "<ISO-8601 Z>",
  "phase": "dev",
  "invoices_dir": "<ruta absoluta>",
  "records": [ "<DecisionRecord>" ]
}
```

Ledger acumulativo: tras cada `PAGAR`, la siguiente factura ve el ledger actualizado (misma lógica que `golden_runner`).

## 5. Tests (sin red)

1. Selección y orden de filas de catálogo.
2. Archivo huérfano → error.
3. Carpeta con una factura chat + dobles → `decisions.json` con un `PAGAR` y `trace` vacío.
4. `make_langsmith_session(Settings())` es `NullTrace` en el camino de la CLI.
5. Import de `eval/run_invoices.py` no abre sockets.

## 6. Criterios de cierre

- `python -m pytest -q` verde.
- `python -m ruff check .` pasa.
- T3.9 HECHA en el tablero. G0 y G3 siguen PENDIENTE.

## 7. Commit

`T3.9: CLI processes invoice folder into decisions.json`
