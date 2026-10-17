# Spec T3.8 — Traza LangSmith y `run_id` en el registro

Dueño: Agent Graph. Skill de dominio: **NINGUNA** (`docs/SKILLS_MAP.md`). Proceso: `test-driven-development` y `python-testing-patterns`. No usar `langfuse` ni `migrate-to-langfuse` (D004). No usar `langchain-rag`.

Estado: contrato para la sesión que implemente T3.8. No cierra la tarea hasta que los criterios de aceptación pasen.

Decisión que fija este contrato: **D024**.

## 0. Para el agente que implementa

Leer antes de tocar código:

- `AGENTS.md` (I2, I3, I6, I8)
- `docs/07_OBSERVABILITY_LANGSMITH.md` (dos capas, variables, metadatos, privacidad)
- `docs/02_ARCHITECTURE.md` fila de trazabilidad
- `docs/T3_7_SPEC.md` §2 y §8.9–§8.10 (hoy `TraceRef()` va vacío)
- `docs/DECISIONS_LOG.md` D004, D023, D024
- Este archivo

No leer `langchain-rag`. No leer la skill `langfuse`. No llamar a la red. No leer `.env`. No llamar `get_llm`. No construir un `Client` real de LangSmith en tests.

No editar `backend/app/models/`, `backend/app/rules/`, `backend/app/records/`, `backend/app/gate/`, `backend/app/llm.py`, `backend/app/extraction/`, `backend/app/jev/`, `backend/app/verifier/`, `data/`. `TraceRef` ya existe. No se cambia el esquema.

`backend/app/config.py` sí se toca, solo para las cuatro claves de §5. El resto de `Settings` queda igual.

No cerrar G0. No implementar T3.9 (CLI), T3.10, datasets de LangSmith ni feedback humano.

Si hace falta mover aristas del grafo, parar. T3.8 no añade nodos. Si se toca `StateGraph` o `Command`, releer `langgraph-fundamentals` y no añadir `add_edge` junto a un `Command`.

## 1. Qué es T3.8

El grafo de T3.7 sigue decidiendo igual. T3.8 solo rellena `DecisionRecord.trace` cuando hay una sesión de traza, y deja los dos campos en `None` cuando no la hay.

`docs/07` separa dos capas. El registro sigue siendo la fuente de la decisión. LangSmith es depuración. La UI no la necesita para explicar el pago.

Una factura, una traza raíz. Los nodos que LangGraph ya ejecuta quedan como hijos si el SDK traza el grafo. No se crea un nodo `trace`.

## 2. Fuera de alcance

- Llamada real a LangSmith (eso es T0.3, sigue bloqueado).
- Datasets, experimentos y evaluadores de `docs/07` § «Evaluación».
- Adjuntar `human_events` como feedback.
- CLI y `decisions.json` (T3.9). T3.9 será quien pase el tracer real armado con `Settings`.
- `backend/tests/gate/test_fail_closed.py` (T3.10).
- Cambiar `decide`, `verify_decision`, `run_final_gate` o el orden de nodos (D023).
- Cerrar G0 o G3.

## 3. Archivos

Crear:

- `backend/app/graph/tracing.py` — protocolo `TraceSession`, `NullTrace`, `make_langsmith_session`

Modificar:

- `backend/app/graph/build.py` — `run_invoice` acepta la sesión y rellena `trace` al volver
- `backend/app/graph/__init__.py` — reexportar lo de §6. Sin efectos al importar
- `backend/app/config.py` — cuatro campos. No cambiar validadores ya existentes
- `backend/tests/test_config.py` — la clave LangSmith deja de ser el ejemplo de «clave ajena»
- `pyproject.toml` — una sola dependencia nueva de runtime: `langsmith`

Tests nuevos:

- `backend/tests/test_tracing.py`

No crear `docs/examples/records/` (eso es T5.5). El registro de ejemplo vive en §10.1 de este spec y en el test.

## 4. Invariantes

- I2. La traza no pide una decisión al modelo. No se llama `get_llm`.
- I3. Un fallo de traza **no** es fallo de pago. No se convierte en `error_tecnico`, no se añade a `errors`, no cambia `decision` ni `severity`. La excepción de un nodo de negocio sigue el camino de T3.7.
- I6. Tests con ids sintéticos. Prohibido pegar una clave real, un `LANGSMITH_API_KEY` del entorno, o el texto de la factura dentro de metadatos de ejemplo que se impriman.
- I8. Rellenar `trace` no mueve dinero.

## 5. Configuración

Añadir a `Settings` y a `_ENV_KEYS`, con estos defaults si la clave falta:

| Variable | Campo | Default |
|---|---|---|
| `LANGSMITH_TRACING` | `langsmith_tracing` | `False` |
| `LANGSMITH_API_KEY` | `langsmith_api_key` | `""` |
| `LANGSMITH_PROJECT` | `langsmith_project` | `blinka-invoice-agent-dev` |
| `LANGSMITH_ENDPOINT` | `langsmith_endpoint` | `""` |

`LANGSMITH_TRACING` usa el mismo parser que `POLISHER_ENABLED`. Valor distinto de `true`/`false` → `ConfigError("invalid_bool")`.

`load_settings` sigue leyendo `os.environ`. No carga archivo `.env`.

`test_settings_ignores_unrelated_env_keys` hoy mete `LANGSMITH_API_KEY` como clave que no debería entrar. Al mapearla, ese ejemplo deja de ser ajeno. Sustituir esa clave del test por otra que siga ignorada (por ejemplo `UNRELATED_TOKEN`). `PATH` sigue ignorada. Añadir un test nuevo que, con las cuatro variables, deja los cuatro campos. No imprimir el valor de la clave.

## 6. API

```python
class TraceSession(Protocol):
    def open_config(self, *, metadata: dict[str, str], tags: list[str]) -> dict: ...
    def finish(self, decision: str) -> TraceRef | None: ...


class NullTrace:
    """open_config devuelve {}. finish devuelve None. No lanza."""


def make_langsmith_session(settings: Settings) -> TraceSession:
    """Si tracing es falso o la clave está vacía: NullTrace.
    Si no: sesión que usa el SDK. No se llama en los tests de este spec.
    """
```

`run_invoice` gana dos argumentos con default, para no romper T3.7:

```python
def run_invoice(
    ...,
    tracer: TraceSession | None = None,
    phase: Literal["dev", "eval", "demo"] = "dev",
) -> DecisionRecord:
```

`tracer is None` equivale a `NullTrace()`. `__init__.py` exporta también `NullTrace`, `TraceSession` y `make_langsmith_session`.

## 7. Cuándo se rellena `trace`

Dentro de `final_gate` y `escalate_technical` se sigue construyendo el registro con `TraceRef()` vacío. El parche es **después** de `invoke`, en `run_invoice`:

1. Armar `metadata` con solo estos strings: `invoice_id`, `rules_version`, `model_extractor`, `model_verifier`, `jev` (el `jev_label`), `phase`.
2. `tags`: `["invoice", phase]`.
3. `config` del grafo = `{"configurable": {"thread_id": thread_id}, **tracer.open_config(metadata=..., tags=...)}`.
4. `invoke`.
5. `record = DecisionRecord.model_validate(state["record"])`.
6. `finished = tracer.finish(record.decision)`. Si no es `None`, `record = record.model_copy(update={"trace": finished})`.
7. Si el `trace` cambió, escribir el dump de vuelta al checkpointer con `update_state`, de forma que `get_state(config).values["record"]["trace"]["langsmith_run_id"]` coincida con el registro devuelto. Si `update_state` exige nodo, usar el nodo que escribió `record` (`final_gate` o `escalate_technical`, el que haya corrido).
8. Devolver `record`.

Si `finish` o `update_state` lanzan: tragar la excepción de traza, devolver el registro de negocio **sin** cambiar la decisión. `trace` queda como estaba (vacío si el parche no llegó a aplicarse).

No meter el documento, el system prompt ni la clave en `metadata` ni en `tags`.

`make_langsmith_session` con tracing activo:

- No se prueba contra la red en este spec.
- `open_config` adjunta el callback o el contexto que el SDK de `langsmith` documente para LangGraph 1.x, más `metadata` y `tags`.
- `finish` lee el id de la traza raíz capturada durante `invoke`. Lo guarda en `langsmith_run_id`.
- `url`: la que devuelva el SDK para esa corrida. Si el SDK no da URL sin otra llamada de red, dejar `url=None` y conservar el id. No inventar un `tenant_id`.
- Cualquier excepción del SDK dentro de `open_config` o `finish` → comportarse como `NullTrace` para esa corrida (decisión intacta, `trace` vacío).
- Con `langsmith_tracing is False` o clave en blanco: devolver `NullTrace` y no instanciar el cliente.

## 8. Qué no cambia

- Orden de nodos de D023, incluido `escalate_technical`.
- Excepción de negocio → ESCALAR `error_tecnico`, salvo FRENAR ya armado.
- Imagen ilegible → `documento ilegible`.
- `MemorySaver` en tests. Sin checkpointer de Postgres.
- Tests actuales de `test_invoice_graph.py`: siguen verdes sin pasar `tracer`. El caso PAGAR sigue con `trace.langsmith_run_id is None`.

## 9. Dependencia

Añadir `langsmith` en `dependencies` de `pyproject.toml`. Anotar en el tablero la versión importada (`importlib.metadata.version("langsmith")`).

Prohibido añadir `langfuse`, `langchain`, `langchain-openai` o un SDK de JEV. `langchain-core` puede seguir como transitiva de `langgraph`.

## 10. Tests

Dobles locales. Cero red. No leer `.env`. No llamar `make_langsmith_session` con una clave.

El fixture PAGAR es el de `backend/tests/test_invoice_graph.py` (mismo chat, mismo contrato temporal, mismas señales). Reutilizarlo o copiar el mínimo; no leer `data/`.

1. **Id en el registro.** `tracer` falso cuyo `finish` devuelve `TraceRef(langsmith_run_id="00000000-0000-4000-8000-000000000001", url="https://smith.langchain.com/r/00000000-0000-4000-8000-000000000001")`. Con el fixture PAGAR: `decision == "PAGAR"`, `trace.langsmith_run_id` es ese uuid, `trace.url` es esa URL. `get_state` del mismo saver y `thread_id` trae el mismo id dentro de `record`. `finish` fue llamado con `"PAGAR"`.
2. **Traza rota.** `finish` lanza `RuntimeError("langsmith_down")`. `run_invoice` no propaga. `decision` sigue `"PAGAR"`. `trace.langsmith_run_id is None`. El texto `"langsmith_down"` no aparece en `summary`.
3. **Sin tracer.** El caso PAGAR de T3.7 no se toca: ambos campos de `trace` en `None`.
4. **Metadatos.** El doble guarda el dict de `open_config`. Contiene `invoice_id` y `phase == "dev"`. No contiene el texto `Demo SA` del chat ni la cadena `test-key`.
5. **Fase.** `phase="eval"` llega al metadata. Otro valor no está en el tipo.
6. **Settings.** Mapping con las cuatro variables rellena los campos. `LANGSMITH_TRACING=yes` → `invalid_bool`. Mapping vacío: tracing falso, clave vacía, proyecto `blinka-invoice-agent-dev`.
7. **NullTrace.** `make_langsmith_session` con `Settings()` (defaults) es un `NullTrace`: `finish` devuelve `None` y no hay cliente.
8. **Import.** `from app.graph import run_invoice, NullTrace, make_langsmith_session` no abre sockets. El fuente de `tracing.py` no contiene una clave pegada.

Registro de ejemplo (sintético, el mismo uuid del test 1):

```json
{
  "trace": {
    "langsmith_run_id": "00000000-0000-4000-8000-000000000001",
    "url": "https://smith.langchain.com/r/00000000-0000-4000-8000-000000000001"
  }
}
```

## 11. Criterios de aceptación

1. Sin `tracer`, el comportamiento de T3.7 no cambia y `langsmith_run_id` queda `None`.
2. Con un tracer falso, el registro devuelto y el `record` del checkpointer llevan el mismo `langsmith_run_id`.
3. Si el tracer lanza, la decisión de negocio se conserva y `run_invoice` no propaga.
4. `metadata` lleva `invoice_id`, versiones y `phase`, y no lleva el documento ni una clave.
5. `Settings` lee las cuatro variables de `docs/07`. Tracing apagado o sin clave → `NullTrace`, sin cliente.
6. `pyproject.toml` gana `langsmith` y ninguna dependencia prohibida en §9.
7. No hay nodos nuevos. JEV sigue antes de `det_checks`.
8. `python -m pytest -q` verde. `python -m ruff check .` pasa.
9. Commit y push. Tablero: T3.8 HECHA solo con conteo real y la versión de `langsmith`. G0 sigue PENDIENTE.

## 12. Subtareas

Hacerlas en orden. Cada una: test que falla, código mínimo, test verde. Un commit al cerrar T3.8.8.

- T3.8.1 `TraceSession`, `NullTrace`, argumento `tracer=None` en `run_invoice`. El PAGAR de T3.7 sigue con `trace` vacío.
- T3.8.2 Parche post-`invoke` + `update_state`. Test §10.1.
- T3.8.3 `finish` que lanza no cambia la decisión. Test §10.2.
- T3.8.4 Metadata y `phase` sin documento ni clave. Tests §10.4 y §10.5.
- T3.8.5 Cuatro campos en `Settings` y ajuste del test de claves ajenas. Tests §10.6.
- T3.8.6 `make_langsmith_session`: apagado → `NullTrace`. Dependencia `langsmith` en `pyproject.toml`. Test §10.7. No llamar al SDK real.
- T3.8.7 `pytest -q` y `ruff check .`. `__init__.py` exporta la API de §6.
- T3.8.8 `docs/TASK_BOARD.md` fila T3.8 a HECHA. No tocar G0. `docs/AI_USAGE_LOG.md` una fila. Anotar la versión de `langsmith`. Commit y push: `T3.8: store LangSmith run id on the decision record`.

## 13. Mensaje para la sesión que implementa

```text
Implementa T3.8 según docs/T3_8_SPEC.md. Skill de dominio: ninguna.
No uses langfuse ni langchain-rag. No llames a la red. No leas .env.
No llames get_llm ni al cliente real de LangSmith.
No edites models/, rules/, records/, gate/, llm.py, extraction/, jev/,
verifier/ ni data/. config.py solo para las cuatro claves LangSmith.
La traza no decide el pago. Si el tracer falla, la decisión no cambia
y run_invoice no propaga. Sin tracer, trace queda en None como en T3.7.
No añadas nodos. No cierres G0. No marques T3.8 HECHA sin pytest y ruff.
Al terminar: commit y push con el mensaje del spec, sección 12.
```
