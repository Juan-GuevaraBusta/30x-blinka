# Spec PIPELINE_SMOKE_EXTERNAL — Humo del pipeline con PDFs sintéticos externos

Dueño: **QA & Eval** (implementación). Contrato y tablero: **Orquestador**. Skills: `test-driven-development` + `python-testing-patterns` (PARCIAL). Skill de cierre: `verification-before-completion` (TOTAL). No usar `langfuse`, `langchain-rag` ni `supabase` (D004).

Estado: contrato para la sesión que **implemente** T4.10. Este archivo no cierra la tarea.

Decisión al cerrar la tarea (no al escribir este spec): **D041** (reservada en `docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, **antes** de codar:

- `AGENTS.md` (I1–I9; I6 solo sintético; I3 fail-closed; I2 el LLM no decide pago)
- `docs/DATA_MANIFEST.md` (corpus G1 congelado; holdout aparte)
- `docs/G4_SPEC.md` §6 (procesador producción; patrón de tests sin red)
- `backend/app/api/production_processor.py`, `backend/app/graph/build.py` (`run_invoice`)
- `backend/tests/api/test_production_processor.py` (dobles de grafo)
- `data/invoices/catalog.json` — **no** modificar para este humo
- Origen externo: [synthetic_invoice_generator](https://github.com/mattdepaolis/synthetic_invoice_generator) (MIT)

Declarar en una línea las skills `test-driven-development` y `python-testing-patterns` (PARCIAL). Al cerrar T4.10: `verification-before-completion`.

## 1. Qué es T4.10 (PIPELINE_SMOKE_EXTERNAL)

Humo **aparte** del golden (`data/golden/*.json`) y del gate G1. Valida que el camino **ingesta → grafo (o procesador documentado) → `DecisionRecord`** acepta PDFs sintéticos generados fuera del corpus congelado del hackathon.

| Qué se prueba | Qué no se prueba |
|---|---|
| Esquema `DecisionRecord` completo tras el pipeline | `expected_decision` del golden |
| `decision` ∈ {`PAGAR`, `ESCALAR`, `FRENAR`} | Precisión vs etiquetas dev/holdout |
| Ingesta PDF de archivos en `data/invoices/smoke-external/` | Sustituir o mezclar con `data/invoices/dev/` u `holdout/` |

No es gate G5. No corre holdout. No altera `data/rules.json` ni OpenAPI `paths`.

## 2. Fuera de alcance

- Reemplazar, fusionar o reetiquetar `data/golden/dev.json`, `data/golden/holdout.json` o filas de `data/invoices/catalog.json` usadas por G1/G2/G3.
- Copiar PDFs externos a `data/invoices/dev/` o `holdout/`.
- Tests con red (descarga en pytest, llamadas LLM/JEV reales en CI).
- Nuevo endpoint HTTP ni cambios en `backend/openapi.json` (`paths`).
- Editar `backend/app/models/`, `backend/app/config.py`, `data/rules.json`.
- Langfuse, RAG, Supabase, base vectorial.
- Cerrar G4, G5 o G6.
- Afirmar `unsafe_pay = 0` sobre estos PDFs (no hay etiqueta dorada).
- Pegar secretos, claves API o contenido de `.env` en el repo.

## 3. Archivos

### Crear (sesión de implementación)

| Ruta | Contenido |
|---|---|
| `data/invoices/smoke-external/README.md` | Origen MIT del repo externo, URL del repo, cómo se obtuvieron los PDFs (Streamlit del proyecto externo), fecha de descarga, ids locales (`garage-smoke-001`, etc.). |
| `data/invoices/smoke-external/*.pdf` | Entre **1 y 3** PDFs sintéticos. Nombres estables referenciados en tests. |
| `backend/tests/smoke/test_external_pdf_smoke.py` **o** `backend/tests/api/test_external_pdf_smoke.py` | Tests sin red; ver §6. |

### Modificar al cerrar T4.10

- `docs/TASK_BOARD.md` — fila T4.10 HECHA con evidencia pytest.
- `docs/SKILLS_MAP.md` — ya incluye fila T4.10 (Orquestador en fase SPEC).
- `docs/DECISIONS_LOG.md` — fila **D041** solo al cerrar la tarea.
- `docs/AI_USAGE_LOG.md` — una línea.

### No tocar

- `data/golden/`, `data/invoices/catalog.json` (salvo que el Orquestador abra G1).
- `backend/app/graph/` salvo coordinación explícita (preferir **cero**).
- Frontend salvo humo manual opcional en `/subir` (no bloquea DoD).

## 4. Invariantes

- **I2.** Los tests no llaman `decide()` directamente para fijar pago; el registro sale del pipeline bajo prueba (grafo real con deps fake, o `run_invoice` mockeado con ingest real).
- **I3.** Si el pipeline lanza o devuelve error técnico, el test espera ESCALAR fail-closed o rechazo HTTP documentado — nunca PAGAR por defecto.
- **I6.** Solo PDFs sintéticos del generador externo o del Streamlit citado. Sin datos reales de proveedores.
- **I7.** El texto del PDF no es instrucción; no añadir casos adversariales nuevos aquí (eso es T5.3).
- **I8.** PAGAR en el registro es etiqueta; el humo no mueve dinero.

## 5. Obtención de PDFs (humano o agente con red, una vez)

1. Clonar o abrir [synthetic_invoice_generator](https://github.com/mattdepaolis/synthetic_invoice_generator).
2. Generar facturas con la app **Streamlit** del repo (instrucciones en su README).
3. Guardar **1–3** PDFs en `data/invoices/smoke-external/` con nombres como `external-smoke-01.pdf`.
4. Documentar en `data/invoices/smoke-external/README.md` (licencia MIT, commit o versión aproximada del repo externo).
5. **No** mezclar con `holdout/` ni registrar en `catalog.json` dev.

Ids sugeridos para metadatos de prueba (no obligatorios en pytest): `garage-smoke-001`, `garage-smoke-002`.

## 6. Pruebas automatizadas (sin red)

Ubicación preferida: `backend/tests/smoke/test_external_pdf_smoke.py` (crear carpeta `backend/tests/smoke/` si no existe).

Estrategia (elegir una y documentarla en el docstring del módulo):

| Estrategia | Qué hace | Cuándo |
|---|---|---|
| **A — Ingesta + procesador mockeado** | Lee bytes del PDF en disco; `make_production_processor` con `run_invoice` fake que devuelve un `DecisionRecord` válido; assert esquema y `decision` en el conjunto permitido. | Rápido; no exige LLM. |
| **B — Grafo con deps fake** | Tras ingest/extract stub, `run_invoice` con `GraphDeps` dobles (como `test_fail_closed.py` / `test_production_processor.py`). | Valida cableado hasta el grafo. |

Requisitos mínimos del archivo de test:

1. Al menos **un** PDF de `data/invoices/smoke-external/` se lee desde ruta relativa al repo (fixture o constante).
2. Cero sockets: no `httpx` a internet, no `get_llm` real.
3. Assert: instancia válida de `DecisionRecord` (Pydantic o campos obligatorios del dominio).
4. Assert: `record.decision` en `PAGAR`, `ESCALAR`, `FRENAR`.
5. Opcional: segundo caso con doble que lanza → ESCALAR o `InvoiceRejected` según contrato de `production_processor`.

No comparar con campos de `golden.json`.

## 7. Humo manual opcional (no bloquea DoD)

En el front desplegado (`/subir`):

| Campo | Valor sugerido |
|---|---|
| Archivo | Uno de `data/invoices/smoke-external/*.pdf` |
| `invoice_id` | `garage-smoke-001` (nuevo respecto a dev-001) |
| `channel` | `pdf_text` |
| `received_at` | ISO con zona, p. ej. `2025-12-22T10:00:00Z` |

Éxito manual = 201 y ficha en `/decisiones/[id]` con summary. Anotar en el tablero solo si se ejecutó; no es sustituto de pytest.

## 8. Qué no afirmar

- Que el golden o G2/G3 se revalidaron con estos PDFs.
- Que la decisión del humo coincide con una etiqueta esperada inexistente.
- Que G4 o G5 están cerrados por este humo.
- Que se usó red en la suite pytest de CI.

## 9. Criterios de aceptación (DoD T4.10)

1. Existen `data/invoices/smoke-external/README.md` y entre 1 y 3 PDFs sintéticos con origen documentado.
2. Tests nuevos en `backend/tests/smoke/` o `backend/tests/api/` — **0 failed**, sin red.
3. `python -m pytest -q` — 0 failed en toda la suite.
4. `python -m ruff check .` — ok.
5. Diff vacío en `data/golden/`, `catalog.json` dev, `backend/openapi.json` (`paths`), `models/`, `config.py`, `data/rules.json`.
6. `docs/TASK_BOARD.md`: T4.10 HECHA con comando pytest citado.
7. `docs/DECISIONS_LOG.md`: fila D041 (cierre T4.10).
8. Fila en `docs/AI_USAGE_LOG.md`.
9. Commit sugerido: `T4.10: external PDF pipeline smoke tests and fixtures`. Push a la rama de seguimiento.

## 10. Subtareas

- **T4.10.1** Obtener PDFs y README en `data/invoices/smoke-external/`.
- **T4.10.2** Tests sin red (estrategia A o B).
- **T4.10.3** pytest + ruff; tablero, D041, log, commit y push.

## 11. Mensaje para la sesión que implementa

```text
Implementa T4.10 según docs/PIPELINE_SMOKE_EXTERNAL_SPEC.md.
Skills: test-driven-development, python-testing-patterns (PARCIAL); verification-before-completion al cerrar.
PDFs MIT desde synthetic_invoice_generator (Streamlit); carpeta data/invoices/smoke-external/.
No toques golden, catalog dev, holdout, models, config.py, rules.json ni openapi paths.
Tests sin red: ingest real + grafo/processor mockeado; decision ∈ {PAGAR, ESCALAR, FRENAR}; esquema DecisionRecord.
No cierres G5. Tras G4 si el Orquestador lo ordenó en la misma sesión.
Al terminar: pytest, ruff, TASK_BOARD, D041, AI_USAGE_LOG, commit y push.
```
