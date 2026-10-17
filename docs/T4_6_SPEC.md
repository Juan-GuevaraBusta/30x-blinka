# Spec T4.6 — UI `/aprobaciones`

Dueño: **Frontend**. Skill de dominio: `frontend-design` (TOTAL). Rendimiento al escribir la página: `vercel-react-best-practices` (PARCIAL). No usar `ui-ux-pro-max` (dos criterios visuales). No usar `supabase`, `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **implemente** T4.6. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D035**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (I2 el LLM no decide el pago; I5 la explicación sale de plantillas; I8 cero dinero: aprobar es estado simulado)
- `docs/04_RULES_AND_DECISION_SPEC.md` §1 y §5 (el evento humano no reescribe la decisión del agente)
- `docs/05_PHASES_AND_ROADMAP.md` T4.6
- `docs/T4_1_SPEC.md` §5.2 y §5.4
- `docs/SKILLS_MAP.md` fila T4.6
- `docs/TASK_BOARD.md` nota T4.6
- `backend/app/models/domain.py` (`HumanEvent`, `HumanAction`, `DecisionRecord.human_events`)
- `backend/app/api/schemas.py` (`HumanDecisionBody`)
- `backend/app/api/app.py` (`GET /decisions`, `POST /decisions/{id}/approve`, `POST /decisions/{id}/reject`)
- `backend/openapi.json` paths `/decisions`, `/decisions/{id}/approve`, `/decisions/{id}/reject` y schema `HumanDecisionBody`
- `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/app/api/rules/route.ts`

Declarar la skill en una línea, leer `frontend-design` y seguir su proceso: plan visual corto y revisión contra el brief **antes** de escribir componentes. El plan **confirma** los tokens ya puestos en T4.3 (sección 9). No abre una segunda paleta. Luego leer `vercel-react-best-practices` solo para no meter waterfalls ni renders de más en esta página.

No editar `backend/`, `data/`, `eval/`, `docs/04`, `pyproject.toml` ni `backend/openapi.json`. Si el recorrido exige CORS, un entrypoint commiteado o un endpoint nuevo, **parar**: CORS y el entrypoint son T4.9; la cola ya existe.

G3 y G4 siguen PENDIENTE. Esta tarea es la pantalla de aprobaciones (`docs/05`: no se corta). No anticipar T4.4, T4.5, T4.7 ni T4.8.

## 1. Qué es T4.6

Una sola pantalla nueva, `/aprobaciones`, en español. Muestra la cola de decisiones del agente cuyo valor es `ESCALAR` y deja aprobar o rechazar con motivo. El `DecisionRecord` conserva `decision` y `severity`. El éxito añade un `HumanEvent`. Un motivo vacío no se envía; si el servidor responde 422, la UI no cuenta el evento como registrado.

| Pieza | Qué hace |
|---|---|
| App | La Next.js de T4.3, App Router, TypeScript estricto, dentro de `frontend/` |
| Cola | `GET /decisions?decision=ESCALAR`. No hay otra ruta de cola en el OpenAPI |
| Acciones | `POST /decisions/{id}/approve` y `POST /decisions/{id}/reject` |
| Cuerpo | Solo `{ "author", "reason" }`. El cliente no manda `at`, `action` ni `decision` |
| Motivo | Obligatorio en el cliente (texto recortado, 1–500). Vacío no sale del navegador |
| 422 | El OpenAPI lo declara en approve y en reject. La tarjeta no gana un evento |
| Éxito | 200, cuerpo = `DecisionRecord`. `decision` sigue `ESCALAR`. Hay un `HumanEvent` nuevo |

El id del path es `DecisionRecord.id`, no `invoice_id`.

## 2. Fuera de alcance

- Lista general `/decisiones` con filtros Pagadas / Frenadas / Pendientes (T4.4).
- Detalle `/decisiones/[id]`: chequeos, cláusula, explicación larga, enlace a la traza (T4.5). Un enlace o un cascarón vacío no cuenta como esas pantallas.
- `/metricas` (T4.7) y subida de factura (T4.8).
- Auth, API keys de cliente, JWT.
- CORS, `render.yaml`, Vercel, Postgres, bind `0.0.0.0:$PORT` (T4.9).
- Endpoint nuevo de cola, de pendientes o de “solo sin evento”.
- Editar `backend/`, modelos, OpenAPI o el motor. Aunque el cliente exija motivo, no se parchea el servidor en esta tarea.
- Reescribir `decision` o `severity` al aprobar o rechazar (I2, `docs/04` §1 y §5).
- LangChain, Langfuse, RAG, Supabase.
- Cerrar G3, G4 o G5.
- Mover dinero. Aprobar es un evento sobre un estado simulado (I8).

`/reglas` (T4.3) se queda como está. No se rediseña.

## 3. Archivos

Crear en `frontend/`:

- `app/aprobaciones/page.tsx` y el componente de esa pantalla.
- Proxy same-origin, mismo estilo que `app/api/rules/route.ts`:
  - `GET` que reenvía a `${API_URL}/decisions?decision=ESCALAR`
  - `POST` que reenvía a `${API_URL}/decisions/{id}/approve`
  - `POST` que reenvía a `${API_URL}/decisions/{id}/reject`
- Funciones puras: motivo y autor enviables, cuerpo `{author, reason}`, y lectura del 200 (decisión intacta, un evento más). Prueba en el runner que ya usa el frontend (vitest). Sin Playwright en CI.

Modificar:

- `frontend/README.md`: esta pantalla ya se puede construir con el OpenAPI de T4.1. La frase que deja `/aprobaciones` fuera de alcance queda limitada al resto de rutas (T4.4, T4.5, T4.7, T4.8).
- Al cerrar la implementación: `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`.

No tocar `backend/`, `data/`, `openapi.json`. `API_URL` ya está en `frontend/.env.example`. No añadir claves.

El navegador llama a rutas bajo `/api/…` del propio Next. Next reenvía al API. Así no hace falta CORS.

## 4. Invariantes

- I2. La pantalla no llama a un LLM ni a `decide()`. No elige `PAGAR` ni `FRENAR`. El 200 se muestra solo si `decision` y `severity` son los de antes (`ESCALAR` y `1`). Si un 200 trajera otra decisión, la UI no lo trata como éxito y no sustituye la tarjeta.
- I5. El texto que explica la factura es el `summary` (y el `detail` que ya venga en el registro), salido de plantillas. Esta pantalla no redacta una explicación nueva.
- I6. Autor de ejemplo `cfo@demo.test`. Beneficiarios y empresa de los registros sintéticos (`Globex LLC`, `Acme Demo Inc.`). No pegar datos reales ni claves. `API_URL` no se loguea.
- I8. El botón de aprobar no paga. La copia lo dice: queda un evento; no se mueve dinero; la decisión del agente sigue `ESCALAR`.

Un 422, un 404 o un 409 no añaden un `HumanEvent` en la tarjeta. La `decision` mostrada sigue siendo la del agente.

## 5. Contrato HTTP que la UI consume

Sin prefijo en el API. Nombres reales del OpenAPI y de `app.py`. No inventar rutas.

| Llamada | Cuerpo | Éxito | Fracaso que la UI debe conocer |
|---|---|---|---|
| `GET /decisions?decision=ESCALAR` | — | 200, array de `DecisionRecord` | Otro valor de `decision` es 422 en el OpenAPI. Esta pantalla solo pide `ESCALAR` |
| `POST /decisions/{id}/approve` | `HumanDecisionBody` | 200, `DecisionRecord` | 422 |
| `POST /decisions/{id}/reject` | `HumanDecisionBody` | 200, `DecisionRecord` | 422 |

`HumanDecisionBody` en `backend/openapi.json`:

- `author`: string, `minLength` 1, `maxLength` 500
- `reason`: string, `minLength` 1, `maxLength` 500
- `additionalProperties: false`
- `required`: `author`, `reason`
- Descripción del schema: el cliente no envía `at` ni una decisión nueva

El 422 de approve y de reject está en el OpenAPI (`HTTPValidationError`). Un `reason` `""`, un campo ausente o un campo extra lo provocan. `app.py` arma el `HumanEvent` solo después de validar el cuerpo.

`app.py` además, y **no** está listado en esas dos respuestas del OpenAPI:

- 404 `detail` `not_found` si el id no existe
- 409 `detail` `not_escalated` si `decision` no es `ESCALAR`

La UI los muestra en español y no los cuenta como evento. No se edita el OpenAPI para documentarlos.

`at` lo pone el reloj del servidor. `action` la pone la ruta: `aprobada_humano` o `rechazada_humano` (`HumanAction`).

No hay query de “pendientes” ni path `/approvals`. La cola es el filtro `decision=ESCALAR`.

## 6. Cola y evento

Un solo `GET` al entrar. Del array:

- **Pendiente:** `decision === "ESCALAR"` y `human_events` vacío. Aquí van aprobar y rechazar.
- **Con evento:** el mismo array, `human_events` con al menos un elemento. Sigue mostrando `decision` `ESCALAR` y la lista de eventos (autor, fecha, `action`, motivo). No se oculta: el filtro HTTP la sigue devolviendo porque la decisión del agente no cambió.

`PAGAR` y `FRENAR` no entran en ese GET. No hace falta un segundo filtro en el cliente para esconderlos.

Cada pendiente muestra, como mínimo: `id`, `invoice_id`, la palabra `ESCALAR`, `severity` 1, `summary`, beneficiario y monto si vienen en `extracted`, y `next_step`. Sin la tabla de chequeos ni el enlace de traza (eso es T4.5).

Formulario por tarjeta:

- Autor, precargado con `cfo@demo.test`, editable.
- Motivo, vacío al abrir.
- Botones «Aprobar» y «Rechazar».

Envío: recortar autor y motivo. Si alguno queda vacío o pasa de 500 caracteres, no hay `fetch`. El OpenAPI trata un espacio suelto como longitud 1; el cliente igual lo rechaza tras recortar. El JSON lleva solo esas dos claves.

Tras un 200 de aprobar: la tarjeta pasa al grupo con evento, `action` `aprobada_humano`, `decision` sigue `ESCALAR`, `severity` sigue 1. Tras un 200 de rechazar con motivo: igual, con `rechazada_humano`.

Tras un 422 (o si el cliente ni siquiera envió): el grupo pendiente no se mueve y `human_events` de esa tarjeta sigue igual.

Cola vacía: una frase en español. No se inventan facturas.

## 7. Recorrido

Textos de la interfaz en español. Dos registros sintéticos `ESCALAR` con `human_events` vacío, y uno `PAGAR`, cargados en el proceso local (sección 8). Ids distintos. Motivo de ejemplo: `Coincide con el presupuesto`.

1. Abrir `/aprobaciones`. Se ven las dos `ESCALAR`. La `PAGAR` no está.
2. En la primera, pulsar Rechazar con el motivo en blanco (o solo espacios). No sale la petición, o el servidor responde 422. Recargar: esa factura sigue en pendientes, `human_events` sigue `[]`, `decision` sigue `ESCALAR`, `severity` sigue 1.
3. En la segunda, autor `cfo@demo.test` y motivo `Coincide con el presupuesto`. Aprobar. La respuesta es 200. `decision` sigue `ESCALAR`, `severity` sigue 1, y aparece un `HumanEvent` con `action` `aprobada_humano`, ese autor y ese motivo. `at` viene del servidor. Recargar: el evento sigue ahí y la decisión del agente sigue `ESCALAR`.
4. La primera factura, la del paso 2, sigue sin evento.

## 8. Arranque del recorrido

El backend no tiene entrypoint (T4.9). Para el navegador, la sesión levanta el API **sin commitear** un módulo nuevo y **sin** añadir `uvicorn` a `pyproject.toml`. Si `uvicorn` no está en el venv, se instala solo en local para el recorrido.

`PYTHONPATH=backend`, almacén en memoria, reglas desde `data/rules.json`, reloj y límite holgados. El procesador de facturas no se usa. Antes de servir, `add_decision` de tres `DecisionRecord` sintéticos válidos (el ejemplo de `backend/tests/api/support.py` vale como forma): dos `ESCALAR` (`severity` 1, `human_events` `[]`) y uno `PAGAR` (`severity` 0). Host `127.0.0.1`, puerto 8000, alineado a `API_URL`.

El navegador habla con Next. Next reenvía al API. No hace falta cabecera CORS.

Ese proceso muere al cerrar la sesión. No afirmar que el evento sobrevivió a un reinicio del backend: con `MemoryStore` no sobrevive. Probar `SqlStore` aquí no es obligatorio.

## 9. Diseño

Continuar T4.3. Lienzo `#e8ecf1`, superficie blanca, tinta `#152033`, acento `#b45309`, Source Serif 4 para el título y DM Sans para el resto. Esos tokens ya viven en `frontend/app/globals.css` y `frontend/app/layout.tsx`. Reutilizarlos. No cambiar la fuente global ni el title de `/reglas`.

La pantalla es la cola de un puesto de control, no un landing. Una sola decisión visual fuerte; el resto, quieto. Copiar en español, voz activa. El error de motivo vacío dice que hace falta un motivo. El error 422 dice que el servidor no registró el evento.

Accesible por teclado, foco visible, usable en un ancho de móvil. El motivo vacío no se dispara con Enter.

`vercel-react-best-practices`: un fetch al entrar. Autor por defecto es una constante, no un `GET /rules` previo. No hace falta memoizar esta página por adelantado.

## 10. Qué no afirmar

- Que `/decisiones`, el detalle, `/metricas` o la subida existen.
- Que un deploy público ya sirve `/aprobaciones`.
- Que aprobar cambió la decisión del agente a `PAGAR` o que se movió dinero.
- Que el 422 está solo en el cliente. El OpenAPI lo declara.
- Que hay una ruta de cola distinta de `GET /decisions?decision=ESCALAR`.
- Que hay auth.
- Que G3 o G4 están cerrados.
- Que el evento sigue en disco tras matar el proceso en memoria.

## 11. Criterios de aceptación

1. Recorrido en navegador (no basta una captura): el paso 2 deja la primera factura sin evento y en `ESCALAR`; el paso 3 deja la segunda en `ESCALAR` con un `HumanEvent` `aprobada_humano`. Anotar la herramienta (Playwright u otra) y el resultado en el tablero.
2. `npx tsc --noEmit` en `frontend/` — ok. El lint del proyecto Next — ok.
3. La prueba de las funciones puras — verde. Motivo vacío o en blanco → no enviable. Motivo y autor válidos → cuerpo solo con esas dos claves. Un 200 con la misma `decision` y un evento más → éxito. Un 422 → la lista de eventos no crece.
4. `git status` sin `.env`, sin `.env.local`, sin `node_modules`, sin secretos, sin el lanzador local del API.
5. Diff de `backend/` y de `backend/openapi.json` vacío.
6. Tablero: T4.6 HECHA con la nota del recorrido. T4.4, T4.5, T4.7, T4.8, T4.9, G3 y G4 siguen PENDIENTE.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit: `T4.6: approval queue that appends human events`.

## 12. Subtareas

- T4.6.1 Proxy same-origin de la lista `ESCALAR` y de approve/reject. Sin otras pantallas.
- T4.6.2 Funciones puras del motivo, del cuerpo y del 200. Prueba roja y luego verde.
- T4.6.3 Página `/aprobaciones` según el plan de `frontend-design`, con los tokens de T4.3. Un GET al entrar. POST solo si autor y motivo recortados son válidos.
- T4.6.4 Recorrido del §7 en el navegador. Tablero. Commit y push.

## 13. Mensaje para la sesión que implementa

```text
Implementa T4.6 según docs/T4_6_SPEC.md.
Skill: frontend-design (léela y escribe el plan visual antes del código; conserva lienzo #e8ecf1, acento #b45309, Source Serif 4 y DM Sans).
Al escribir la página, vercel-react-best-practices.
No uses ui-ux-pro-max, supabase, langfuse ni langchain-rag.
No edites backend/, data/ ni openapi.json.
La cola es GET /decisions?decision=ESCALAR por un proxy same-origin.
Aprobar y rechazar son POST /decisions/{id}/approve y /reject con {author, reason}.
Un motivo vacío no se envía. Un 422 no cuenta como evento registrado.
Tras el éxito, decision sigue ESCALAR y aparece un HumanEvent.
No construyas /decisiones, el detalle, métricas ni la subida. G3 y G4 siguen abiertos.
Al terminar: recorrido en navegador, tsc, commit y push (sección 11.8).
```
