# Spec T3.7 — Grafo LangGraph fail-closed con checkpointer

Dueño: Agent Graph. Skill de dominio: **`langgraph-fundamentals`** (`docs/SKILLS_MAP.md`, TOTAL). Proceso: `test-driven-development` y `python-testing-patterns`. No usar `langchain-rag` (D004). No usar `langfuse`.

Estado: contrato para la sesión que implemente T3.7. No cierra la tarea hasta que los criterios de aceptación pasen.

Decisión que fija este contrato: **D023**.

## 0. Para el agente que implementa

Leer antes de tocar código:

- `AGENTS.md` (I1–I9, en especial I2, I3, I4, I7)
- `docs/02_ARCHITECTURE.md` secciones «Flujo (LangGraph)», «Nodos» y «Verificador: qué audita»
- `docs/04_RULES_AND_DECISION_SPEC.md` §6 y §7
- `docs/DECISIONS_LOG.md` D004, D016, D018, D019, D020, D021, D022, D023
- Este archivo
- La skill `langgraph-fundamentals` (StateGraph, `Command`, checkpointer, el aviso de no mezclar `add_edge` con `Command`)

No leer `langchain-rag`. No llamar a la red. No leer `.env`. No construir `Settings`. No llamar `get_llm`.

No editar `backend/app/models/`, `backend/app/rules/`, `backend/app/records/`, `backend/app/gate/`, `backend/app/config.py`, `backend/app/llm.py`, `backend/app/extraction/`, `backend/app/jev/`, `backend/app/verifier/`, `data/`. Esos dueños ya congelaron el contrato. El grafo solo los importa.

No cerrar G0. No implementar T3.8 (LangSmith), T3.9 (CLI) ni T3.10 (`backend/tests/gate/test_fail_closed.py`).

## 1. Qué es T3.7

Un grafo lineal que cablea piezas ya hechas y, si algo truena, entrega un `DecisionRecord` de fallo cerrado. No decide el pago por su cuenta.

Orden de nodos (D023 corrige la flecha del mermaid: R09 lee señales, así que JEV va **antes** de los chequeos):

```text
START → ingest → extract → contract_lookup → jev_checks → det_checks
      → aggregate → record → verify → final_gate → END
```

Cualquier excepción de nodo que no sea el caso de documento ilegible va al nodo `escalate_technical` y termina. No hay reintentos. No hay `interrupt`. No hay pausa humana. No hay `Send`. El pulidor no entra.

`decide()` sigue siendo la única función que propone PAGAR / ESCALAR / FRENAR a partir de chequeos. El verificador solo sube severidad, vía `verify_decision` (T3.6), que ya llama a `apply_verifier_severity_floor`. `run_final_gate` es el último filtro. El grafo no copia esas funciones.

## 2. Fuera de alcance

- Traza LangSmith y `trace.langsmith_run_id` relleno (T3.8). Aquí `TraceRef` queda con ambos campos en `None`.
- CLI y `decisions.json` (T3.9).
- `backend/tests/gate/test_fail_closed.py` (T3.10).
- OCR, RAG, cola, Postgres, API, UI.
- Recalibrar umbrales. No mirar el holdout.
- E2E del set dorado y el caso D005 completo. T3.7 prueba el cable con fakes, no las 34 facturas.
- Reescribir `decide`, `run_final_gate`, plantillas, extractor, JEV o verificador.

## 3. Archivos

Crear:

- `backend/app/graph/state.py` — `InvoiceState`
- `backend/app/graph/deps.py` — `GraphDeps`
- `backend/app/graph/build.py` — nodos, `compile_invoice_graph`, `run_invoice`, `GraphError`

Modificar:

- `backend/app/graph/__init__.py` — reexportar la API de §6. Sin efectos al importar (no compilar el grafo, no leer disco, no leer entorno).
- `pyproject.toml` — una sola dependencia nueva de runtime: `langgraph`. Permitidas las transitivas que ese paquete declara (incluye `langchain-core`). Prohibido añadir `langchain`, `langchain-openai`, `langsmith`, `httpx`, `python-dotenv` o un SDK de JEV.

Al cerrar, y solo entonces:

- `docs/TASK_BOARD.md` — fila T3.7 a HECHA, con el conteo real de pytest y la versión de `langgraph` importada. No tocar G0.
- `docs/AI_USAGE_LOG.md` — una fila.

Tests nuevos (raíz de `backend/tests/`, no `tests/gate/`):

- `backend/tests/test_invoice_graph.py`

## 4. Invariantes que este código no puede romper

- I2. Ningún nodo pide al modelo una decisión de pago. Extractor, contrato, JEV y verificador se llaman con sus funciones ya escritas.
- I3. Excepción, timeout, JSON malo, cliente roto o dato que impide seguir → no PAGAR. Sale un registro ESCALAR, salvo la regla de §7 cuando ya había un FRENAR.
- I4. La decisión que sale de `run_invoice` no es menos severa que `decide(checks)` ni que el piso del verificador. Un informe limpio no baja un FRENAR.
- I6. Solo datos sintéticos en tests. Los códigos de error no incluyen el documento ni una clave.
- I7. El documento solo viaja dentro de las funciones que ya lo aíslan (`extract_document`, `lookup_contract`, `build_jev_state`, `build_verifier_user`). El grafo no concatena el documento a un system prompt.
- I8. PAGAR es un campo del registro. No hay movimiento de dinero.

## 5. Dependencia

Añadir `langgraph` en `dependencies` de `pyproject.toml`. Importar `StateGraph`, `START`, `END` y `Command` desde `langgraph.graph`, y `MemorySaver` desde `langgraph.checkpoint.memory`.

Si esos nombres no existen en la versión instalada: parar y anotarlo. No envolver LangGraph en otro framework.

Sin `RetryPolicy`. Sin `interrupt`. Cada nodo que enruta con `Command` no lleva además `add_edge` hacia otro nodo (la skill avisa que se ejecutarían los dos). La única arista estática permitida es `START → ingest`.

## 6. API pública

```python
class GraphError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GraphDeps:
    extractor: object  # complete_json(system, user) -> dict
    verifier: object   # igual, rol verifier
    jev: object        # ask(state, questions) -> list[JevSignal]
    rules: RulesConfig
    fx: FxTable
    ledger: tuple[LedgerEntry, ...]
    company_name: str
    rules_version: str
    model_extractor: str
    model_verifier: str
    jev_label: str
    contracts_dir: Path | None = None


def compile_invoice_graph(deps: GraphDeps, checkpointer: BaseCheckpointSaver): ...

def run_invoice(
    deps: GraphDeps,
    *,
    raw: bytes,
    channel: IngestChannel,
    invoice_id: str,
    received_at: datetime,
    checkpointer: BaseCheckpointSaver,
    thread_id: str,
) -> DecisionRecord: ...
```

`__init__.py` exporta: `GraphDeps`, `GraphError`, `InvoiceState`, `compile_invoice_graph`, `run_invoice`.

`str(GraphError(...)) == error.code`. Códigos de `GraphError`, solo antes de invocar:

| Código | Cuándo |
|---|---|
| `empty_invoice_id` | `invoice_id` vacío o solo espacios |
| `naive_datetime` | `received_at.tzinfo` es `None` |

Esos dos no llaman al grafo ni a ningún modelo. Cualquier fallo **dentro** de un nodo no sale como excepción de `run_invoice`: sale como `DecisionRecord`.

## 7. Estado

`InvoiceState` es un `TypedDict` con `total=False`. Nada de `bytes` en el estado (el checkpointer tiene que poder guardarlo).

| Campo | Tipo en el estado | Quién lo escribe |
|---|---|---|
| `raw_b64` | `str` ASCII | `run_invoice`, antes de `invoke` |
| `channel` | `str` | igual |
| `invoice_id` | `str` | igual |
| `received_at` | `str` ISO-8601 con zona | igual |
| `doc_text` | `str` | `ingest` |
| `extraction` | `dict` (`model_dump(mode="json")`) | `extract` |
| `contract_terms` | `dict \| None` | `contract_lookup` |
| `contract_confirmed` | `bool` | `contract_lookup` |
| `cited_clause` | `str \| None` | `contract_lookup` (primera cita, o `None`) |
| `jev_signals` | `list[dict]` | `jev_checks` |
| `check_results` | `list[dict]` | `det_checks` |
| `proposed_decision` | `Decision` | `aggregate` (`decide`) |
| `summary` | `str` | `record`, luego `verify` puede ampliarla |
| `admin_notice` | `str \| None` | `record`, luego `verify` |
| `next_step` | `str` | `record` |
| `verifier_report` | `dict` | `verify` |
| `record` | `dict` | `final_gate` o `escalate_technical` |
| `final_decision` | `Decision` | `final_gate` o `escalate_technical` |
| `errors` | `Annotated[list[str], operator.add]` | cualquier nodo en fallo |

`run_invoice` mete `raw_b64 = base64.b64encode(raw).decode("ascii")`. El nodo `ingest` decodifica y llama `ingest_bytes`. No guarda los bytes.

`trace_ids` no se rellena (T3.8).

## 8. Nodos

Cada nodo cierra sobre `GraphDeps`. El estado no lleva clientes.

Envoltura de cada nodo (menos `escalate_technical`): `try` el cuerpo / `except Exception` → `Command(goto="escalate_technical", update={"errors": ["error_tecnico"]})`. No encadenar el mensaje original. No meter el documento en `errors`.

`escalate_technical` no lanza. Si algo falla al armar el registro mínimo, el `except` interno igual devuelve un `DecisionRecord` ESCALAR con `build_technical_error_summary("error_tecnico")` y `Extraction()` vacía.

### 8.1 `ingest`

`ingest_bytes(base64.b64decode(raw_b64), channel=channel)`.

- `IngestError` con código `illegible` o `empty_text` → `errors: ["documento ilegible"]` y `goto="escalate_technical"`.
- Otro `IngestError` (`unsupported_channel`) → `errors: ["error_tecnico"]` y el mismo goto.
- Éxito → `doc_text` y `goto="extract"`.

### 8.2 `extract`

`extract_document(doc_text, deps.extractor)`.

- `ExtractError` o cualquier otra excepción → `error_tecnico` → `escalate_technical`.
- Éxito → `extraction` (dump JSON) y `goto="contract_lookup"`.

### 8.3 `contract_lookup`

`lookup_contract(extraction.beneficiary, deps.extractor, contracts_dir=deps.contracts_dir)`.

- `found=False`, o `terms is None`, o `confirmed` falso: no es excepción. Guardar `contract_terms=None`, `contract_confirmed=False`, `cited_clause=None`. Seguir. R06 ya escala.
- `ContractLookupError` → `error_tecnico` → `escalate_technical`.
- Éxito con `terms` y `confirmed=True` → dump de `terms`, `contract_confirmed=True`, `cited_clause` = primer elemento de `cited_clauses` o `None`. `goto="jev_checks"`.

### 8.4 `jev_checks`

`state = build_jev_state(extraction=..., company_name=deps.company_name, doc_text=doc_text, cited_clause=cited_clause)`.

`signals = ask_invoice_signals(deps.jev, state)` con las preguntas por defecto (`INVOICE_QUESTIONS`).

- `JevRunError` → `error_tecnico`.
- Éxito → `jev_signals` como lista de dumps. `goto="det_checks"`.

No llamar `ids_below_threshold` para decidir. R09 y R13 ya leen las señales.

### 8.5 `det_checks`

Armar `RuleContext` con `deps.rules`, `deps.fx`, la extracción, `contract_terms` (o `None`), `contract_confirmed`, `jev_signals`, `doc_text`, `deps.ledger`, `received_at` parseado del ISO, `manual_block=False`.

`run_deterministic_checks(ctx)`. Guardar los dumps. `goto="aggregate"`.

No recalcular FX en el grafo. Los chequeos ya convierten.

### 8.6 `aggregate`

`proposed = decide(checks)`. Guardar `proposed_decision`. `goto="record"`. Sin LLM.

### 8.7 `record`

`RecordContext.from_rule_context(ctx, invoice_id=invoice_id)`.

- `checks` para el registro = `enrich_check_details(checks, record_ctx)`.
- `summary = build_summary(proposed_decision, checks, record_ctx)`.
- `admin_notice = build_admin_notice(proposed_decision, checks, record_ctx, summary)`.
- `next_step = build_next_step(proposed_decision, checks, record_ctx)`.

Todavía no hay `DecisionRecord`: falta el verificador. `goto="verify"`.

### 8.8 `verify`

`outcome = verify_decision(deps.verifier, doc_text=..., extraction=..., checks=..., proposed=proposed_decision, jev_signals=..., rules_version=deps.rules_version, invoice_id=..., beneficiary=extraction.beneficiary)`.

- `VerifierError` → `error_tecnico` → `escalate_technical`. No inventar un `VerifierReport` aquí; lo arma el nodo de fallo.
- Éxito:
  - `verifier_report` = dump de `outcome.report`.
  - `raised = outcome.decision` (ya es el max con el piso).
  - Si `outcome.summary` no es `None`, `summary = summary_de_record + " " + outcome.summary`. Así la explicación sigue citando cada regla no-OK y también el verificador.
  - Si `outcome.admin_notice` no es `None`, reemplaza `admin_notice`.
  - Guardar la decisión elevada en el estado como `elevated_decision` (`Decision`). `proposed_decision` no se pisa: el gate lo necesita.
  - `goto="final_gate"`.

### 8.9 `final_gate`

Construir `DecisionRecord` con:

- `id` = `invoice_id` (el mismo string; no hace falta otro id)
- `invoice_id`, `received_at`
- `decision` = `elevated_decision`
- `severity` = `SEVERITY[decision]`
- `summary`, `checks` (los enriquecidos), `extracted`, `jev_signals`
- `verifier` = el report
- `admin_notice`, `next_step`
- `trace` = `TraceRef()`
- `versions` = `ModelVersions(rules_version=deps.rules_version, model_extractor=deps.model_extractor, model_verifier=deps.model_verifier, jev=deps.jev_label)`
- `human_events` = `[]`

`GateInput(proposed_decision=proposed_decision, record=ese_record, jev_thresholds=deps.rules.jev_thresholds)`.

`out = run_final_gate(inp)`. Guardar `record` = dump de `out.record`, `final_decision` = `out.final_decision`. `goto=END`.

No leer `gate_violations` para volver a decidir. El registro que devuelve el gate manda.

### 8.10 `escalate_technical`

Motivo:

- si `"documento ilegible"` está en `errors` → `build_technical_error_summary("documento ilegible")`
- si no → `build_technical_error_summary("error_tecnico")`

Decisión de este nodo:

- Si `proposed_decision` es `"FRENAR"` **y** el estado ya tiene `summary` y `admin_notice` no vacío del nodo `record`: no bajar. `final_decision` queda `"FRENAR"`. No reemplazar summary ni aviso. Igual se anota el error en `errors` (ya viene del nodo que falló). El `record` se arma con la decisión FRENAR, el verificador que haya, o si no hay report: `VerifierReport(consistent=False, issues=[])`.
- En cualquier otro caso: `final_decision` = `"ESCALAR"`, `severity` 1, `summary` = el motivo de arriba, `admin_notice` = `None`, `next_step` = `"Requiere revisión humana."`.

Huecos, cuando el fallo fue temprano:

- `extraction` ausente → `Extraction()`
- `checks` ausentes → `[]`
- `jev_signals` ausentes → `[]`
- `verifier` ausente → `VerifierReport(consistent=False, issues=[])`
- `proposed_decision` ausente → tratarlo como `"PAGAR"` solo para el max interno de esta sección; la decisión publicada sigue la regla de arriba (ESCALAR, porque no había FRENAR armado)

`goto=END`. `run_invoice` devuelve `DecisionRecord.model_validate(state["record"])`.

## 9. Checkpointer

`compile_invoice_graph` hace `builder.compile(checkpointer=checkpointer)`. El argumento es obligatorio.

`run_invoice` invoca con:

```python
config = {"configurable": {"thread_id": thread_id}}
```

Tras un recorrido que llega a END, `compile_invoice_graph(deps, el_mismo_saver).get_state(config).values["final_decision"]` es la decisión del registro devuelto.

No usar checkpointer de SQLite ni de Postgres.

## 10. Tests

Dobles locales, como en `test_extract.py`: `complete_json` y `ask`. Cero red.

Fixture sintética del caso que puede PAGAR (en el propio test, no en `data/`):

- Chat UTF-8 cuyo texto contiene, literales: `Demo SA`, `100 USD`, `2026-04-01`, `Blinka Demo`, `IT`, `INV-G1`.
- Extractor: si el user es ese texto, JSON de extracción con esos campos y `source_spans` que sean subcadenas. `amount` 100.0, moneda `USD`, destinatario `Blinka Demo`, depto `IT`.
- `contracts_dir` = `tmp_path` con un solo `.txt`:

```text
confirmed: true
El beneficiario autorizado es Demo SA.
Cláusula 4.1. Tarifa 100 USD.
```

- Si el user es el contrato, el mismo doble devuelve `fee_amount` 100, `fee_currency` `USD`, `beneficiary` `Demo SA`, `cited_clauses` `["4.1"]`, `quotes` con `beneficiary`, `fee_amount` y `fee_currency` iguales a subcadenas de ese archivo. El resto de campos del payload en `null` y sin claves de más.
- JEV: siete señales. J1–J4, J6, J7 con `answer=True` y `probability=0.99`. J5 con `answer="servicios"` y `probability=0.99`.
- Verificador, salvo el test que lo pisa: `{"consistent": true, "issues": []}`.
- `RulesConfig` mínimo: empresa `Blinka Demo` / `USD`; límite por pago 5000; periodo `calendar_month` 100000; umbral humano 3000; beneficiario permitido `Demo SA`; presupuesto `IT` 10000; approver `default` = `a@demo.test`; `manual_blocks` vacío; `on_fail` de R01 y R05 y R07 = `FRENAR`, el resto `ESCALAR`; umbrales JEV todos 0.5.
- `FxTable` con `USD` → 1.0, base `USD`, fecha `2026-03-01`.
- `ledger` vacío. `received_at` con zona (UTC). `company_name` = `Blinka Demo`.

Casos:

1. **PAGAR cableado.** Con ese fixture, `record.decision == "PAGAR"`, `severity == 0`, los 13 chequeos `OK`, `verifier.consistent is True`, `trace.langsmith_run_id is None`. `get_state` del mismo saver y `thread_id` devuelve `final_decision == "PAGAR"`.
2. **Excepción → error_tecnico.** El extractor lanza `DecisionClientError("http_error")` en el primer `complete_json`. `decision == "ESCALAR"`, `severity == 1`, `"error_tecnico"` está en `record.summary`, `admin_notice is None`. `run_invoice` no propaga la excepción. `str` del camino de error no contiene `test-key` ni el texto del documento.
3. **Ilegible.** `channel="image"` y `raw=b"not-an-image"`. Cero llamadas a `complete_json` y a `ask`. `decision == "ESCALAR"` y `"documento ilegible"` está en `summary`.
4. **Verificador sube.** Mismo fixture PAGAR, pero el verificador devuelve `consistent=false` y un issue `kind=violation`, `code="extraction_mismatch"`, `evidence` igual a una cita que está en el chat (`100 USD`). `decision == "FRENAR"`. `admin_notice` contiene `100 USD`.
5. **No baja.** Beneficiario extraído `Fuera De Lista` (y el span en el texto). Verificador limpio. `decision == "FRENAR"` (R01). 
6. **Duda del verificador.** Fixture PAGAR, issue `kind=uncertainty`, `evidence=null`. `decision == "ESCALAR"` y `admin_notice is None`.
7. **FRENAR y luego el verificador truena.** Beneficiario fuera de lista (R01 ya FRENAR) y `verify` recibe un doble que lanza `DecisionClientError`. `decision == "FRENAR"` y `admin_notice` no es `None`.
8. **`empty_invoice_id` y `naive_datetime`.** `GraphError` con ese código. El doble no se llama.
9. **Import.** `from app.graph import compile_invoice_graph, run_invoice, GraphDeps, GraphError, InvoiceState` no toca la red.

## 11. Criterios de aceptación

1. El grafo compilado tiene los nodos de §1 más `escalate_technical`.
2. JEV corre antes de `run_deterministic_checks`.
3. Una excepción del extractor produce ESCALAR con `error_tecnico` en el summary (§10.2).
4. `image` produce ESCALAR con `documento ilegible` y cero llamadas LLM (§10.3).
5. Violación con evidencia sube a FRENAR y deja aviso (§10.4).
6. Incertidumbre sube a ESCALAR sin aviso (§10.6).
7. R01 FRENAR no baja aunque el verificador venga limpio (§10.5) ni aunque el verificador lance (§10.7).
8. Hay checkpointer: `get_state` ve `final_decision` (§10.1).
9. `trace.langsmith_run_id` queda `None`.
10. `pyproject.toml` gana `langgraph` y ninguna dependencia prohibida en §3.
11. `python -m pytest -q` verde. `python -m ruff check .` pasa.
12. Commit y push. Tablero: T3.7 HECHA solo con conteo real. G0 sigue PENDIENTE.

## 12. Subtareas

Hacerlas en orden. Cada una: test que falla, código mínimo, test verde. Un commit al cerrar T3.7.12.

- T3.7.1 Dependencia `langgraph` + `GraphError` de `empty_invoice_id` / `naive_datetime` sin invocar.
- T3.7.2 `ingest` en el grafo: `image` → `documento ilegible`, sin LLM.
- T3.7.3 `extract` que lanza → ESCALAR `error_tecnico`.
- T3.7.4 Happy path PAGAR con el fixture de §10 (contrato temporal, JEV, chequeos, gate).
- T3.7.5 Checkpointer: `get_state` conserva `final_decision`.
- T3.7.6 Verificador con evidencia → FRENAR + `admin_notice`.
- T3.7.7 Verificador en duda → ESCALAR sin aviso.
- T3.7.8 R01 FRENAR no baja con informe limpio.
- T3.7.9 Verificador que lanza después de un FRENAR no baja la decisión.
- T3.7.10 `__init__.py` reexporta la API. `pytest -q` y `ruff check .`.
- T3.7.11 `docs/TASK_BOARD.md` fila T3.7 a HECHA. No tocar G0. `docs/AI_USAGE_LOG.md` una fila. Anotar la versión de `langgraph`.
- T3.7.12 Commit y push: `T3.7: fail-closed LangGraph invoice graph`.

## 13. Mensaje para la sesión que implementa

```text
Implementa T3.7 según docs/T3_7_SPEC.md. Skill de dominio: langgraph-fundamentals.
Antes de escribir código lee ese spec, AGENTS.md, docs/02_ARCHITECTURE.md
(flujo y nodos) y la skill langgraph-fundamentals.
No leas langchain-rag. No llames a la red. No leas .env. No llames get_llm.
No edites models/, rules/, records/, gate/, config.py, llm.py, extraction/,
jev/, verifier/ ni data/.
El grafo solo cablea. decide() propone. verify_decision solo sube severidad.
run_final_gate filtra. Excepción → ESCALAR error_tecnico, salvo FRENAR ya
armado, que no baja. Imagen ilegible → ESCALAR documento ilegible.
Checkpointer en memoria. Sin LangSmith, sin CLI, sin T3.10.
No cierres G0. No marques T3.7 HECHA sin pytest y ruff.
Al terminar: commit y push con el mensaje del spec, sección 12.
```
