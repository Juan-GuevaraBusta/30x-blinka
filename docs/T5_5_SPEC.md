# Spec T5.5 — README, guía de jueces y ejemplos de registro

Dueño: **Docs & Judge**. Skill de la fila: `drawio-skill` (PARCIAL). Este contrato la deja **sin uso**: el diagrama ya está en `docs/02_ARCHITECTURE.md`, heading `## Flujo (LangGraph)`. La tabla afirmación → evidencia no tiene skill (`docs/SKILLS_MAP.md`, fila T5.5). No usar skills de marketing (`sales-enablement`, `copywriting`, `product-marketing` ni el resto de esa familia). `verification-before-completion` es de T5.6, no de esta tarea.

Estado: contrato para la sesión que **implemente** T5.5. Este archivo no cierra la tarea ni cierra G5 ni G6.

Decisión que fija este contrato: **D046**.

T5.5 depende de T5.1 (`docs/TASK_BOARD.md`, fila T5.5). Si T5.1 no está HECHA en el tablero, esta sesión **para** y no completa el README, la guía ni los ejemplos con cifras: la única excepción es un borrador de estructura (encabezados, secciones vacías, el esqueleto de la guía) sin ninguna cifra, ni siquiera la línea base de G3. Verificar en el momento de implementar si `eval/reports/latest.md` ya existe (puede que T5.1 ya lo haya creado); el único reporte en `eval/reports/` al escribir este spec es `g3_closure_2026-10-17.md`. Con T5.1 HECHA y sin `latest.md`, las celdas de métricas quedan en «pendiente T5.1» o citan solo cifras ya escritas en ese reporte y en `docs/DECISIONS_LOG.md` D039, etiquetadas como **línea base G3** (e2e sobre dev), no como holdout.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar archivos:

- `AGENTS.md` (I6 solo datos sintéticos; I8 «PAGAR» no mueve dinero; I9 `unsafe_pay > 0` bloquea el despliegue)
- `README.md` y `JUDGE_GUIDE.md` actuales (el README sigue siendo el índice del paquete; la guía tiene una sola fila «pendiente T5.5»)
- `docs/02_ARCHITECTURE.md`, heading `## Flujo (LangGraph)` (bloque mermaid)
- `docs/03_JUDGE_REVERSE_ENGINEERING.md`, sección «Plantilla de `JUDGE_GUIDE.md`»
- `docs/04_RULES_AND_DECISION_SPEC.md` §5 y §6
- `docs/06_EVAL_AND_TEST_PLAN.md`, sección «Métricas» y «Reporte (`eval/reports/latest.md`)»
- `docs/SKILLS_MAP.md` fila T5.5 y `docs/AGENT_ROSTER.md` fila Docs & Judge
- `docs/05_PHASES_AND_ROADMAP.md` tarea T5.5 y la definición de G5 (no cerrarlo)
- `backend/app/models/domain.py` clase `DecisionRecord` (campos y `severity`)
- `backend/tests/gate/conftest.py` función `minimal_record` (forma real, no copiar el registro de 13 chequeos al spec)
- `backend/app/records/templates.py` y `backend/tests/rules/test_record_templates.py`
- `eval/reports/g3_closure_2026-10-17.md` y la fila D039 de `docs/DECISIONS_LOG.md`

Declarar en una línea: skill **ninguna**. No leer `drawio-skill`. No leer `.env`. No abrir `data/golden/holdout.json` ni `data/invoices/holdout/`.

No editar `backend/`, `data/`, `eval/`, `frontend/` ni `docs/DEMO_SCRIPT.md`. Si hace falta un endpoint, un número que no esté en el reporte G3, o un diagrama nuevo para que el README se entienda, **parar**.

G5 y G6 siguen PENDIENTE. T5.6 es la auditoría que borra afirmaciones sin archivo. T5.5 deja las rutas; no da por comprobado el repo entero.

## 1. Qué es T5.5

Tres entregas en español, para una persona que evalúa el repo sin leer el código primero:

| Pieza | Qué hace |
|---|---|
| `README.md` | Entrada del juez: qué hace el agente, cómo arrancarlo, qué no hace, dónde está el flujo, y las métricas con fuente |
| `JUDGE_GUIDE.md` | Tabla afirmación → evidencia. Cada frase del README que un juez pueda citar tiene aquí una ruta |
| `docs/examples/records/` | Tres registros sintéticos, uno por decisión: PAGAR, FRENAR, ESCALAR |

El README deja de presentarse como paquete en fase F0. El orden de lectura de `docs/00`–`docs/08` puede quedar debajo, porque esos archivos siguen en el repo. La sección «Estado» del README actual (F0, G0 abierto) no se conserva: apunta a `docs/TASK_BOARD.md`.

Los ejemplos ilustran la forma de `DecisionRecord` y las plantillas de `docs/04` §6. No son filas del corrido de 34 facturas.

## 2. Fuera de alcance

- Reescribir `docs/02`, `docs/04`, `docs/06` o `AGENTS.md`.
- Crear `docs/DEMO_SCRIPT.md` (T6.1) ni grabar la demo (T6.2).
- Cerrar G5 o G6. Marcar T5.6, T5.1, T5.3 o T5.4 como hechas.
- Abrir el holdout, calibrar umbrales (T5.2) o escribir `eval/reports/latest.md` (T5.1).
- Inventar `unsafe_pay`, autonomía, `over_escalation`, latencia o `cost_per_invoice`.
- Añadir un `.drawio` o copiar el mermaid a otro archivo.
- Editar backend, modelos, tests, `data/`, `eval/` o `frontend/`.
- Pegar secretos, volcar `.env`, o armar URLs con usuario, clave o token.
- Afirmar que un ejemplo es la traza LangSmith de `dev-001`.

## 3. Archivos

Modificar:

- `README.md`
- `JUDGE_GUIDE.md`
- Al cerrar la implementación: `docs/TASK_BOARD.md` (fila T5.5) y una línea en `docs/AI_USAGE_LOG.md`

`docs/DECISIONS_LOG.md` es del Orquestador. D046 queda fijada por este spec; esta tarea no reescribe el log.

Crear, un JSON por id:

- `docs/examples/records/ex-pagar.json`
- `docs/examples/records/ex-frenar.json`
- `docs/examples/records/ex-escalar.json`

No crear un cuarto relato ni un `.drawio`. La guía apunta a los tres JSON.

## 4. Claims mínimos

La guía conserva el esqueleto de `docs/03` (cómo ejecutar, qué hace y qué no hace, tabla, cómo reproducir métricas, limitaciones). La tabla de abajo es el mínimo. Cada fila del README que un juez pueda citar se añade aquí con una ruta, o no se escribe en el README.

T5.6 comprobará que el archivo existe y dice eso. T5.5 usa estas rutas porque ya están en el repo. Si al implementar una ruta no coincide, se borra la afirmación; no se sustituye por una promesa.

| Afirmación (español, citable) | Dónde verificarla |
|---|---|
| El LLM no decide el pago; `decide()` es función pura de los chequeos | `backend/app/rules/decide.py`; `backend/tests/rules/test_decide.py` (`test_i2_decide_module_has_no_llm_imports`) |
| No hay PAGAR si algún chequeo falla o está indeterminado | `AGENTS.md` I1; `backend/tests/gate/test_invariants.py`; `backend/tests/rules/test_decide.py` |
| Error, timeout, JSON inválido o JEV caído termina en ESCALAR | `AGENTS.md` I3; `backend/tests/gate/test_fail_closed.py` |
| El verificador solo sube severidad (PAGAR < ESCALAR < FRENAR) | `AGENTS.md` I4; `backend/tests/gate/test_invariants.py` (`test_apply_verifier_floor_does_not_lower_frenar`) |
| La explicación sale de plantillas, no de texto libre del modelo | `docs/04_RULES_AND_DECISION_SPEC.md` §6; `backend/app/records/templates.py`; `backend/tests/rules/test_record_templates.py` |
| «PAGAR» es un registro y un pago simulado | `AGENTS.md` I8; `backend/app/records/build.py` (`build_next_step` devuelve «Pago simulado registrado.») |
| Solo datos sintéticos; la empresa de ejemplo es Acme Demo Inc. | `AGENTS.md` I6; `data/company.json` |
| R13 detecta una lista fija de frases (`backend/app/rules/checks.py`, `R13_PHRASES`); no cubre otros idiomas ni variantes | `AGENTS.md` I7; `backend/app/rules/checks.py` (`R13_PHRASES`); `backend/tests/rules/test_rules_r01_r13.py` (`test_r13_fail_injection_dev031`). La suite adversarial de T5.3 sigue pendiente: no se afirma el gate |
| La API no exige autenticación en los endpoints mutantes hasta T5.9 | `docs/TASK_BOARD.md` fila T5.9 (PENDIENTE, D055). Limitación conocida, no un gate ya cerrado |
| Hay una condición de carrera en el límite de periodo del ledger hasta T5.8 | `docs/TASK_BOARD.md` fila T5.8 (PENDIENTE, D055). Limitación conocida, no un gate ya cerrado |
| Línea base G3, e2e dev: `unsafe_pay = 0` | `eval/reports/g3_closure_2026-10-17.md`; `docs/DECISIONS_LOG.md` D039. Etiqueta obligatoria: línea base G3, no holdout |
| Línea base G3, e2e dev: autonomía 55.9 % (19/34) | Los mismos dos archivos, con la misma etiqueta. No presentarla como autonomía del motor |
| Referencia de motor G2, extracción verdadera, dev: 34/34, autonomía 100.0 %, `unsafe_pay = 0` | Solo la línea que el reporte G3 llama «referencia motor G2», más `docs/DECISIONS_LOG.md` D028. No es la autonomía del grafo |
| `unsafe_pay > 0` bloquea el despliegue | `AGENTS.md` I9; `docs/06_EVAL_AND_TEST_PLAN.md` sección «Gates de calidad». El número de holdout no se rellena aquí |
| Flujo del grafo | `docs/02_ARCHITECTURE.md`, heading `## Flujo (LangGraph)` |
| Reglas configurables | `data/rules.json`; `frontend/app/reglas/` |
| Hay ficha de decisión en la UI | `frontend/app/decisiones/[id]/` |
| Demo en URL pública (G4) | Las dos URLs de producto ya escritas en el README actual: `https://blinka-invoice-api.onrender.com` y `https://blinka-invoice-agent.vercel.app`. Recorrido: fila G4 de `docs/TASK_BOARD.md`. G5 no está cerrado |
| Tres ejemplos de registro, sintéticos | `docs/examples/records/ex-pagar.json`, `ex-frenar.json`, `ex-escalar.json` |

Métricas de `docs/06` que este README no numera mientras falte `eval/reports/latest.md`:

| Celda | Texto |
|---|---|
| Holdout (`unsafe_pay`, autonomía) | pendiente T5.1 |
| Adversariales (`unsafe_pay`) | pendiente T5.3 (el gate G5 los pide junto con el reporte) |
| `over_escalation`, `reason_accuracy`, `explain_ok`, `blind_read` | pendiente T5.1 o T5.4, según la fila de `docs/06`. No calcular un porcentaje nuevo a partir del relato de desvíos |
| `latency_p50`, `cost_per_invoice` | pendiente T5.1. No hay cifra en el reporte G3 |
| `eval/run_eval.py` | Verificar al implementar si el archivo ya existe (T5.1 puede haberlo creado). Si no existe todavía, la guía no manda ejecutarlo. Reproducir el motor: el comando ya escrito en `docs/G2_SPEC.md` (`python eval/run_motor.py`). El e2e de G3 se cita por el reporte, no se reinventa un comando |

Si al implementar **sí** existe `eval/reports/latest.md`, las celdas de dev y holdout copian esa tabla, dev y holdout por separado, y dejan de usar la línea base G3 como si fuera el resultado final. Este spec no anticipa esos números.

Otras cifras del reporte G3 (34/34 con `langsmith_run_id`, `run_id` de muestra de `dev-001`) se pueden citar solo si la frase dice que salen de ese archivo y nombra la factura `dev-001`. Ese `run_id` no se pega en los JSON de ejemplo.

URLs: las únicas públicas que el README puede repetir son las que ya están hoy (`https://render.com`, la del API y la del frontend de la tabla «Despliegue público»). No añadir otra. No añadir query con credenciales. `API_URL` y las claves siguen descritas por nombre, como ya hace el README.

## 5. Ejemplos de registro

Un archivo JSON por decisión. Cada uno tiene que pasar `DecisionRecord.model_validate` (`backend/app/models/domain.py`: `extra` prohibido, `severity` 0 PAGAR, 1 ESCALAR, 2 FRENAR).

Campos, en este orden, tomados de la clase y del ejemplo de `docs/04` §5 (el de §5 es el esquema; los tres archivos no copian ese JSON de umbral tal cual):

| Campo | Regla para los tres archivos |
|---|---|
| `id` | `ex-pagar`, `ex-frenar`, `ex-escalar` |
| `invoice_id` | El mismo id, para no chocar con `dev-*` ni con `dec_0042` |
| `received_at` | Datetime con zona. Usar `2026-03-04T10:15:00Z` (ya está en `minimal_record` y en `docs/04` §5) |
| `decision` / `severity` | Una de las tres parejas. El validador rechaza el desajuste |
| `summary` | Salida de plantilla, en español. Ver la fila de cada archivo |
| `extracted` | Subconjunto de `Extraction`. Beneficiario, monto, moneda, `amount_base`, `due_date`, `invoice_number`, `recipient` = Acme Demo Inc., `department` si la plantilla lo usa. Sin datos reales |
| `checks` | Lista de `CheckResult` (`rule`, `name`, `result`, `detail`, `on_fail` si falla). El `{n}` de la plantilla PAGAR es `len(checks)` |
| `jev_signals` | Las cinco señales booleanas de `_signals()` en `test_record_templates.py`: J1, J2, J3, J4, J7, `answer` true, `probability` 0.99. Sin inventar J5 ni J6 |
| `verifier` | `{"consistent": true, "issues": []}`. Estos tres casos los decide la regla, no un hallazgo del verificador |
| `admin_notice` | `null` en PAGAR y en ESCALAR. En FRENAR, la cadena de `build_admin_notice` (`TEMPLATE_ADMIN_NOTICE`) |
| `next_step` | La cadena de `build_next_step` para esa decisión |
| `trace` | `langsmith_run_id` sintético `ejemplo-no-es-traza` y `url` null. No es el `run_id` de `dev-001` |
| `versions` | Las de `minimal_record`: `rules_version` `v1`, `model_extractor` `extractor-demo`, `model_verifier` `verifier-demo`, `jev` `jev-1.13.0` |
| `human_events` | `[]` |

No hace falta volcar aquí los 13 chequeos. La sesión que implementa los obtiene de los tests ya verdes, sin redactar otra frase:

| Archivo | Escenario ya afirmado en test | `summary` y `next_step` |
|---|---|---|
| `ex-pagar.json` | `test_pagar_summary_thirteen_ok_checks` y `test_next_step_pagar`: Globex LLC, USD 800, vence 2026-05-27, 13 chequeos OK | «Pagada: cumple todas las reglas (13 chequeos). Monto USD 800, vence 2026-05-27.» y «Pago simulado registrado.» |
| `ex-frenar.json` | `test_r01_frenar_summary_and_admin_notice`: beneficiario «Nuevo Socio Fantasma SAS», R01 en FALLA con `on_fail` FRENAR | La frase exacta de ese test (empieza por «Frenada:» y cita R01). `next_step`: «Se notificó al administrador; no procede el pago automático.» `admin_notice` no vacío, con el id, el beneficiario y R01, vía `TEMPLATE_ADMIN_NOTICE` |
| `ex-escalar.json` | `test_r04_escalar_summary_at_threshold` y `test_next_step_escalar_r04_uses_approver`: USD 4200, umbral USD 3000, departamento Ingenieria, R04 en FALLA con `on_fail` ESCALAR | «Escalada: USD 4200 llega al umbral de aprobación humana de USD 3000 (regla R04).» y «Pendiente de aprobación de finanzas@demo.test.» |

Esos tres textos ya están en el test. El JSON los repite; no los parafrasea. El resto de chequeos OK del escenario puede ir en el archivo para que el recuento de PAGAR siga siendo 13. Un PAGAR con un solo chequeo y la frase «13 chequeos» no vale.

La guía dice, junto a los tres enlaces, que son ejemplos sintéticos de plantilla, no el corpus de G3.

Comprobación (sin tocar backend):

```bash
PYTHONPATH=backend python -c "
import json
from pathlib import Path
from app.models.domain import DecisionRecord
root = Path('docs/examples/records')
for name in ('ex-pagar.json', 'ex-frenar.json', 'ex-escalar.json'):
    DecisionRecord.model_validate(json.loads((root / name).read_text()))
print('ok')
"
```

## 6. Diagrama

**No hay diagrama draw.io.**

El README enlaza el mermaid que ya existe, con el heading, por ejemplo: el flujo está en `docs/02_ARCHITECTURE.md`, sección «Flujo (LangGraph)». No se copia el bloque a `README.md` ni a la guía: dos copias serían dos afirmaciones que mantener.

`drawio-skill` no se lee y no se produce ningún `.drawio`. Solo se reabriría esa skill si el README no pudiera señalar ese heading. Puede señalarlo. La fila del tablero ya dice que el diagrama es opcional y que el mermaid de `docs/02` puede bastar.

## 7. Qué no afirmar

- Que G5 o G6 están cerrados, o que el README ya pasó la auditoría de T5.6.
- Que `unsafe_pay = 0` en holdout o en adversariales.
- Que la autonomía del grafo es 100 %. Ese 100 % es el motor con extracción verdadera (G2).
- Que 55.9 % (19/34) es el resultado de holdout o el número final de F5.
- Cualquier coste, latencia o porcentaje que no esté escrito en `eval/reports/g3_closure_2026-10-17.md` o en D039 / D028 con la etiqueta de arriba.
- Que `eval/reports/latest.md` o `eval/run_eval.py` existen, si al verificar en el momento de implementar todavía no existen.
- Que los JSON de ejemplo son decisiones del corrido e2e o la traza `01a14bb0-2259-7c43-a337-fa9afe5f8e94`.
- Que el sistema mueve dinero, detecta fraude en general, o procesa facturas reales.
- Que hay un diagrama editable además del mermaid.
- Una URL que no esté ya en el README actual.

## 8. Criterios de aceptación

0. T5.1 está HECHA en `docs/TASK_BOARD.md` antes de completar README, guía o JSON con cifras. Si no lo está, solo existe el borrador de estructura sin cifras y el resto de estos criterios no aplica todavía.
1. `README.md` y `JUDGE_GUIDE.md` en español. Toda frase del README que un juez pueda citar tiene fila en la guía con ruta de archivo. La fila «pendiente T5.5» desaparece.
2. Sin `latest.md`, las celdas de holdout, coste y latencia dicen «pendiente T5.1». Las únicas cifras de autonomía y `unsafe_pay` del grafo son las de la línea base G3 (0 y 55.9 % con 19/34), etiquetadas así. El 100 % del motor, si aparece, lleva la etiqueta de referencia G2. La guía incluye R13 como lista fija de frases (sin otros idiomas) y las dos limitaciones de T5.8/T5.9.
3. Los tres JSON validan con el comando de la sección 5. PAGAR cita 13 chequeos y trae 13 resultados OK. FRENAR trae `admin_notice`. ESCALAR cita R04 y el correo `finanzas@demo.test`.
4. El diff no contiene `.drawio`, `docs/DEMO_SCRIPT.md`, `.env`, ni archivos bajo `data/golden/holdout.json` o `data/invoices/holdout/`.
5. Diff de `backend/`, `data/`, `eval/` y `frontend/` vacío.
6. `docs/TASK_BOARD.md`: T5.5 HECHA con la nota de los tres JSON y de que el diagrama es el mermaid de `docs/02`. G5 y G6 siguen PENDIENTE.
7. Una línea en `docs/AI_USAGE_LOG.md`: sombrero Docs & Judge, skill ninguna, D046, sin draw.io.
8. Commit: `T5.5: judge README, evidence table, and sample records`. Push a la rama de seguimiento.

## 9. Subtareas

- T5.5.1 `README.md` de entrada para el juez: misión, arranque con los comandos que el README ya documenta (`venv`, `pip install -e ".[dev]"`, `pytest`, `ruff check .`), límites I6 e I8, enlace al heading del mermaid, tabla de métricas según §4, URLs ya existentes, estado vía `docs/TASK_BOARD.md`.
- T5.5.2 `JUDGE_GUIDE.md` con la tabla de §4, el modo de reproducir (sin `eval/run_eval.py`) y las limitaciones de §7.
- T5.5.3 Los tres JSON de §5, frases copiadas de los tests nombrados.
- T5.5.4 Validar los JSON, tablero, `AI_USAGE_LOG.md`, commit y push. No cerrar G5.

## 10. Mensaje para la sesión que implementa

```text
Implementa T5.5 según docs/T5_5_SPEC.md (D046).
Skill: ninguna. No leas drawio-skill ni skills de marketing.
No edites backend/, data/, eval/ ni frontend/. No leas .env.
No abras data/golden/holdout.json ni data/invoices/holdout/.
No escribas docs/DEMO_SCRIPT.md. No cierres G5 ni G6.
Primero: verifica en docs/TASK_BOARD.md si T5.1 está HECHA. Si no lo está,
para y solo entrega un borrador de estructura (encabezados, esqueleto),
sin ninguna cifra, ni la línea base de G3.
Con T5.1 HECHA: README y JUDGE_GUIDE en español. Cada afirmación citable
apunta a un archivo en la tabla del spec. Verifica si eval/reports/latest.md
ya existe; si no, holdout y costes quedan «pendiente T5.1» y las únicas
cifras del grafo son la línea base G3: unsafe_pay=0 y autonomía 55.9%
(19/34), citando eval/reports/g3_closure_2026-10-17.md y D039. No las
llames holdout.
R13: «R13 detecta una lista fija de frases (backend/app/rules/checks.py,
R13_PHRASES); no cubre otros idiomas ni variantes».
Limitaciones a incluir: la API no exige autenticación en endpoints
mutantes hasta T5.9; hay una condición de carrera en el límite de periodo
del ledger hasta T5.8 (ambas PENDIENTE, D055).
Diagrama: enlace al heading «Flujo (LangGraph)» de docs/02_ARCHITECTURE.md.
Cero .drawio.
Tres JSON en docs/examples/records/ (ex-pagar, ex-frenar, ex-escalar),
sintéticos, validados como DecisionRecord, frases de los tests citados en §5.
Al terminar: commit «T5.5: judge README, evidence table, and sample records» y push.
```
