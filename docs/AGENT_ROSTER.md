# Roster de agentes

Fecha: 2026-10-16. Dueño: Orquestador. Estado: PROPUESTO, pendiente de confirmación humana.

## Modo de ejecución: SOMBREROS SECUENCIALES — motivo

El IDE puede crear subagentes (`.cursor/agents/*.md`, skill `create-subagent`) y lanzarlos con el mecanismo de tareas. No se crean en este turno.

Una sola persona y la ruta crítica F1 → F2 → F3 → F4 → F5 son secuenciales. Ocho subagentes a la vez multiplican conflictos de archivos. KISS: un agente cambia de sombrero. Un subagente aparte solo si, más adelante, hay dueño distinto y trabajo paralelo de verdad.

Los ocho roles de `AGENTS.md` §5 se mantienen. No se fusionan. Las tareas de invariantes (T2.7), fail-closed (T3.10) y verificador (T3.6) siguen con dueño propio.

| Agente | Dueño de | Skills | Tareas (IDs) | Entradas | Salida / DoD | Entrega a |
|---|---|---|---|---|---|---|
| Orquestador | `docs/05_PHASES_AND_ROADMAP.md`, `docs/SKILLS_MAP.md`, `docs/AGENT_ROSTER.md`, `docs/TASK_BOARD.md`, `docs/DECISIONS_LOG.md`, `docs/AI_USAGE_LOG.md`, `docs/OPEN_QUESTIONS_STATUS.md` | `verification-before-completion` en los gates. Resto NINGUNA | T0.1, T0.2, T0.4, T0.5, T6.3, G0–G6 | Confirmación humana; evidencia de cada dueño | Repo base; gates con prueba; rama congelada | El humano, y el sombrero de la fase siguiente |
| Spec & Data | `data/`, `backend/app/models/`, `docs/DATA_MANIFEST.md`, `docs/PARAMETERS.md` | NINGUNA | T1.1, T1.2, T1.3, T1.4, T1.5, T1.6, T1.7 | `docs/04`, parámetros confirmados o PROPUESTOS | Esquemas congelados; contratos; facturas; `golden.json` con extracción verdadera y segunda lectura | Rules Engine y QA & Eval. Cambios de esquema posteriores: solo con aprobación del Orquestador |
| Rules Engine | `backend/app/rules/`, `backend/app/records/`, `backend/tests/rules/` | `test-driven-development`, `python-testing-patterns` | T2.1, T2.2, T2.3, T2.4, T2.5, T2.6 | Modelos congelados; `rules.json`; extracción verdadera | R01–R13 puras; `decide()` pura; plantillas; ledger determinista | QA & Eval (para T2.7 y T2.8) y Agent Graph |
| Agent Graph | `backend/app/graph/`, `backend/app/extraction/`, `backend/app/jev/`, `backend/app/verifier/`, `backend/app/config.py` | `langgraph-fundamentals` solo en T3.7. Resto de sus tareas: NINGUNA | T0.3, T3.1, T3.2, T3.3, T3.4, T3.5, T3.6, T3.7, T3.8, T3.9 | G0; motor de Rules Engine; contratos confirmados | Grafo e2e fail-closed; `DecisionClient`; verificador que solo sube severidad; CLI; `run_id` en el registro | QA & Eval y API. `config.py` no lo edita API |
| API | `backend/app/api/`, módulos SQLAlchemy de persistencia (ruta por crear, fuera de `models/` y de `config.py`), `backend/tests/api/` | `api-engineer` (PARCIAL). En T4.9, skills de Render si el SUPUESTO se confirma | T4.1, T4.2, T4.9 (mitad backend) | Esquemas de F1; grafo de F3 | OpenAPI; persistencia; URL del backend | Frontend, cuando el contrato OpenAPI exista |
| Frontend | `frontend/` | `frontend-design` (TOTAL); `vercel-react-best-practices` (PARCIAL) | T4.3, T4.4, T4.5, T4.6, T4.7, T4.8, mitad Vercel de T4.9 | OpenAPI, aunque el backend aún no persista | Pantallas de reglas, decisiones, detalle, aprobaciones y métricas | Orquestador para G4 |
| QA & Eval | `backend/app/gate/`, `backend/tests/gate/`, `backend/tests/adversarial/`, `eval/` | `python-testing-patterns`; `test-driven-development` en T2.7 | T2.7, T2.8, T3.10, T5.1, T5.2, T5.3, T5.4 | Motor; grafo; set dorado y holdout | `final_gate` en `backend/app/gate/`; invariantes verdes; `unsafe_pay = 0`; `eval/reports/latest.md` | Orquestador (G2, G3, G5) y Docs & Judge |
| Docs & Judge | `README.md`, `JUDGE_GUIDE.md`, `docs/examples/records/`, `docs/DEMO_SCRIPT.md` | `drawio-skill` PARCIAL en T5.5; `verification-before-completion` en T5.6; `sales-enablement` PARCIAL en T6.1 | T5.5, T5.6, T6.1, T6.2 | Reporte de eval y tests ya verdes | Cada afirmación apunta a un archivo, un test o un reporte | Orquestador para G5 y G6 |

`T4.8` no parte archivos: el `POST /invoices` es de API (T4.1); la pantalla es de Frontend.

`T4.9` no parte el criterio de un dueño por archivo: `render.yaml` y el servicio backend son de API; la configuración de Vercel bajo `frontend/` es de Frontend. La fila del tablero lleva dueño API y la nota de la mitad Vercel.

## Paralelismo

| Tareas paralelas | Condición |
|---|---|
| T0.1 y T0.3 | Ninguna escribe los archivos de la otra. T0.3 solo necesita claves en el entorno local, no en el repo. |
| T1.1, T1.4 y T1.5 | Tras existir la carpeta `data/`. T1.6 espera reglas y contratos (protocolo de `docs/06`). |
| T2.7 (tests que deben fallar) en paralelo con T2.3–T2.6 | Solo después de G1, con la firma de `decide()` y `CheckResult` congelada. T2.8 espera el motor verde. No comparten archivos: QA escribe `backend/tests/gate/` y `backend/app/gate/`; Rules Engine escribe `backend/tests/rules/` y `backend/app/rules/`. |
| T4.3–T4.7 en paralelo con T4.2 | Cuando T4.1 ha publicado el contrato OpenAPI. El frontend usa datos de ejemplo con esa forma. No edita `backend/`. |
| T5.4 | Puede hacerse en cuanto haya 5 registros de ejemplo. No bloquea el motor. Sí bloquea el claim de explicabilidad en G5. |

Skill de esa ventana, si se lanza un subagente: `dispatching-parallel-agents`.

## Ruta crítica

F0 (T0.3, las APIs) habilita F3, pero la cadena de producto es:

**F1 (datos y contratos) → F2 (motor) → F3 (grafo) → F4 (UI) → F5 (eval).**

Dentro de esa cadena, el cuello es: T1.3 congelar modelos → T1.7 extracción verdadera → T2.5 `decide()` → T2.8 runner → T3.7 grafo → T4.1 OpenAPI → G4 URL → T5.1 reporte.

F6 no está en la ruta crítica de producto. No empieza sin G5.

## Fusiones de roles propuestas y motivo

Ninguna. Cada rol tiene carpetas distintas. Rules Engine y QA & Eval comparten familia de skill, pero pueden trabajar en paralelo sin tocarse y las tareas de seguridad no se fusionan. Spec & Data no tiene skill: aun así no se funde con Rules Engine, porque el esquema se congela antes de implementar y un solo sombrero tendería a cambiar modelos a mitad de F2.

## Subagentes propuestos (no crear todavía)

El IDE los aceptaría en `.cursor/agents/`. Contenido listo, sin archivo creado.

### `frontend-ui` — solo durante F4, tras el OpenAPI

```markdown
---
name: frontend-ui
description: Construye solo frontend/ de Blinka (reglas, decisiones, detalle, aprobaciones, métricas) contra el OpenAPI ya publicado. Usar cuando T4.1 está cerrado y T4.2 sigue en curso.
---

Eres el sombrero Frontend. Lee AGENTS.md, docs/04 y docs/SKILLS_MAP.md.
Antes de escribir UI, lee ~/.agents/skills/frontend-design/SKILL.md.
Dueño exclusivo: frontend/. No edites backend/, data/ ni docs de seguimiento.
La decisión y la explicación vienen del API. No calcules PAGAR en el cliente.
Textos de interfaz en español. Datos solo sintéticos.
Al terminar, lista archivos, cómo se probó en el navegador y qué queda bloqueado.
```

### `qa-invariants` — solo durante F2, tras G1

```markdown
---
name: qa-invariants
description: Escribe tests de invariantes I1–I4 en backend/tests/ contra decide() congelado, sin implementar reglas. Usar tras G1, en paralelo con Rules Engine.
---

Eres QA & Eval. Lee AGENTS.md y docs/04 §1 y §7.
Antes de escribir, lee la skill test-driven-development y python-testing-patterns.
Dueño exclusivo: backend/app/gate/, backend/tests/gate/ y eval/. No implementes reglas ni cambies modelos.
Un test debe fallar si decide() devuelve PAGAR con algún chequeo no OK o indeterminado.
Fail-closed y el verificador que no baja severidad se prueban aquí, no se implementan aquí.
```

No hay más subagentes. El verificador sigue dentro del sombrero Agent Graph (T3.6) y no se delega a un agente que pueda relajar I4.
