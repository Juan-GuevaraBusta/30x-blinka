# Spec T4.5 — UI `/decisiones/[id]`

Dueño: **Frontend**. Skill de dominio: `frontend-design` (TOTAL). Rendimiento al escribir la página: `vercel-react-best-practices` (PARCIAL). No usar `ui-ux-pro-max` (dos criterios visuales). No usar `supabase`, `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **implemente** T4.5. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D034**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (I2 el LLM no decide; I4 el verificador solo sube severidad y esta pantalla no lo hace; I5 la explicación sale de plantillas ya guardadas; I6 solo datos sintéticos; I8 cero dinero)
- `docs/04_RULES_AND_DECISION_SPEC.md` §5 (el registro no se reescribe) y §6 (las plantillas ya están en el registro)
- `docs/07_OBSERVABILITY_LANGSMITH.md` (el enlace es `trace.url`; sin URL no se inventa una)
- `docs/T4_1_SPEC.md` (`GET /decisions/{id}` es 200 o 404; el id es `DecisionRecord.id`, no `invoice_id`)
- `docs/SKILLS_MAP.md` fila T4.5
- `backend/app/models/domain.py` (`Extraction`, `CheckResult`, `VerifierReport`, `TraceRef`, `DecisionRecord`; no editarlo)
- `backend/openapi.json` path `GET /decisions/{id}` (no editarlo)
- `frontend/README.md`, `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/app/api/rules/route.ts`

Declarar la skill en una línea, leer `frontend-design` y seguir su proceso: plan visual corto **antes** de escribir componentes. Ese plan adopta el puesto de control ya construido en T4.3 (sección 9). No abre otro sistema visual. Luego leer `vercel-react-best-practices` solo para esta página: un fetch al entrar, sin cadena de requests y sin llamar a LangSmith.

No editar `backend/`, `data/`, `eval/`, `docs/04`, `docs/T4_4_SPEC.md`, `pyproject.toml` ni `backend/openapi.json`. Si el recorrido exige CORS, un entrypoint commiteado o un campo nuevo en el registro, **parar**: eso es T4.9 o un cambio de esquema.

G3 y G4 siguen PENDIENTE. Esta tarea es la pantalla de un registro (`docs/05` T4.5). No anticipar filtros de lista, aprobaciones, métricas, subida ni deploy.

## 1. Qué es T4.5

Una sola pantalla, `/decisiones/[id]`, en español. Lee un `DecisionRecord` y lo muestra. No lo calcula, no lo pule y no lo guarda de nuevo.

| Pieza | Qué hace |
|---|---|
| App | La Next.js de T4.3, App Router, TypeScript estricto, dentro de `frontend/` |
| Datos | `GET /decisions/{id}` al abrir. El `{id}` de la ruta es `DecisionRecord.id` |
| Extracción | Campos de `extracted`, con «no consta» donde el valor es `null` |
| Chequeos | Cada ítem de `checks`: `rule`, `name`, `result` (`OK` / `FALLA` / `INDETERMINADO`), `detail`, `on_fail` |
| Explicación | `summary`, `next_step`, `admin_notice`. El `detail` es el de cada chequeo, no un párrafo nuevo |
| Traza | Enlace solo si `trace.url` viene en el registro. Si no, el texto «sin traza» |
| Error | 404, 429 u otro fallo: mensaje en español. Ningún documento inventado |

La lista filtrable es T4.4. Esta pantalla puede ser el destino de un enlace `/decisiones/{id}` que esa lista añada. No implementa la tabla, los filtros ni la ruta índice `/decisiones`.

No hay un campo `detail` en la raíz de `DecisionRecord` (`openapi.json`, schema `DecisionRecord`). El único `detail` es `checks[].detail` (obligatorio, `minLength` 1). La UI no redacta otro.

## 2. Fuera de alcance

- Tabla y filtros de `/decisiones` (T4.4). Un enlace «Volver al listado» hacia `/decisiones` no es esa pantalla. No crear `app/decisiones/page.tsx`.
- Aprobar, rechazar, formularios de motivo, `POST /decisions/{id}/approve` y `.../reject` (T4.6).
- `/metricas` y `GET /metrics` (T4.7).
- Subir factura y `POST /invoices` (T4.8).
- CORS, `render.yaml`, Vercel, Postgres, bind `0.0.0.0:$PORT` (T4.9).
- Editar reglas. `/reglas` ya existe; no se rediseña.
- Auth, API keys de cliente, JWT.
- Llamar a `decide()`, al grafo, a un LLM o a la API de LangSmith.
- Abrir `data/contracts/`, PDFs u otro archivo para completar una cita que el JSON no trae.
- Construir una URL de LangSmith a partir de `trace.langsmith_run_id`.
- Reescribir `decision`, `severity`, `summary`, `checks`, `admin_notice` o `human_events`.
- Cambiar el redirect de `/` (sigue en `/reglas`).
- Cerrar G3, G4 o G5.
- Mover dinero. Ver `PAGAR` no paga (I8).

## 3. Archivos

Crear en `frontend/`:

- `app/decisiones/[id]/page.tsx` y los componentes de esa pantalla.
- `app/api/decisions/[id]/route.ts`: proxy `GET` same-origin, mismo patrón que `app/api/rules/route.ts`. El navegador llama a `/api/decisions/{id}`. Next reenvía a `${API_URL}/decisions/{id}` con `cache: "no-store"`. Solo `GET`.
- Funciones puras de presentación (traza, nulos, cita) y una prueba en el Vitest que ya usa el frontend. Playwright no entra en CI.

Modificar:

- `frontend/README.md`: esta ruta ya se puede abrir. Las demás (`/decisiones` índice, `/aprobaciones`, `/metricas`, subida) siguen fuera hasta su tarea.

Al cerrar la implementación (no este spec): `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`.

No tocar `backend/`, `data/`, `openapi.json`, ni el spec de T4.4.

## 4. Invariantes

- I2. La pantalla no llama a un LLM ni a `decide()`. La decisión que se lee es `record.decision`. Los chequeos no se vuelven a evaluar.
- I4. No se sube ni se baja `severity`. El bloque del verificador muestra `verifier.consistent` y `verifier.issues` tal cual. No aplica el piso de severidad en el cliente.
- I5. `summary`, `checks[].detail`, `next_step` y `admin_notice` se muestran como texto ya guardado. La UI no rellena las plantillas de `docs/04` §6 ni pide a un modelo que las reescriba. `human_events` se listan si el array trae elementos; no se añaden.
- I6. El ejemplo del recorrido usa nombres ficticios ya del repo (`Globex LLC`, `Acme Demo Inc.`, `cfo@demo.test`, `https://example.test/...`). No pegar datos reales ni claves. No leer `.env`.
- I8. Junto a la decisión, una frase fija: «PAGAR es una decisión registrada. Esta pantalla no mueve dinero.» Vale también cuando la decisión es `ESCALAR` o `FRENAR`: el estado es el del registro, no un pago.

Si `severity` y `decision` llegaran en desacuerdo, se muestran los dos valores guardados. La pantalla no «corrige» el JSON.

## 5. Contrato HTTP que la UI consume

Sin prefijo en el API. Ruta real: `GET /decisions/{id}` (`backend/openapi.json` y `backend/app/api/app.py`). Respuesta 200: `DecisionRecord`. El OpenAPI commiteado documenta 200 y 422. El proceso, si el id no está, responde **404** con `{"detail":"not_found"}` (T4.1 §5.2). No hace falta editar el OpenAPI para que la UI trate ese 404.

El id de la ruta es `DecisionRecord.id`. Pedir el `invoice_id` (por ejemplo `INV-0042` cuando el id es `dec_0042`) es un 404. La pantalla no busca por número de factura.

| Respuesta | Qué muestra |
|---|---|
| 200 | El registro, sección 6 |
| 404 | «No hay una decisión con ese identificador.» Sin factura de relleno |
| 429 `{"detail":"rate_limited"}` | «Demasiadas solicitudes. Espera un momento y vuelve a abrir esta decisión.» Sin registro inventado |
| 422, 5xx o red caída | El fallo en español. Sin registro inventado |

El proxy no añade cuerpo, ni query `decision`, ni cabecera de auth. Un `id` vacío, con `/` o con `..`, no se reenvía: la página muestra el mismo vacío que un 404, en español.

## 6. Qué se muestra del registro

Textos de interfaz en español. Los códigos `PAGAR`, `ESCALAR`, `FRENAR`, `OK`, `FALLA`, `INDETERMINADO`, `R01`–`R13` se ven como vienen.

### 6.1 Identidad

`id`, `invoice_id`, `received_at`, `decision`, `severity` (0, 1 o 2, el entero guardado), `versions.rules_version`, `versions.model_extractor`, `versions.model_verifier`, `versions.jev`.

Frase fija junto a las versiones: este registro conserva las versiones con las que se decidió. Cambiar reglas en `/reglas` no reescribe esta ficha.

### 6.2 Datos leídos (`extracted`)

Mostrar cada campo. Si el valor es `null`, la etiqueta visible es «no consta». No rellenar con el golden, con `data/rules.json` ni con otro registro.

Campos: `beneficiary`, `amount`, `currency`, `amount_base`, `fx` (`rate` y `date`; si `fx` es `null`, «no consta»), `due_date`, `invoice_number`, `recipient`, `department`, `invoice_type`, `lines` (descripción, monto, `source_span`; lista vacía → «sin líneas»), `source_spans`.

`source_spans` vacío → «sin citas de origen en el registro». Si hay entradas, cada clave y su texto, en el orden del JSON.

### 6.3 Chequeos

Un bloque por elemento de `checks`, en el orden del array. Por chequeo:

- `rule` y `name`
- `result`: `OK`, `FALLA` o `INDETERMINADO`. No colapsar `INDETERMINADO` en `FALLA` ni en `OK`
- `detail`, el texto guardado
- `on_fail`: `FRENAR` o `ESCALAR` si viene; si es `null`, «sin acción de fallo en el registro». No mirar el `on_fail` vigente de las reglas para completarlo
- `evidence`: si hay `clause` o `quote`, mostrarlos como cita ya guardada. Si `evidence` es `null`, o ambos textos son `null`, «sin cita de cláusula en el registro»

Array vacío → «sin chequeos en el registro». No pintar R01–R13 de adorno.

### 6.4 Explicación

En este orden, solo cadenas del registro:

1. `summary`
2. `next_step`
3. `admin_notice`, o, si es `null`, «sin aviso al administrador»

El `detail` de la explicación es el de la sección 6.3. No hay segundo párrafo generado.

### 6.5 Verificador y señales

`verifier.consistent` como «consistente» o «no consistente», según el booleano. `issues` vacía → «sin hallazgos del verificador». Si hay issues: `code`, `kind`, y `evidence` / `admin_message` o «no consta» si ese texto es `null`.

`jev_signals`: si el array está vacío, «sin señales JEV en el registro». Si hay elementos: `id`, `answer`, `probability`. No comparar con umbrales.

`human_events`: vacío → «sin eventos humanos». Si hay eventos, autor, fecha, acción y motivo, solo lectura. Sin botones.

### 6.6 Cita

La cita visible es únicamente la que ya está en el registro: `checks[].detail`, `checks[].evidence.clause`, `checks[].evidence.quote`, `extracted.source_spans` o `lines[].source_span`. Si el API no la devolvió, se dice en español (sección 6.2 y 6.3). No se abre el contrato en disco.

### 6.7 Traza

Función pura, cubierta por la prueba:

- `trace.url` es un string no vacío con esquema `http` o `https` → enlace. El `href` es ese string, tal cual. Se abre en pestaña nueva con `rel="noopener noreferrer"`. El texto visible dice que es la traza guardada en el registro.
- `trace.url` es `null`, vacío o solo espacios → texto visible «sin traza». Aunque `langsmith_run_id` tenga valor.
- Cualquier otro `url` (`javascript:`, ruta relativa, esquema distinto) no se vuelve enlace. Texto: «sin traza». No se sustituye por una URL de LangSmith.

No llamar a LangSmith. No incrustar nodos, prompts ni latencias. No afirmar en la UI ni en el tablero que el proyecto LangSmith está configurado: una URL presente solo prueba que el registro la trae.

El `langsmith_run_id`, si no es `null`, puede mostrarse como dato de texto, nunca como `href`.

## 7. Recorrido

El recorrido abre la URL directa. No depende de que T4.4 exista.

1. Levantar el API como en `docs/T4_3_SPEC.md` §8 (proceso local, sin commitear entrypoint, sin añadir `uvicorn` a `pyproject.toml`). Antes de servir, insertar **un** `DecisionRecord` sintético en el almacén de ese proceso (`MemoryStore.add_decision` o el store que ese proceso ya use). Sin endpoint nuevo. Sin commit de esa semilla. Forma válida: la de `docs/04` §5 o `backend/tests/api/support.py` (`id` `dec_0042`, al menos un chequeo, al menos un campo extraído no nulo, `trace.url` o bien una URL `https://example.test/...` o bien `null`).
2. Abrir `http://localhost:3000/decisiones/` más ese `id` (no el `invoice_id`). Se ve el chequeo (regla, resultado, detail y on_fail o la frase de nulo), un campo extraído y el estado de la traza: el enlace con el `href` igual a `trace.url`, o el texto «sin traza».
3. Abrir `/decisiones/dec_no_existe`. Pantalla en español de la sección 5. No aparece Globex ni un monto inventado.
4. Recargar el id del paso 2: los mismos textos. La pantalla no ha escrito el registro.

Con `MemoryStore` el registro muere al cerrar el proceso. No afirmar que sobrevivió a un reinicio. Probar `SqlStore` aquí no es obligatorio.

Anotar en el cierre si la traza del paso 2 estaba presente o era «sin traza». Las dos salidas cumplen. La otra rama la cubre la prueba de la función pura.

## 8. Arranque del recorrido

Igual que T4.3 §8. Host del API `127.0.0.1`, puerto 8000, `API_URL` del `.env.example` ya existente. El navegador habla con Next. Next reenvía. No hace falta cabecera CORS.

No hace falta `POST /invoices` ni el grafo para este recorrido. Sembrar un registro evita claves y red.

## 9. Diseño

Seguir `frontend-design` con una restricción: continuar T4.3. Tokens ya en `frontend/app/globals.css` y `frontend/app/layout.tsx`:

- Lienzo `#e8ecf1`, superficie blanca, tinta `#152033`, tinta secundaria `#5c6778`, línea `#c5cdd8`
- Acento `#b45309`
- Éxito `#166534` para `OK`, peligro `#9f1239` para `FALLA`, acento o tinta secundaria para `INDETERMINADO`
- Source Serif 4 en títulos (`--font-display`), DM Sans en el resto (`--font-sans`)

No añadir otra paleta, otra pareja tipográfica ni un tema distinto. La página es la ficha de una decisión en el mismo puesto de control. Copiar en español, voz activa. El 404 dice que ese id no está, no un ensayo de marca.

Teclado, foco visible, ancho de móvil usable. `prefers-reduced-motion` ya está en el CSS global; no añadir animación obligatoria.

`vercel-react-best-practices`: un solo fetch al montar la ficha. No prefetch de LangSmith, de reglas ni del listado. No hace falta memoizar esta página por adelantado.

## 10. Qué no afirmar

- Que LangSmith está configurado, que hay `run_id` en la nube o que el enlace abre un proyecto real.
- Que la lista, las aprobaciones, las métricas o la subida existen.
- Que un deploy público ya sirve esta ruta.
- Que la pantalla recalcula la decisión o completa una cláusula que faltaba.
- Que hay auth.
- Que G3 o G4 están cerrados.
- Que el registro de la semilla sigue tras reiniciar el API en memoria.

## 11. Criterios de aceptación

1. Recorrido en navegador (no basta una captura): el id sintético muestra al menos un chequeo, un campo extraído y el estado de la traza (enlace con la URL del registro, o «sin traza»); el id ausente muestra el 404 en español sin documento inventado. Anotar la herramienta y cuál de los dos estados de traza se vio.
2. `npx tsc --noEmit` en `frontend/` — ok. El lint del proyecto Next — ok.
3. Prueba de la función de traza y de los nulos — verde. URL `https` → enlace con ese `href`. `url` null con `langsmith_run_id` presente → «sin traza» y sin `href`. Campo `null` → «no consta». `on_fail` null → la frase de la sección 6.3, no un `FRENAR`/`ESCALAR` inventado.
4. `git status` sin `.env`, sin `.env.local`, sin `node_modules`, sin secretos, sin el script de semilla.
5. Diff de `backend/` y de `backend/openapi.json` vacío.
6. Tablero: T4.5 HECHA con la nota del recorrido. T4.4 y T4.6–T4.9, G3 y G4 siguen PENDIENTE. T4.3 sigue HECHA.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit: `T4.5: decision detail with checks and trace link`.

## 12. Subtareas

- T4.5.1 Proxy `GET` `/api/decisions/[id]` hacia `${API_URL}/decisions/{id}`. Sin otras rutas nuevas.
- T4.5.2 Funciones puras: estado de traza, nulos, cita solo desde el registro. Prueba roja y luego verde.
- T4.5.3 Página `/decisiones/[id]` según el plan que adopta T4.3. Un fetch. Sin botones de aprobación ni edición.
- T4.5.4 Recorrido de la sección 7 en el navegador. Tablero. Commit y push.

## 13. Mensaje para la sesión que implementa

```text
Implementa T4.5 según docs/T4_5_SPEC.md.
Skill: frontend-design (léela; el plan visual adopta el puesto de T4.3, sin segunda paleta).
Al escribir la página, vercel-react-best-practices.
No uses ui-ux-pro-max, supabase, langfuse ni langchain-rag.
No edites backend/, data/, openapi.json ni docs/T4_4_SPEC.md.
La pantalla lee GET /decisions/{id} por un proxy same-origin.
Muestra extracción, chequeos y la explicación guardada. No llames a decide() ni a un LLM.
Enlace de traza solo si trace.url es http(s). Si no, el texto «sin traza». No inventes la URL.
Un 404 es una pantalla en español, sin documento inventado.
No construyas la lista, las aprobaciones ni el deploy. G3 y G4 siguen abiertos.
Al terminar: recorrido en navegador, tsc, commit y push (sección 11.8).
```
