# Prompt para nueva sesión (Composer 2.5)

Copiar **todo el bloque** de abajo como primer mensaje en un chat nuevo.

---

```text
Repo: raíz de este repositorio (`30x-blinka`), clonado localmente en tu máquina
Modelo de ejecución: Composer 2.5 (una sesión, dos fases: spec → implementación).

## Misión

1. **Fase SPEC (Orquestador):** redactar specs nuevos en `docs/`, sin código de producto todavía.
2. **Fase EJECUCIÓN:** implementar exactamente esos specs, verificar, commit + push tras cada tarea (regla `.cursor/rules/commit-push-after-progress.mdc` y `AGENTS.md`).

## Contexto obligatorio (leer antes de escribir)

- `AGENTS.md` (I1–I9; I6 solo sintético; I8 sin dinero; I2 el LLM no decide pago)
- `docs/G4_SPEC.md` (gate demo pública; G4.2 ya hecha en código)
- `docs/T4_9_SPEC.md` §9 (recorrido infra)
- `docs/TASK_BOARD.md` filas G4, T4.9
- `docs/DECISIONS_LOG.md` D040, D038, D003 (Render+Vercel SUPUESTO)
- Deploy vivo (no commitear secretos):
  - API: https://blinka-invoice-api.onrender.com
  - Front: https://blinka-invoice-agent.vercel.app
  - `production_processor.py` cableado; Postgres `blinka-postgres` en Render workspace "My Workspace"

## Objetivo A — Cerrar G4 (prioridad)

Seguir `docs/G4_SPEC.md` §7–§9:

- Recorrido en URL pública del front: `/reglas` (PUT umbral 2500), `/subir` (factura sintética; preferir `dev-001` del catálogo o id nuevo si 409), `/decisiones/[id]` con extracción, ≥1 chequeo, `summary`.
- Evidencia en `docs/TASK_BOARD.md` (URLs, herramienta, invoice_id, decisión 201).
- `docs/DECISIONS_LOG.md` fila G4 cerrado (D040).
- `docs/AI_USAGE_LOG.md`, README URLs si cambian.
- Skill: `verification-before-completion` — no afirmar cierre sin prueba fresca en https.
- `python -m pytest -q` y `python -m ruff check .` antes de cerrar.
- Commit sugerido al cerrar gate: `G4: complete public demo walkthrough and evidence`

No cerrar G5/G6. No holdout. No pegar `.env` ni claves en el repo.

## Objetivo B — Spec + pipeline smoke con PDFs externos

El humano quiere validar el **pipeline** (ingesta → grafo → registro) con PDFs generados por:
https://github.com/mattdepaolis/synthetic_invoice_generator
**Sin** reemplazar `data/golden/*.json` ni el corpus congelado G1 (`docs/DATA_MANIFEST.md`).

### Fase SPEC — crear estos archivos (tú los escribes en la sesión)

1. **`docs/PIPELINE_SMOKE_EXTERNAL_SPEC.md`**
   - Dueño: QA & Eval (o Orquestador si no hay agente).
   - Qué es: smoke opcional aparte del golden; criterio = esquema `DecisionRecord` + decisión ∈ {PAGAR, ESCALAR, FRENAR}; no `expected_decision` del golden.
   - Carpeta: `data/invoices/smoke-external/` (PDFs commiteados o script de descarga documentado; solo sintéticos; README en carpeta con origen del repo externo y licencia MIT).
   - Cómo obtener PDFs: clonar/generar con Streamlit del repo externo; 1–3 PDFs bastan para smoke; no mezclar con `holdout/`.
   - Tests: `backend/tests/smoke/` o `backend/tests/api/test_external_pdf_smoke.py` — sin red; opcional integración local con `run_invoice` + LLM mockeado; al menos un test que lee bytes de un PDF en `smoke-external/` y verifica que el grafo no lanza sin capturar (fake deps) O test HTTP local con processor mockeado documentado.
   - Recorrido manual opcional: subir un PDF externo en `/subir` con `invoice_id` `garage-smoke-001`, `channel=pdf_text`.
   - Fuera de alcance: cambiar `catalog.json` dev, `golden.json`, reglas, OpenAPI paths, G5.
   - Invariantes I3 fail-closed.
   - Criterios de aceptación y subtareas numeradas.
   - Decisión nueva en `DECISIONS_LOG.md` (ej. D041) solo al **cerrar** la tarea, no en el borrador del spec.

2. **Actualizar `docs/SKILLS_MAP.md`** — fila para pipeline smoke (TDD / python-testing-patterns PARCIAL).

3. **Fila en `docs/TASK_BOARD.md`** — tarea nueva ej. `T5.0` o `T4.10` PIPELINE_SMOKE_EXTERNAL, PENDIENTE → HECHA al terminar.

Plantilla de estilo: copiar estructura de `docs/G4_SPEC.md` §0–§11 (§0 para el agente, invariantes, archivos crear/modificar/no tocar, mensaje final).

### Fase EJECUCIÓN — después de aprobar el spec (misma sesión)

- Declarar skill por tarea (`test-driven-development` / `python-testing-patterns` para tests; `verification-before-completion` para cierre).
- Implementar `PIPELINE_SMOKE_EXTERNAL_SPEC.md` al pie de la letra.
- Si G4 y B compiten por tiempo: **G4 primero**, luego smoke externo.
- Commits pequeños con ID de tarea (`T4.10: …`, `G4: …`).

## Restricciones

- No editar `backend/app/models/`, `backend/app/config.py`, `data/rules.json`, `backend/openapi.json` paths sin Orquestador.
- No usar Langfuse, RAG, Supabase.
- Español en docs/UI; inglés en código y commits.
- El autor del commit debe ser solo el humano del repo (no aparecer como coautor el agente).

## Entregables de la sesión

| Entregable | Cuándo |
|------------|--------|
| `docs/PIPELINE_SMOKE_EXTERNAL_SPEC.md` + tablero/skills | Fase SPEC |
| G4 HECHA con evidencia §7 | Tras deploy OK |
| Código + tests smoke external | Fase EJECUCIÓN |
| pytest + ruff verdes | Siempre antes de “hecho” |
| push a `origin/main` | Tras cada avance |

## Orden de trabajo sugerido

1. Leer contexto listado arriba.
2. Escribir `docs/PIPELINE_SMOKE_EXTERNAL_SPEC.md` y actualizar tablero/skills (commit `docs: add PIPELINE_SMOKE_EXTERNAL spec`).
3. Verificar deploy: `GET /health`, proxy `/api/rules` en Vercel (esperar cold start Render).
4. Ejecutar recorrido G4 §7; documentar; cerrar gate si pasa.
5. Ejecutar spec pipeline smoke externo (PDFs + tests).
6. pytest, ruff, logs, push final.

Empieza declarando en una línea las skills y entra en Fase SPEC escribiendo `docs/PIPELINE_SMOKE_EXTERNAL_SPEC.md` completo antes de tocar código de smoke. Para G4 puedes paralelizar verificación de deploy mientras redactas el spec si no bloquea.
```
