# Tachyon — agente de pagos a proveedores (Hackathon 30x · reto Blinka)

> **Borrador de estructura (T5.5, D046).** `T5.1` (`docs/TASK_BOARD.md`) sigue
> **PENDIENTE**. Por contrato (`docs/T5_5_SPEC.md` §0 y criterio de aceptación 0),
> mientras eso sea así este README solo trae estructura y afirmaciones sin
> cifras: nada de autonomía, `unsafe_pay`, montos ni conteos de chequeos. Las
> celdas de métricas quedan marcadas `pendiente T5.1`. Esta tarea no se marca
> hecha en el tablero.

<details>
<summary>English summary (for non-Spanish graders — the rest of this document is in Spanish, the project's documentation language)</summary>

This is an invoice-paying agent built for a hackathon. The user is the
**finance team of a company that is a client of Blinka**, paying that
company's own vendors through Blinka (decision D059). An invoice (PDF,
image, email or chat text) goes through an extraction step and a fixed set
of deterministic rule checks; a language model never decides whether to
pay — `decide()` is a pure function over check results. On any error,
timeout, or low-confidence signal the system fails closed into ESCALAR
(human review), and a separate verifier may only raise severity, never
lower it. "PAGAR" records a decision and a **simulated** payment status —
no real money moves, no real KYC/fraud determination is made, no OCR runs
on image invoices, and there is no live mailbox integration. See
`JUDGE_GUIDE.md` for the claim → evidence table. Metrics are not yet
reported here; T5.1 (dev + holdout evaluation) is pending.

</details>

## Qué es

Agente que decide si pagar una factura recibida por una empresa, o si debe
frenarse o escalarse a una persona. El usuario es el **equipo de finanzas de
una empresa cliente de Blinka**, que paga a sus propios proveedores a
través de Blinka; Blinka en sí no tiene este problema, sus clientes sí
(decisión **D059**, `docs/DECISIONS_LOG.md`).

## El problema

Un equipo de finanzas recibe facturas por distintos canales (PDF, imagen,
correo, chat) y necesita decidir pagarlas, frenarlas por sospecha de fraude,
o escalarlas a una persona para aprobación — sin que un modelo de lenguaje
tenga la última palabra sobre si el dinero sale.

## Cómo funciona

El flujo completo (extracción → chequeos de reglas → verificador → puerta
final → registro) está documentado como diagrama:

- `docs/02_ARCHITECTURE.md`, heading **`## Flujo (LangGraph)`** (bloque
  mermaid ya existente).
- `docs/diagrams/architecture.md` (diagrama de componentes: frontend, API,
  grafo y almacenamiento).

Este README no copia esos diagramas; enlaza al archivo para no mantener dos
copias de la misma afirmación.

## Garantías de seguridad

Cada afirmación de esta lista tiene fila con ruta exacta en
`JUDGE_GUIDE.md`. Resumen:

- **El LLM nunca decide el pago.** `decide()` es una función pura sobre los
  resultados de los chequeos: `backend/app/rules/decide.py`.
- **Fail-closed.** Error, timeout, JSON inválido o verificador JEV caído
  terminan en ESCALAR, nunca en PAGAR: `backend/app/gate/final_gate.py`.
- **El verificador solo puede subir severidad** (PAGAR < ESCALAR < FRENAR),
  nunca bajarla.
- **Cero pagos indebidos es la vara de medir**: `unsafe_pay > 0` hace fallar
  el CI (`.github/workflows/ci.yml`, paso `eval/run_motor.py`). El despliegue en
  Render no espera al CI, así que el gate está en CI y no en el deploy.
- **Explicación por plantilla**, no texto libre del modelo.
- **PAGAR es un registro y un pago simulado**, no una transferencia real.
- **Cadena de registros con hash**, verificable sin recalcular todo:
  `backend/app/records/chain.py` y `GET /decisions/verify-chain`.
- Batería de escenarios de fraude y duplicados, y suite adversarial,
  corren en CI junto con el resto de pruebas.

## Inicio rápido

Backend (Python 3.11+), desde la raíz del repo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
python -m pytest -q
```

Frontend, desde `frontend/`:

```bash
npm ci
npm run lint
npx tsc --noEmit
npm test
```

(`CONTRIBUTING.md` tiene el detalle completo, incluyendo `python eval/run_motor.py`.)

## Despliegue público

| Pieza | URL |
|---|---|
| API (Render) | `https://blinka-invoice-api.onrender.com` |
| Frontend (Vercel) | `https://blinka-invoice-agent.vercel.app` |

## Qué NO hace

- No mueve dinero real: "PAGAR" es un registro con estado simulado.
- No hace una determinación general de fraude o KYC; aplica un conjunto fijo
  de reglas deterministas sobre la factura.
- No hace OCR sobre facturas en imagen: ese canal falla cerrado
  (`illegible`) en la extracción (`backend/app/extraction/ingest.py`).
- No tiene un buzón de correo real (IMAP/SMTP): el canal "correo" y "chat"
  son texto de entrada simulado, no una integración con un servidor de
  correo.

## Limitaciones conocidas

- **Un solo worker.** El candado que serializa las decisiones dependientes
  del ledger es un lock de proceso; el despliegue debe correr un único
  worker de `uvicorn` (sin `--workers`), no coordina entre réplicas
  (`backend/app/api/app.py`).
- **Identidad sin verificar (hackathon).** El navegador envía el id y el
  correo de Supabase como `X-User-Id` / `X-User-Email` y el API no verifica
  el JWT: quien conozca el id de otro usuario puede actuar como él dentro de
  su empresa (`docs/T9_8_SPEC.md` §5). La empresa de cada usuario sale de
  `company_members` (T9.8); la bandeja de correos sigue por usuario y usa los
  aprobadores de la demo.
- **Nota sobre el holdout.** Durante otra tarea, el *motor* (sin LLM) se
  corrió una vez sobre el holdout como chequeo de regresión; eso no es la
  corrida e2e de holdout que hace T5.1 y no se usó para calibrar nada
  (decisión **D064**, `docs/DECISIONS_LOG.md`).

## Métricas

Sin `eval/reports/latest.md` todavía, ninguna cifra de evaluación se
escribe aquí:

| Celda | Estado |
|---|---|
| Autonomía / `unsafe_pay` (dev y holdout) | `[pendiente T5.1: autonomía dev/holdout de eval/reports/latest.md]` |
| Adversariales (`unsafe_pay`) | `[pendiente T5.3]` |
| `over_escalation`, `reason_accuracy`, `explain_ok`, `blind_read` | `[pendiente T5.1 / T5.4]` |
| `latency_p50`, `cost_per_invoice` | `[pendiente T5.1]` |

## Estado

Ver `docs/TASK_BOARD.md` para el estado real de cada tarea y gate. A la
fecha de este borrador: T5.1 PENDIENTE, T5.5 en borrador de estructura
(esta misma entrega), G5 y G6 PENDIENTE.

## Guía para evaluadores

`JUDGE_GUIDE.md` trae la tabla afirmación → evidencia completa y el modo de
reproducir lo que ya existe.

## Orden de lectura del paquete de contexto original

Estos archivos documentan el diseño original del agente y siguen vigentes
como referencia de arquitectura, aunque el README ya no se presenta como
paquete de fase F0:

| # | Archivo | Para qué sirve |
|---|---|---|
| 0 | `docs/00_MASTER_PROMPT.md` | Primer mensaje para la IA que implementa. |
| 1 | `AGENTS.md` | Reglas inviolables, orquestación de agentes, protocolo de skills. |
| 2 | `docs/01_CONTEXT_AND_SCOPE.md` | El reto, qué entra y qué no, criterios de éxito. |
| 3 | `docs/02_ARCHITECTURE.md` | Grafo LangGraph, roles de modelos, JEV, verificador, stack. |
| 4 | `docs/03_JUDGE_REVERSE_ENGINEERING.md` | Investigación de jueces-agente en hackathons. |
| 5 | `docs/04_RULES_AND_DECISION_SPEC.md` | Esquema de reglas, catálogo R01–R13, registro de decisión. |
| 6 | `docs/05_PHASES_AND_ROADMAP.md` | Fases, subtareas con ID, gates. |
| 7 | `docs/06_EVAL_AND_TEST_PLAN.md` | Set dorado, casos trampa, métricas, pruebas. |
| 8 | `docs/07_OBSERVABILITY_LANGSMITH.md` | Registro de operaciones con LangSmith. |
| 9 | `docs/08_OPEN_QUESTIONS_AND_ASSUMPTIONS.md` | Supuestos y preguntas abiertas. |

## Variables de entorno (nombres, no valores)

- Render: `PORT` (inyectado), `DATABASE_URL`, `CORS_ORIGINS`, `API_RATE_LIMIT_PER_MINUTE`, `ADMIN_API_KEY`.
- Producción (grafo real): `LLM_API_KEY`, modelos según `.env.example`; `JEV_API_KEY` o plan B (`docs/DECISIONS_LOG.md`). Opcional: `LANGSMITH_API_KEY`.
- Vercel (solo servidor): `API_URL` — origen público del API, sin ruta ni clave.

El navegador usa same-origin (`/api/*` en Next); CORS en el API es allowlist de respaldo.
