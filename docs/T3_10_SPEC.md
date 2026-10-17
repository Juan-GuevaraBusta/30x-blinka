# Spec T3.10 — Fakes fail-closed: LLM roto, JEV expirado, JSON inválido → ESCALAR

Dueño: **QA & Eval**. Skills: `python-testing-patterns` (TOTAL) y `test-driven-development`. No usar `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que implemente T3.10. No cierra la tarea hasta que los criterios de aceptación pasen.

Decisión que fija este contrato: **D026**.

## 0. Para el agente que implementa

Leer antes de tocar código:

- `AGENTS.md` (I1, I2, I3, I6, I8)
- `docs/06_EVAL_AND_TEST_PLAN.md` pirámide, fila «Fail-closed con fakes»
- `docs/T3_7_SPEC.md` §8 (envoltura de nodos) y §10.2
- `docs/DECISIONS_LOG.md` D006, D008, D023, D026
- Este archivo

No leer `.env`. No llamar a la red. No llamar `get_llm`. No construir un `Client` de LangSmith. No leer `langgraph-fundamentals` salvo que un test falle y haya que diagnosticar el grafo; aun así, **no editar** el grafo en esta tarea.

Ruta canónica del archivo: `backend/tests/gate/test_fail_closed.py` (D008). `docs/03` cita `backend/tests/test_fail_closed.py`. Esa ruta está vieja. No crear el archivo ahí. No corregir `docs/03` en esta tarea (eso es T5.5).

## 1. Qué es T3.10

Pruebas de I3 sobre el grafo ya cableado (T3.7). Dobles inyectados en `GraphDeps`. Cada fallo de modelo o de JEV sale como `DecisionRecord` con `decision == "ESCALAR"`. `run_invoice` no propaga la excepción.

`docs/06` pide cuatro situaciones. Las tres del tablero más la de baja confianza:

| Caso | Dónde se inyecta | Qué debe salir |
|---|---|---|
| LLM roto | `extractor.complete_json` lanza `DecisionClientError("http_error")` | ESCALAR, `"error_tecnico"` en `summary`, `severity == 1`, `admin_notice is None` |
| JSON inválido del extractor | `extractor.complete_json` devuelve un valor que no es `dict` (una `list`) | igual: ESCALAR + `error_tecnico` |
| JEV expirado | extracción y contrato siguen el camino feliz; `jev.ask` lanza `DecisionClientError("http_error")` | igual. El verificador no se llama |
| JSON inválido del verificador | camino que sin ese fallo sería PAGAR; `verifier.complete_json` devuelve una `list` | ESCALAR + `error_tecnico`. No queda PAGAR |
| Probabilidad baja | señales J1–J4, J6 y J7 con `answer=True` y `probability=0.1` (umbral del fixture 0.5) | ESCALAR por R09. `summary` no contiene `error_tecnico`. `admin_notice is None` |

El timeout real de `DecisionClient` ya se traduce a `DecisionClientError("http_error")` (`backend/app/jev/decision_client.py`). El fake de «JEV expirado» lanza ese mismo código. No abrir sockets. No inventar un código `timeout`.

T3.7 ya tiene un test de extractor que lanza (`test_extractor_exception_escalar`) y otro de verificador que lanza sobre un FRENAR (`test_frenar_preserved_when_verifier_raises`). No borrarlos. T3.10 es el archivo que un juez puede abrir para I3. Cubre los huecos: JSON no-dict, JEV que falla después de extraer, verificador roto en una factura que iba a PAGAR, y baja confianza.

## 2. Fuera de alcance

- Editar `backend/app/graph/`, `extraction/`, `jev/`, `verifier/`, `models/`, `rules/`, `records/`, `gate/`, `config.py`, `llm.py`, `data/`.
- Añadir nodos, cambiar `decide()`, o bajar un FRENAR ya armado.
- CLI, LangSmith real, `eval/reports/` (eso es G3, no esta tarea).
- Cerrar G0 o G3.
- Adversariales de texto (T5.3).
- Depender de `unittest.mock` del grafo entero. El doble es un objeto con `complete_json` o `ask`.

Si un caso de §1 falla contra el código actual: **parar**. Anotar el fallo en `docs/AI_USAGE_LOG.md`. No parchear producción desde el sombrero QA. El dueño del grafo es Agent Graph.

## 3. Archivos

Crear:

- `backend/tests/gate/test_fail_closed.py`

Modificar, solo al cerrar:

- `docs/TASK_BOARD.md` — fila T3.10 a HECHA, con el conteo real de pytest
- `docs/AI_USAGE_LOG.md` — una fila

No crear otro módulo de producto.

## 4. Invariantes que el archivo demuestra

- I1 / I3. Ningún caso de §1 termina en `PAGAR`.
- I2. El doble no elige la decisión. La decisión sale de `run_invoice` → `decide` / `escalate_technical`.
- I6. Ids sintéticos. Una cadena `_SECRET = "test-key"` se lanza dentro de `DecisionClientError` en el caso LLM roto y en el JEV expirado. No aparece en `summary`, `next_step` ni `admin_notice`. El texto de la factura tampoco.
- I8. ESCALAR aquí es un registro. No hay pago.

## 5. Fixture

Copiar un mínimo dentro del archivo de test. No importar helpers privados de `backend/tests/test_invoice_graph.py`.

- Canal `chat`. Texto corto sintético, el mismo espíritu que el PAGAR de T3.7: beneficiario `Demo SA`, `100 USD`, vencimiento `2026-04-01`, destinatario `Blinka Demo`, depto `IT`, número `INV-G1`.
- `RulesConfig` mínimo de T3.7 §10: umbrales JEV `0.5`, beneficiario permitido `Demo SA`, `on_fail` de R01 y R05 y R07 = `FRENAR`, el resto `ESCALAR`.
- Contrato temporal `confirmed: true` con tarifa `100 USD`, para que el camino feliz llegue a JEV y al verificador.
- Extractor de camino feliz: `complete_json` devuelve el dict de extracción con `source_spans` literales del texto, y en la segunda llamada (contrato) el dict de términos. Contar llamadas.
- Verificador de camino feliz: `{"consistent": true, "issues": []}`.
- JEV de camino feliz: J1–J4, J6, J7 con `answer=True`, `probability=0.99`. J5 puede ir o no; si va, `answer="servicios"`.
- `received_at` con zona UTC. `MemorySaver`. `thread_id` distinto por test.
- `tracer` ausente. `trace.langsmith_run_id is None`.

## 6. Casos (exactos)

Cada test llama `run_invoice` y no usa `pytest.raises` para el fallo del doble: la excepción se queda dentro del grafo.

1. **LLM roto.** `complete_json` del extractor lanza `DecisionClientError("test-key")` en la primera llamada. `decision == "ESCALAR"`, `severity == 1`, `"error_tecnico" in summary`, `admin_notice is None`. `run_invoice` retorna. `"test-key"` y el cuerpo del chat no están en `summary` ni en `next_step`.

2. **JSON inválido.** Primera `complete_json` devuelve `["no-es-objeto"]`. Mismo ESCALAR + `error_tecnico`. El verificador no se llama.

3. **JEV expirado.** Extractor y contrato responden bien. `ask` lanza `DecisionClientError("http_error")`. ESCALAR + `error_tecnico`. `extractor` fue llamado. `verifier` no fue llamado. `"http_error"` no tiene que estar en el summary (el motivo público es `error_tecnico`). `"test-key"` no se usa aquí; el código de error del cliente tampoco se copia al summary.

4. **Verificador con JSON inválido.** Extractor, contrato y JEV van por el camino feliz de §5. `verifier.complete_json` devuelve `["no-es-objeto"]`. `decision == "ESCALAR"`, `"error_tecnico" in summary`, `admin_notice is None`. No es `PAGAR`.

5. **Baja confianza.** Mismo camino feliz, pero cada señal de umbral lleva `probability=0.1`. `decision == "ESCALAR"`. Algún chequeo `R09` no está `OK`. `"error_tecnico" not in summary`. `admin_notice is None`.

6. **Import.** `from app.graph import run_invoice` dentro del módulo de test no abre sockets. Un guard de `socket.socket` durante el import del módulo de test basta. Los cinco casos tampoco llaman a la red: no hace falta un sexto recorrido con socket si el import ya está cubierto y los dobles no usan transporte.

## 7. Qué no afirmar

- No exigir `unsafe_pay` del set dev (G3).
- No exigir un `run_id` de LangSmith.
- No exigir que el summary de los casos 1–4 cite la regla R09.
- No exigir FRENAR en estos cinco casos. El FRENAR que no baja ya está en T3.7.

## 8. Criterios de aceptación

1. Existe `backend/tests/gate/test_fail_closed.py` con los casos §6.1–§6.5.
2. Ningún caso devuelve `PAGAR`.
3. `python -m pytest -q` verde, incluidos los tests previos.
4. `python -m ruff check .` pasa.
5. Cero cambios en `backend/app/` y en `data/`, salvo que el Orquestador autorice un parche del grafo en otra tarea.
6. Tablero: T3.10 HECHA solo con el conteo real. G0 y G3 siguen PENDIENTE.
7. Commit y push: `T3.10: fail-closed fakes escalate instead of paying`.

## 9. Subtareas

- T3.10.1 Escribir `test_fail_closed.py` con el fixture §5 y los casos §6. Correr solo ese archivo.
- T3.10.2 Si algo rojo: parar y anotarlo. Si verde: no tocar producción.
- T3.10.3 `pytest -q` y `ruff check .`.
- T3.10.4 Tablero + `docs/AI_USAGE_LOG.md`. Commit y push con el mensaje de §8.7.

## 10. Mensaje para la sesión que implementa

```text
Implementa T3.10 según docs/T3_10_SPEC.md.
Skills: python-testing-patterns y test-driven-development.
No uses langfuse ni langchain-rag. No llames a la red. No leas .env.
No llames get_llm ni al cliente real de LangSmith.
El archivo es backend/tests/gate/test_fail_closed.py.
No edites graph/, extraction/, jev/, verifier/, models/, rules/,
records/, gate/, config.py, llm.py ni data/.
LLM roto, JSON que no es dict, y JEV que lanza http_error → ESCALAR
con error_tecnico. Probabilidad 0.1 → ESCALAR por R09, sin error_tecnico.
Nunca PAGAR. run_invoice no propaga. Si un test falla, para y anótalo;
no parchees el grafo. No cierres G0 ni G3.
No marques T3.10 HECHA sin pytest y ruff.
Al terminar: commit y push con el mensaje de la sección 8.
```
