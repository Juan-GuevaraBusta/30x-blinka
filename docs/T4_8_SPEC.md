# Spec T4.8 — UI `/subir`

Dueño: **Frontend**. El `POST /invoices` ya es de API (T4.1); esta tarea no lo cambia. Skill de dominio: `frontend-design` (PARCIAL, tablero: solo la pantalla). Al escribir la página: `vercel-react-best-practices` (PARCIAL). No usar `ui-ux-pro-max` (dos criterios visuales). No usar `supabase`, `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **implemente** T4.8. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D037**.

No es camino crítico. `docs/05` línea de corte 3: si hay retraso, T4.8 se corta y la demo usa facturas precargadas. Si se hace, el contrato es este.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (I2 el LLM no decide; I3 fail-closed; I6 solo datos sintéticos; I7 el texto del archivo no es instrucción; I8 cero dinero)
- `docs/T4_1_SPEC.md` §5.3 (multipart) y §5.6 (429)
- `docs/T4_3_SPEC.md` §9 (continuidad visual de `/reglas`)
- `docs/SKILLS_MAP.md` fila T4.8
- `docs/05_PHASES_AND_ROADMAP.md` línea de corte 3
- `backend/app/api/app.py` (`post_invoice`, `_read_capped`) y `backend/app/api/schemas.py` (`InvoiceUpload`, `InvoiceMeta`, `MAX_INVOICE_BYTES`)
- `backend/openapi.json` path `/invoices` y schema `DecisionRecord`
- `backend/tests/api/test_invoices.py` y `backend/tests/api/support.py` (`default_processor`, `make_record`)
- `data/invoices/catalog.json` filas `dev-001` y `dev-004` (el operador copia metadatos; la app no carga el catálogo)
- `frontend/README.md`, `frontend/app/globals.css`, `frontend/app/api/rules/route.ts`

Declarar la skill en una línea, leer `frontend-design` y escribir un plan visual corto **antes** de los componentes. El plan reutiliza la pantalla de T4.3; no abre una identidad nueva. Luego leer `vercel-react-best-practices` solo para esta página: un envío, sin cadena de requests.

No editar `backend/`, `data/`, `eval/`, `docs/04` ni `backend/openapi.json`. Si el recorrido exige CORS, un endpoint nuevo o un entrypoint commiteado, **parar**.

G3 y G4 siguen PENDIENTE. No hay deploy.

## 1. Qué es T4.8

Una sola pantalla nueva, **`/subir`**, en español. El operador adjunta un archivo sintético y envía el multipart que ya define T4.1. Si el API responde 201, la misma pantalla muestra la decisión devuelta. Subir no mueve dinero (I8).

Ruta `/subir`, no una segunda `/decisiones`. `/decisiones` es la tabla de T4.4 y `/decisiones/[id]` es el detalle de T4.5. Esta pantalla tiene que poder enseñar el resultado aunque esas dos no existan. El tablero marca dependencia de T4.1 y T4.4: T4.1 ya está; T4.4 no se construye aquí. El criterio de T4.8 se cumple con el cuerpo del POST en `/subir`.

| Pieza | Qué hace |
|---|---|
| App | La Next.js de T4.3, en `frontend/` |
| Envío | El navegador hace `POST /api/invoices` (mismo origen). Next reenvía el multipart a `${API_URL}/invoices` |
| Éxito | Solo HTTP **201** con `id`, `decision` y `summary` en el cuerpo |
| Fracaso | 422, 409, 429, red o cuerpo incompleto: error en español. Cero decisión inventada |
| Resultado | En la misma pantalla. Enlace a `/decisiones/[id]` con el `id` del registro; esa ruta puede responder 404 hasta T4.5 |

## 2. Fuera de alcance

- Construir `/decisiones`, `/decisiones/[id]`, `/aprobaciones` o `/metricas` (T4.4–T4.7). El enlace al detalle no es esa pantalla.
- Auth, API keys de cliente, JWT.
- CORS, `render.yaml`, Vercel, Postgres, bind `0.0.0.0:$PORT` (T4.9).
- Añadir o cambiar un endpoint. Editar `backend/`, modelos, OpenAPI o `data/`.
- Llamar a `decide()`, al grafo, a un LLM o a `run_invoice` desde la UI o desde el arranque de este recorrido.
- Leer el PDF o el txt en el navegador para proponer una decisión. El archivo es dato (I7), no instrucciones.
- Tratar el `expected_decision` del catálogo como lo que la pantalla debe mostrar.
- Cerrar G3 o G4. El doble de tests no es el e2e del grafo.
- Mover dinero. Un 201 con `decision: "PAGAR"` es un registro simulado (I8).

## 3. Archivos

Crear en `frontend/`:

- `app/subir/page.tsx` y los componentes de esa pantalla.
- `app/api/invoices/route.ts`: solo `POST`. Lee el `FormData` y lo reenvía. No fija `Content-Type` a mano (el boundary lo pone `fetch`). No convierte el archivo a JSON. Devuelve el status y el cuerpo del API, incluido 422, 409 y 429.
- Route handler, no Server Action: el tope de esta subida es 2_000_000 bytes y no debe cortarse en un límite menor del framework.
- Funciones puras: archivo presente y tamaño en rango; «esto cuenta como éxito». Prueba de esas funciones (Vitest, como T4.3). Sin Playwright en CI.

Modificar:

- `frontend/README.md`: cómo abrir `/subir` y que el proxy es `/api/invoices`.
- Al cerrar la implementación: `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`.

No tocar el comportamiento de `/reglas`. `/` sigue redirigiendo a `/reglas`. En `/subir`, un enlace de texto a `/reglas`. No añadir un menú que presente como hechas las rutas de T4.4–T4.7.

No tocar `backend/`, `data/`, `openapi.json`.

## 4. Invariantes

- I2. La UI no llama a `decide()` ni a un LLM. El procesador inyectado del API ya construyó el `DecisionRecord` (T4.1). La pantalla solo muestra ese JSON.
- I3. Error de red, timeout, 5xx, 429, cuerpo que no trae `id` + `decision` + `summary`, o `decision` fuera de `PAGAR` | `ESCALAR` | `FRENAR` → mensaje de error. No se rellena una decisión por defecto.
- I6. El archivo del recorrido sale de `data/invoices/dev/`. Empresa de ejemplo: Acme Demo Inc. Sin datos reales ni claves. `API_URL` no se loguea.
- I7. Los bytes y el texto del archivo no se interpretan, no se inyectan en el DOM como HTML y no se mandan a un modelo desde esta pantalla.
- I8. Una frase visible: subir registra una decisión simulada; no hay pago.

Un 422 o un 409 no sustituye el último 201 ni se rotula como decisión de este envío.

## 5. Contrato HTTP que la UI consume

Sin prefijo en el API (`/invoices`). El navegador no llama a otro origen. No hay CORS.

`POST` `multipart/form-data`. Campos, todos obligatorios, copiados de `Body_post_invoice_invoices_post` y de `InvoiceMeta`. No hay otros.

| Campo | Regla real |
|---|---|
| `file` | obligatorio. `MAX_INVOICE_BYTES = 2_000_000`. Vacío o mayor → 422, `detail` = `invalid_file_size`. 2_000_000 bytes exactos sí pasan |
| `invoice_id` | string, 1–64, patrón `^\S+$` (sin espacios) |
| `channel` | `pdf_text` \| `image` \| `email` \| `chat`. Otro valor → 422 |
| `received_at` | ISO-8601 con zona (`AwareDatetime`). Naive → 422 |

Respuestas que existen:

| Status | Cuándo | Cuerpo que ya devuelve el API |
|---|---|---|
| **201** | El procesador devolvió un registro y el almacén lo guardó | JSON `DecisionRecord` |
| **422** | Metadatos inválidos, archivo vacío o enorme, o `InvoiceRejected` | `detail`: lista de errores de validación, o el string `invalid_file_size`, o un código corto (en el test, `rejected`). Sin traceback |
| **409** | `invoice_id` ya guardado, o `DuplicateDecisionError` | `{"detail":"duplicate_invoice"}` |

`backend/openapi.json` documenta en este path **201** y **422**. El **409** está en `app.py` y en `docs/T4_1_SPEC.md` §5.3; no se edita el OpenAPI para añadirlo. No existe un 200 de éxito en este POST. El proxy no reescribe el 201.

`DecisionRecord` (campos que esta pantalla tiene que saber nombrar, sin inventar otros en el formulario):

- `id` (string, min 1) — este es el segmento de `/decisiones/[id]`, no el `invoice_id`
- `invoice_id`
- `decision`: `PAGAR` \| `ESCALAR` \| `FRENAR`
- `summary` (string, min 1)

El 201 trae más campos obligatorios (`received_at`, `severity`, `extracted`, `checks`, `jev_signals`, `verifier`, `next_step`, `trace`, `versions`, `human_events`; `admin_notice` puede ser null). Se pueden mostrar como texto del registro en la misma pantalla. No se maqueta el detalle de T4.5 (chequeos con cláusula, enlace de traza como producto).

Rate limit (T4.1 §5.6), por si aparece: **429**, `{"detail":"rate_limited"}`, header `Retry-After: 60`. Es un error, no una decisión. La clave del límite es la IP que ve el API; con este proxy, esa IP es el proceso Next. No se cambia el límite ni se añade límite por usuario.

Antes de enviar, el cliente exige archivo elegido y tamaño de 1 a 2_000_000 bytes inclusive. Si falta el archivo, o está vacío, o pasa de 2_000_000, no hay `fetch`. Los tres metadatos van en el multipart; si faltan, no se envía. Un 422 del servidor no se muestra como éxito.

## 6. Qué se muestra tras el envío

Solo un 201 válido pinta resultado:

- `decision`, `summary` e `id`, en ese orden visual, como texto.
- Enlace a `/decisiones/` + `id` del registro. El texto del enlace dice que el detalle puede no existir todavía.
- El resto del JSON, si se muestra, es el cuerpo recibido, en un bloque de texto. No se pide `GET /decisions/{id}` para «completar» la pantalla.

Cualquier otro desenlace deja un error en español que dice qué pasó (rechazo del servidor, factura ya registrada, límite, o el API no respondió). No aparece un `PAGAR`, `ESCALAR` o `FRENAR` de relleno. Si había un 201 anterior, sigue etiquetado como el último aceptado y no como el resultado del envío que falló.

## 7. Recorrido

Textos de la interfaz en español. El botón dice que envía la factura al registro. Junto al resultado, la frase de que no se mueve dinero.

El procesador de la sesión es el doble de tests, no el grafo. La decisión en pantalla es la del 201, no la etiqueta `expected_decision` del catálogo. Con `make_record`, ese cuerpo trae `decision` `ESCALAR` y un `summary` fijo del ejemplo de `support.py`. Ver `ESCALAR` después de subir `dev-001` es correcto para este recorrido. Afirmar que el corpus pagó esa factura sería cerrar G3, y G3 sigue abierto.

1. Abrir `/subir`. No hay decisión pintada.
2. Adjuntar `data/invoices/dev/dev-001_normal_pay.pdf`. Rellenar, copiando la fila `dev-001` del catálogo (la persona, no la app): `invoice_id` `dev-001`, `channel` `pdf_text`, `received_at` `2025-12-22T10:00:00Z`. Enviar. La respuesta es 201. Se leen `decision`, `summary` e `id` del cuerpo. El enlace apunta a `/decisiones/` + ese `id`. Abrirlo puede ser 404: T4.5 no es requisito.
3. Alternativa equivalente: `data/invoices/dev/dev-004_normal_pay.txt`, `invoice_id` `dev-004`, `channel` `chat`, `received_at` `2026-01-26T10:00:00Z`. Un solo archivo basta.
4. Elegir un archivo vacío, o uno de 2_000_001 bytes (generado en la sesión, no commiteado en `data/`). El cliente no envía, o el servidor responde 422. No aparece una decisión de ese intento.
5. Repetir el mismo `invoice_id` del paso 2. Respuesta 409, `detail` `duplicate_invoice`. No es un segundo éxito.

No usar `data/invoices/holdout/` ni un PDF de fuera del corpus.

## 8. Arranque del recorrido

El backend no tiene entrypoint (T4.9). Para el navegador, la sesión levanta el API **sin commitear** un módulo nuevo y **sin** añadir `uvicorn` a `pyproject.toml`. Si `uvicorn` no está en el venv, se instala solo en local.

`PYTHONPATH=backend`, almacén en memoria, reglas desde `data/rules.json`, reloj y `rate_limit` holgados (el 429 no es el caso de este recorrido). Host `127.0.0.1`, puerto 8000, alineado a `API_URL`.

Procesador: el doble de `backend/tests/api/support.py`, no `run_invoice`. `default_processor` siempre devuelve `id` `dec_0042`. Un segundo `invoice_id` distinto puede acabar en 409 porque ese `id` ya está en el almacén. El script local, sin commit, puede envolver `make_record` y pasar `invoice_id=upload.invoice_id` con un `id` distinto por envío. Sigue sin llamar a `decide()` ni al grafo. Ese script no entra en el diff.

Este recorrido demuestra el contrato HTTP y la UI. No demuestra el e2e del grafo y no cierra G3.

El navegador habla con Next. Next reenvía al API. No hace falta cabecera CORS. El proceso muere al cerrar la sesión. Con `MemoryStore` el 201 no sobrevive a un reinicio. Probar `SqlStore` aquí no es obligatorio.

## 9. Diseño

Continuidad de T4.3. Reutilizar las variables de `frontend/app/globals.css` (`--canvas`, `--surface`, `--ink`, `--ink-muted`, `--line`, `--accent`, `--danger`, `--success`), DM Sans, Source Serif 4 y el ancho `max-w-4xl`. Puesto de control, no un landing. Una sola acción primaria: enviar. El error usa el rojo ya definido; no se inventa otra paleta.

Plan corto de `frontend-design` antes del código, limitado a esta pantalla. Copiar en español, voz activa. El error dice qué corregir (falta archivo, pesa de más, el servidor rechazó, ya estaba registrada).

Teclado: el input de archivo, los tres metadatos y el botón se alcanzan con Tab y el foco se ve. Usable en un ancho de móvil.

`vercel-react-best-practices`: no hay fetch al entrar. Un POST al enviar. No se encadena un GET del detalle.

## 10. Qué no afirmar

- Que `/decisiones` o el detalle existen.
- Que el 201 del doble es la decisión del corpus o que `dev-001` quedó en PAGAR.
- Que G3 o G4 están cerrados.
- Que un deploy público ya sirve `/subir`.
- Que hay CORS, auth o un endpoint nuevo.
- Que el OpenAPI lista el 409 (no lo lista; el código sí lo devuelve).
- Que subir mueve dinero.
- Que T4.8 es imprescindible para la demo (la línea de corte 3 lo permite saltar).

## 11. Criterios de aceptación

1. Recorrido en navegador (no basta una captura): el paso 2 o el 3 del §7 muestra `decision`, `summary` e `id` del 201; el paso 4 se ve como rechazo. Anotar la herramienta y el resultado en el tablero. Decir en la nota que el procesador fue el doble, no el grafo.
2. `npx tsc --noEmit` en `frontend/` — ok. El lint del proyecto Next — ok.
3. La prueba de las funciones puras — verde. Sin archivo, 0 bytes y 2_000_001 → no se envía. 1 byte y 2_000_000 → tamaño aceptable. Solo el status 201 con los tres campos cuenta como éxito.
4. `git status` sin `.env`, sin `.env.local`, sin `node_modules`, sin el script local del API, sin secretos, sin un archivo enorme de prueba.
5. Diff de `backend/` y de `backend/openapi.json` vacío. Diff de `data/` vacío.
6. Tablero: T4.8 HECHA con la nota del recorrido, o sigue PENDIENTE si se corta por la línea de corte. T4.4–T4.7 y T4.9, G3 y G4 siguen PENDIENTE salvo las que ya estuvieran hechas por su propia tarea.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit: `T4.8: invoice upload screen posts to the API`. Push a la rama de seguimiento.

## 12. Subtareas

- T4.8.1 Proxy `POST /api/invoices` que reenvía el multipart y el status. Sin endpoint nuevo.
- T4.8.2 Funciones puras de archivo y de «éxito = 201 con id, decision y summary». Prueba roja y luego verde.
- T4.8.3 Página `/subir` con el plan de continuidad visual. Validación de archivo antes del `fetch`. Resultado o error según §6.
- T4.8.4 Recorrido del §7 en el navegador, con el doble. Tablero. Commit y push.

## 13. Mensaje para la sesión que implementa

```text
Implementa T4.8 según docs/T4_8_SPEC.md.
Skill: frontend-design (PARCIAL). Léela y escribe el plan visual antes del código;
el plan continúa /reglas (mismos tokens), no abre otra identidad.
Al escribir la página, vercel-react-best-practices (PARCIAL).
No uses ui-ux-pro-max, supabase, langfuse ni langchain-rag.
No edites backend/, data/ ni openapi.json. No añadas endpoint ni CORS.
La pantalla es /subir. El navegador hace POST /api/invoices y Next reenvía el multipart.
Éxito = 201 con id, decision y summary, en la misma pantalla.
422, 409 y un fallo de red no son una decisión. No llames a decide() ni al grafo.
El recorrido usa el doble de tests: no cierra G3. G4 sigue abierto.
Al terminar: recorrido en navegador, tsc, commit y push (sección 11.8).
```
