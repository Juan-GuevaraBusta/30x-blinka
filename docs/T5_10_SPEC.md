# Spec T5.10 — Encadenar los registros con hash y exponer su verificación

Dueño: **Rules Engine** (lógica pura del hash en `backend/app/records/`). Carril: B. Colabora: **API** (columnas de persistencia y endpoint), **Frontend** (badge opcional en `/decisiones`). Skill de dominio: NINGUNA; proceso: `python-testing-patterns` PARCIAL, `test-driven-development`.

Depende de: ninguna tarea de F5 previa. No depende de T5.8 ni T5.9, aunque toque archivos cercanos a T5.9 en `app.py`.

Estado: contrato para la sesión que **implemente** T5.10. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D055** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio NINGUNA: no inventar una. Declarar `python-testing-patterns` (PARCIAL) y leerla antes del test de manipulación.

Lecturas:

- `backend/app/models/domain.py` líneas 127–139 (`DecisionRecord`, `_Frozen` con `extra=forbid`): **congelado v1 (D013)**. Este spec no le añade campos. El encadenado vive en la capa de persistencia, no en el esquema de dominio.
- `backend/app/persistence/tables.py` (`DecisionRecordRow`: `id`, `invoice_id`, `decision`, `position`, `payload`)
- `backend/app/persistence/sql_store.py` `add_decision` (líneas 47–67): construye `payload = record.model_dump_json()` y calcula `position` como el máximo actual + 1, dentro de la misma sesión.
- `backend/app/api/app.py` líneas 57–71 (`list_decisions`, `get_decision`): patrón de endpoint de solo lectura a imitar para el nuevo `GET /decisions/verify-chain`.
- `backend/app/records/templates.py` y `backend/app/records/build.py` (carpeta que ya es de Rules Engine; el módulo nuevo vive al lado, sin tocar esos dos archivos).
- AP2 (Agent Payments Protocol de Google): el mandate chaining expone un historial encadenado y verificable de mandatos/decisiones de agentes de pago. Es la única referencia pública con un mecanismo parecido que esta sesión puede citar; no se afirma que Blinka implemente AP2, solo que la idea de un log encadenado y verificable viene de ahí. Ramp, Brex y Polar no publican un mecanismo de verificación de su log de decisiones: ese es el diferencial de explicabilidad/seguridad que motiva esta tarea.

## 1. Qué es T5.10

Cada `DecisionRecord` persistido guarda, además de su contenido, un hash que depende del registro anterior. Si alguien edita un registro ya guardado directamente en la base (sin pasar por el API), la verificación detecta en qué posición se rompió la cadena. Esto no cambia qué decide el sistema (PAGAR/ESCALAR/FRENAR): es evidencia de integridad sobre el registro ya tomado, no una regla nueva.

## 2. Alcance

- `backend/app/records/chain.py` (Rules Engine): función pura `canonical_json(record: DecisionRecord) -> str` (JSON con claves ordenadas, sin espacios, `model_dump(mode="json")` de pydantic) y `compute_record_hash(record: DecisionRecord, prev_hash: str) -> str` (SHA-256 hex de `canonical_json(record) + prev_hash`, codificado UTF-8). Hash génesis (primer registro de toda la tabla): `prev_hash = "0" * 64`.
- `backend/app/persistence/tables.py` (API): dos columnas nuevas en `DecisionRecordRow`, `prev_hash: Mapped[str]` y `record_hash: Mapped[str]` (`String`, `nullable=False`). No se tocan `id`, `invoice_id`, `decision`, `position` ni `payload`.
- `backend/app/persistence/sql_store.py` `add_decision` (API): antes de construir la fila, leer el `record_hash` de la fila con mayor `position` ya en la tabla (o `"0" * 64` si la tabla está vacía) como `prev_hash` del nuevo registro; calcular `record_hash` con `compute_record_hash`; guardar ambos en la fila nueva. Dentro de la misma sesión/transacción que ya usa `add_decision`, para no abrir una segunda race (coordinar con T5.8 si ambas tareas tocan este método a la vez: aplicar primero la que haya aterrizado, y el diff de la segunda debe mencionar que compone sobre la primera, no que la revierte).
- `GET /decisions/verify-chain` (API, `backend/app/api/app.py`): recorre `DecisionRecordRow` ordenado por `position`, recalcula `compute_record_hash` sobre el `payload` guardado y el `prev_hash` esperado (encadenado desde `"0" * 64`), y compara contra el `record_hash` almacenado. Responde `{"ok": bool, "length": int, "first_broken_id": str | None}`. `ok=true` y `first_broken_id=null` cuando la cadena entera coincide; en la primera discrepancia, `ok=false` y `first_broken_id` es el `id` de esa fila; el recorrido se detiene ahí (no hace falta seguir comprobando filas posteriores a la primera rotura).
- Badge opcional en `/decisiones` (Frontend, sub-ítem, puede quedar fuera si el tiempo no alcanza): un indicador «registro íntegro» que llama a `GET /decisions/verify-chain` y muestra `ok`. Si no se implementa, anotarlo como línea de corte en el tablero, sin afirmar que existe.
- OpenAPI: añadir el path `GET /decisions/verify-chain` a `backend/openapi.json` (se regenera con la app, como ya hace T4.1).

## 3. Fuera de alcance

- Cambiar `DecisionRecord`, `extra=forbid`, o cualquier modelo congelado de `backend/app/models/`.
- Cambiar qué decide `decide()` o cualquier regla R01–R13.
- Firmar criptográficamente con una clave privada, o publicar el hash en una cadena externa (blockchain). Es un hash encadenado local, no una firma.
- Migrar `DecisionRecordRow` con Alembic: sigue `create_all` (igual que T4.2/T4.9).
- Recalcular o rellenar `prev_hash`/`record_hash` para filas que ya existan en una base viva antes de este cambio (la migración de datos históricos no es parte de este spec; si el deploy tiene filas previas, el primer registro nuevo después del deploy encadena desde `"0" * 64` otra vez y se anota la discontinuidad).
- Implementar AP2 en sí, o cualquier protocolo de Google Agent Payments más allá de citarlo como referencia de diseño.

## 4. Criterios de aceptación

1. `backend/tests/rules/test_record_chain.py` (o ubicación equivalente bajo `backend/tests/rules/`): `compute_record_hash` es determinista para el mismo registro y `prev_hash`; cambia si cualquier campo del registro cambia; cambia si `prev_hash` cambia.
2. Test de integración: insertar 3 `DecisionRecord` vía `SqlStore.add_decision`, llamar `GET /decisions/verify-chain` → `ok=true`, `length=3`, `first_broken_id=null`.
3. Test de manipulación: tras insertar 3 registros, editar directamente en la base (vía SQL o `Session`, no vía el API) el `payload` de la segunda fila sin recalcular su `record_hash`. `GET /decisions/verify-chain` → `ok=false`, `first_broken_id` igual al `id` de esa segunda fila.
4. `cd backend && python -m pytest -q` — 0 failed. `python -m ruff check .` — ok.
5. Ningún test ni código de producción cambia `decision`, `severity` o cualquier campo de `DecisionRecord` a partir del hash. El hash es metadato de persistencia, no insumo de `decide()`.
6. `backend/openapi.json` incluye `GET /decisions/verify-chain`. Diff de `backend/app/models/domain.py` vacío.
7. Si se implementa el badge de frontend: `cd frontend && npx tsc --noEmit && npm run lint && npm test` — ok, y una nota de cómo se probó (Playwright o vitest). Si no se implementa, el tablero lo anota como línea de corte, no como hecho.
8. `docs/TASK_BOARD.md`: T5.10 pasa a HECHA (o PARCIAL si el badge de frontend queda fuera, con la nota explícita).
9. Fila en `docs/AI_USAGE_LOG.md`.
10. Commit y push con el mensaje del §5.

## 5. Commit

```text
T5.10: hash-chain decision records and expose chain verification
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T5.10 según docs/T5_10_SPEC.md. Decisión D055.
No toques backend/app/models/domain.py (DecisionRecord está congelado,
D013). El encadenado vive en persistencia: añade prev_hash y record_hash
como columnas nuevas en DecisionRecordRow (persistence/tables.py), y
calcúlalas en SqlStore.add_decision (persistence/sql_store.py líneas 47-67)
a partir del record_hash de la fila anterior por position (genesis "0"*64).
Hash puro en backend/app/records/chain.py: SHA-256 de un JSON canónico del
registro más el prev_hash. Añade GET /decisions/verify-chain en
backend/app/api/app.py que recorra las filas por position, recalcule y
compare, devolviendo {ok, length, first_broken_id}. Actualiza
backend/openapi.json. Si el tiempo alcanza, un badge opcional en
frontend/app/decisiones/ que llame a ese endpoint; si no, anótalo como
línea de corte, no como hecho. Referencia de diseño (cítala, no la
implementes): AP2 (Google Agent Payments Protocol) mandate chaining;
Ramp/Brex/Polar no exponen un log verificable, por eso es diferencial.
Prueba con un test que manipule un payload en la base directamente (no vía
API) y compruebe que verify-chain detecta la rotura en esa fila exacta.
Al terminar: pytest, ruff, tsc/lint/vitest si tocas frontend, openapi.json,
tablero y AI_USAGE_LOG. Commit y push:
T5.10: hash-chain decision records and expose chain verification
```
