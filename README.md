# Paquete de contexto — Agente pagador de facturas (Hackathon Blinka)

Este paquete incluye **documentación de contexto** y un **scaffold mínimo** (árbol de carpetas, pytest, ruff, `.env.example`). Su objetivo es que otra IA (o tu IDE) entienda qué construimos, por qué, con qué límites y en qué orden, y a partir de ahí implemente el agente pagador.

## Orden de lectura (obligatorio)

| # | Archivo | Para qué sirve |
|---|---|---|
| 0 | `docs/00_MASTER_PROMPT.md` | **Primer mensaje** para la IA. Misión, objetivos, reglas no negociables, qué entregar primero. |
| 1 | `AGENTS.md` | Reglas inviolables, orquestación de agentes, protocolo de skills. Va en la **raíz del repo**. |
| 2 | `docs/01_CONTEXT_AND_SCOPE.md` | El reto, qué entra y qué no, criterios de éxito. |
| 3 | `docs/02_ARCHITECTURE.md` | Grafo LangGraph, roles de modelos, JEV, verificador, stack, estructura de repo. |
| 4 | `docs/03_JUDGE_REVERSE_ENGINEERING.md` | Investigación de jueces-agente en hackathons y qué implica para nuestro repo. |
| 5 | `docs/04_RULES_AND_DECISION_SPEC.md` | Esquema de reglas, catálogo R01–R13, registro de decisión, plantillas de explicación. |
| 6 | `docs/05_PHASES_AND_ROADMAP.md` | Fases, subtareas con ID, gates, líneas de corte (36 h). |
| 7 | `docs/06_EVAL_AND_TEST_PLAN.md` | Set dorado, casos trampa, métricas, pruebas. |
| 8 | `docs/07_OBSERVABILITY_LANGSMITH.md` | Registro de operaciones con LangSmith y puente al futuro frontend. |
| 9 | `docs/08_OPEN_QUESTIONS_AND_ASSUMPTIONS.md` | Supuestos y preguntas abiertas. **Resolver antes de codificar.** |

## Cómo usarlo
1. Copia el repo vacío, pon `AGENTS.md` en la raíz y la carpeta `docs/` tal cual.
2. Pega `docs/00_MASTER_PROMPT.md` como primer mensaje a la IA.
3. La IA debe responder con su comprensión, ambigüedades y el roadmap validado **antes de escribir código**.

## Desarrollo local (scaffold)

Desde la raíz del repo, con Python 3.11+:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
```

## Despliegue público (T4.9)

Host **supuesto** (D003): API en [Render](https://render.com) con Postgres gestionado; frontend en Vercel (`frontend/`). Sustituir las URLs de ejemplo cuando exista el deploy.

| Pieza | URL de ejemplo |
|---|---|
| API (Render) | `https://blinka-invoice-api.onrender.com` |
| Frontend (Vercel) | `https://blinka-invoice-agent.vercel.app` |

**Render (web service):** `render.yaml` en la raíz. Arranque: `uvicorn app.api.asgi:create_production_app --factory --host 0.0.0.0 --port $PORT`. Health: `GET /health`.

Variables (nombres solamente; valores en el Dashboard o en `.env` local, sin commitear):

- Render: `PORT` (inyectado), `DATABASE_URL` (desde la base del Blueprint), `CORS_ORIGINS` (origen exacto del front), `API_RATE_LIMIT_PER_MINUTE`
- Secretos para procesar facturas en producción (G4, grafo real): `LLM_API_KEY`, modelos según `.env.example`; `JEV_API_KEY` o plan B documentado en `docs/DECISIONS_LOG.md`. Opcional: `LANGSMITH_API_KEY` para trazas.
- Vercel (solo servidor): `API_URL` — origen público del API, sin ruta ni clave

El navegador usa same-origin (`/api/rules` en Next); CORS en el API es allowlist de respaldo.

## Estado
- Fase actual: **F0 — arranque** (T0.1 scaffold hecho; G0 abierto hasta T0.3/T0.4).
- Tiempo disponible: **36 h**. Idioma de documentos y UI: español. Identificadores de código: inglés.
