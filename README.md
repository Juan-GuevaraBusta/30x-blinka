# Tachyon — agente de pagos a proveedores (Hackathon 30x · reto Blinka)

> **Estado (T5.5, D046).** `T5.1` (`docs/TASK_BOARD.md`) está **HECHA**. Las
> cifras de este README citan `eval/reports/latest.md` (corrida oficial dev +
> holdout) y `eval/reports/post_t51_dev.md` (rerun de dev tras el arreglo de
> R06/J6, decisión **D068**). El holdout se corrió **una sola vez, antes**
> de ese arreglo, y no se repitió: su autonomía (30.0 %) es anterior a D068.
> `unsafe_pay = 0` en dev, holdout, adversariales y motor. El grafo es
> **conservador**: la mayoría de las facturas que el set dorado espera en
> PAGAR terminan en ESCALAR, sobre todo por la señal JEV J6 bajo umbral y
> por facturas en imagen PNG sin OCR. Ver `JUDGE_GUIDE.md` para la tabla
> completa afirmación → evidencia.

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
`JUDGE_GUIDE.md` for the claim → evidence table.

Metrics (`eval/reports/latest.md`, dev n=34 / holdout n=10): `unsafe_pay = 0`
on both splits; autonomy 55.9% dev / 30.0% holdout. The holdout ran once,
**before** a later fix (D068, `eval/reports/post_t51_dev.md`) that raised
dev autonomy to 61.8% (PAGAR 2/11, `unsafe_pay` still 0) — the holdout was
not re-run after that fix, so its 30.0% figure predates it. The graph is
conservative: most expected-PAGAR invoices still escalate, mainly because
the JEV J6 signal sits below its threshold, or because PNG invoices have
no OCR.

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

## Cuenta de prueba para jueces

Entra en https://blinka-invoice-agent.vercel.app/entrar con:

| Correo | Contraseña | Empresa | Rol |
|---|---|---|---|
| `sebas@pjgorman.com` | `A1b2c3!` | P.J Gorman (ficticia, USD) | Admin y aprobador (grupos finanzas y cfo) |

La cuenta ya tiene configurados la política de aprobación (4 rutas), los proveedores y los acuerdos (Globex LLC mensual fijo, Andesbyte SAS por horas, Cuotasur SAS en cuotas). Para probar, sube desde `/subir` los archivos de [`data/demo/`](data/demo/README.md):

| Archivo | Resultado esperado | Por qué |
|---|---|---|
| `01-globex-mensualidad-octubre.txt` | **PAGAR** | Cuadra con el acuerdo y con todas las reglas |
| `02-globex-mensualidad-octubre-REENVIO.txt` | **FRENAR** | Ya se pagó: duplicado (R05) |
| `03-andesbyte-horas-octubre.txt` | **ESCALAR** | Pago variable por horas: requiere aprobación humana (R19) |

Las tres ya están cargadas en la cuenta con esos resultados (míralas en `/decisiones`). Si vuelves a subir cualquiera de ellas, el agente la frena por duplicado (R05): esa es la protección que impide pagar dos veces.

En `/decisiones/[id]` cada decisión muestra los chequeos, la explicación y el enlace a su traza en LangSmith. La cuenta es solo de demostración, con datos sintéticos; no la uses para nada más.

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
  corrió una vez sobre el holdout como chequeo de regresión, sin usarlo
  para calibrar nada (decisión **D064**, `docs/DECISIONS_LOG.md`). La
  corrida e2e del grafo sobre el holdout (T5.1, `eval/reports/latest.md`)
  se hizo una sola vez, **antes** del arreglo de R06/J6 (decisión **D068**,
  `eval/reports/post_t51_dev.md`); no se volvió a correr, así que su
  autonomía (30.0 %) es anterior a ese arreglo.

## Métricas

Fuente: `eval/reports/latest.md` (corrida oficial `eval/run_eval.py
--output eval/reports/latest.md --include-holdout`, 2026-10-18) y
`eval/reports/post_t51_dev.md` (rerun de solo-dev tras el arreglo de
R06/J6, decisión **D068**, `docs/DECISIONS_LOG.md`).

| Split | n | `unsafe_pay` | Autonomía | `over_escalation` | `reason_accuracy` | `explain_ok` |
|---|---|---|---|---|---|---|
| dev (oficial, `latest.md`) | 34 | 0 | 55.9 % (19/34) | 100.0 % | 14.7 % | 100.0 % |
| dev (tras arreglo R06/J6, `post_t51_dev.md`, D068) | 34 | 0 | 61.8 % (PAGAR 2/11) | 81.8 % | 47.1 % | 100.0 % |
| holdout (`latest.md`, corrida única, **antes** de D068) | 10 | 0 | 30.0 % | 100.0 % | 10.0 % | 100.0 % |

El grafo es conservador: en la corrida oficial, 0 de 11 facturas que el set
dorado espera en PAGAR llegan a PAGAR (las 11 escalan). Tras el arreglo
R06/J6 (D068) eso sube a 2/11 en dev; de las 9 que siguen sin pagar, 6
escalan porque la señal JEV J6 queda bajo su umbral (juicio no
determinista de JEV) y 3 son facturas en imagen PNG sin OCR. El holdout no
se volvió a correr después de ese arreglo, así que su 30.0 % sigue siendo
la cifra **previa**.

| Celda | Estado |
|---|---|
| Adversariales (`unsafe_pay`) | 0; 8/8 casos no-PAGAR — `eval/reports/adversarial.md` |
| Referencia de motor (extracción verdadera, sin LLM) | dev 34/34, f7 16/16, `unsafe_pay = 0` — `eval/reports/metrics_summary.json` |
| `blind_read` | `[pendiente T5.4]` |
| `latency_p50`, `cost_per_invoice` | `[pendiente T5.1: no está en eval/reports/latest.md]` |

## Estado

Ver `docs/TASK_BOARD.md` para el estado real de cada tarea y gate. A la
fecha de esta entrega: T5.1, T5.3, T5.5 y T5.6 **HECHA**; G5 y G6 siguen
**PENDIENTE** (su cierre es decisión del Orquestador, no de esta entrega).

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
