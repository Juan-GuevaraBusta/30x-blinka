# Spec T4.4 — UI `/decisiones`

Dueño: **Frontend**. Skill de dominio: `frontend-design` (TOTAL). Rendimiento al escribir la página: `vercel-react-best-practices` (PARCIAL). No usar `ui-ux-pro-max` (dos criterios visuales). No usar `supabase`, `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **implemente** T4.4. Este archivo no cierra la tarea. T4.4 sigue PENDIENTE.

Decisión que fija este contrato: **D033**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (I2 el LLM no decide; I6 solo datos sintéticos; I8 cero dinero)
- `docs/05_PHASES_AND_ROADMAP.md` fila T4.4 y G4
- `docs/TASK_BOARD.md` fila T4.4
- `docs/T4_3_SPEC.md` (formato; esta pantalla no reabre `/reglas`)
- `docs/T4_1_SPEC.md` §1 y §5.2 (`GET /decisions`)
- `docs/SKILLS_MAP.md` fila T4.4
- `backend/openapi.json` path `/decisions` (no editarlo)
- `backend/app/api/app.py` `list_decisions` (no editarlo)
- `backend/app/models/domain.py` `DecisionRecord` (no editarlo)
- `backend/tests/api/support.py` `_EXAMPLE` / `make_record` (forma sintética del recorrido; no editarlo)
- `frontend/README.md`, `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/app/api/rules/route.ts`

Declarar la skill en una línea y leer `frontend-design`. El plan visual de esta sesión es corto y de **continuidad**: el sistema de T4.3 ya está en código (lienzo, tipo, acento). No rediseñar la app. Luego leer `vercel-react-best-practices` solo para no meter waterfalls ni renders de más en esta página.

No editar `backend/`, `data/`, `eval/`, `docs/04`, `pyproject.toml`, `backend/openapi.json` ni `backend/app/models/`. No editar `frontend/app/reglas/**` ni `frontend/app/page.tsx`. Si el recorrido exige CORS, un entrypoint commiteado o un endpoint nuevo, **parar**: CORS y el deploy son T4.9; el listado ya existe.

G3 y G4 siguen PENDIENTE. Esta tarea es la tabla y los tres filtros. No anticipar T4.5–T4.9.

## 1. Qué es T4.4

Una sola pantalla nueva, `/decisiones`, en español. Muestra una tabla de registros ya guardados y deja filtrar con tres controles. El motivo de cada fila es una línea: el campo `summary`.

| Pieza | Qué hace |
|---|---|
| App | La Next.js de T4.3, App Router, TypeScript estricto, dentro de `frontend/` |
| Datos | `GET /decisions?decision=` al elegir filtro. Un solo request por filtro activo |
| Filtros | Pagadas, Frenadas, Pendientes. El API no usa esas palabras |
| Motivo | Texto de `summary`, tal cual. No se reescribe ni se resume |
| Vacío | Un 200 con lista vacía es un estado vacío, no un error |

Mapeo (el query del API es `PAGAR` \| `ESCALAR` \| `FRENAR`):

| Control | Query `decision` | Etiqueta de la fila |
|---|---|---|
| Pagadas | `PAGAR` | Pagada |
| Frenadas | `FRENAR` | Frenada |
| Pendientes | `ESCALAR` | Pendiente |

Pendientes es la cola humana (`ESCALAR`). No es un cuarto valor de `decision`.

Al abrir, el filtro activo es **Pagadas** y la primera llamada es `GET /decisions?decision=PAGAR`. El orden de los controles es Pagadas, Frenadas, Pendientes. El orden de las filas es el del array del API (orden de inserción del almacén). La UI no reordena.

Columnas: factura (`invoice_id`), estado (etiqueta de la fila), motivo (`summary`). El resto del `DecisionRecord` no se pinta. Las filas no son enlaces.

## 2. Fuera de alcance

- Ruta `/decisiones/[id]` (T4.5). No crear `app/decisiones/[id]`. No exigir un enlace: el destino aún no existe y un 404 no es esta tarea.
- `/aprobaciones` (T4.6), `/metricas` (T4.7), subida de factura (T4.8), deploy (T4.9).
- `POST /invoices`, `POST /decisions/{id}/approve`, `POST /decisions/{id}/reject`, `GET /metrics`, `GET /decisions/{id}`.
- Auth, API keys de cliente, JWT.
- CORS, `render.yaml`, Vercel, Postgres, bind `0.0.0.0:$PORT` (T4.9).
- Llamar a `decide()`, al grafo o a un LLM para rellenar o acortar la tabla (I2).
- Reescribir `summary`, `decision` o `severity`.
- Un cuarto filtro «Todas» o un `GET /decisions` sin query como fuente de la tabla.
- Editar `/reglas`, el redirect de `/` hacia `/reglas`, `backend/`, modelos, OpenAPI o `data/`.
- Sembrar facturas en SQL. El seed de T4.2 solo inserta reglas.
- LangChain, Langfuse, RAG, Supabase.
- Cerrar G3, G4 o G5.
- Mover dinero. Ver «Pagadas» no paga (I8).

## 3. Archivos

Crear en `frontend/`:

- `app/decisiones/page.tsx` y el componente de esa pantalla.
- `app/api/decisions/route.ts`: proxy `GET` same-origin. El navegador llama a `/api/decisions?decision=PAGAR|ESCALAR|FRENAR`. Next reenvía a `${API_URL}/decisions` con ese mismo query. `cache: "no-store"`. Mismo patrón que `app/api/rules/route.ts`. Solo `GET`.
- Funciones puras del mapeo filtro → query, de la etiqueta de fila y del motivo (`summary` sin tocarlo), más una prueba con el runner que ya usa el frontend (vitest). No hace falta Playwright en CI.

Modificar:

- `frontend/README.md`: `/decisiones` ya se puede abrir. El resto de rutas T4.x sigue fuera. El arranque del API apunta también a este spec §8.

`frontend/.env.example` ya tiene `API_URL=http://127.0.0.1:8000`. No añadir claves ni hosts reales. `.env.local` sigue fuera de git.

Al cerrar la implementación (no este spec): `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`.

No tocar `backend/`, `data/`, `openapi.json`, `app/reglas/**`, `app/page.tsx`.

## 4. Invariantes

- I2. La pantalla no llama a un LLM ni a `decide()`. Solo lee el listado. El proceso local del §8 inserta registros ya armados; no procesa facturas.
- I6. Ejemplos = los de `backend/tests/api/support.py` (Acme Demo Inc., Globex LLC, `cfo@demo.test`, `INV-PAY` / `INV-ESC` / `INV-STOP`). No pegar datos reales ni claves. `API_URL` no se loguea si algún día trajera secreto.
- I8. Listar `PAGAR` no dispara un pago. «Pagada» es la etiqueta del registro.

Un 422 o un 429 no se disfraza de lista vacía ni de filas inventadas.

## 5. Contrato HTTP que la UI consume

Sin prefijo en el API (`/decisions`, no `/api/decisions` en el backend). El navegador pega a la misma origen y el servidor Next reenvía.

`GET /decisions` (OpenAPI `list_decisions_decisions_get`):

| Pieza | Contrato |
|---|---|
| Query | `decision`, opcional. Enum `PAGAR` \| `ESCALAR` \| `FRENAR`, o ausente |
| 200 | Array de `DecisionRecord`. Puede ir vacío. Con query, solo ítems con ese `decision` |
| 422 | Query distinto de esos tres (`HTTPValidationError`) |
| Otro fallo | P. ej. 429 `{"detail":"rate_limited"}` si el límite del proceso se agota |

La página **siempre** manda uno de los tres valores. No manda `Pagadas` ni `Pendientes` como query.

Campos que pinta, del `DecisionRecord` (el JSON trae más; se ignoran):

- `invoice_id` (string, no vacío)
- `decision` (`PAGAR` \| `ESCALAR` \| `FRENAR`)
- `summary` (string, no vacío): el motivo

`id` del registro no es `invoice_id`. Esta pantalla no llama a `GET /decisions/{id}`.

El proxy reenvía el status. Un cuerpo que no sea un array en un 200 se muestra como fallo, sin filas inventadas.

## 6. Filtros y vacío

Cambiar de filtro sustituye la tabla. No se mezclan filas del filtro anterior. Mientras llega la respuesta, un texto de carga en español. Si el usuario cambia otra vez antes de la respuesta, se ignora la respuesta vieja.

| Situación | Qué se ve |
|---|---|
| 200 `[]` | Estado vacío de ese filtro, no un error. Pagadas: «No hay facturas pagadas.» Frenadas: «No hay facturas frenadas.» Pendientes: «No hay facturas pendientes de revisión.» |
| 200 con filas | Solo esas filas. Motivo = `summary` en una sola línea visual |
| Red caída, 422, 429 u otro status | El fallo en español, con el código HTTP. Cero filas inventadas |
| `summary` largo | Elipsis si no cabe. El string completo sigue en el DOM (`title` o el texto del nodo). No se corta con un LLM ni se cambia el texto |

La línea de motivo no antepone la etiqueta del filtro, ni `next_step`, ni los chequeos.

## 7. Recorrido

Textos de la interfaz en español. Se abre `http://localhost:3000/decisiones` directo. `/` sigue yendo a `/reglas`.

El API del recorrido lleva tres registros sintéticos (§8), los de `test_list_decisions_filters_escalar`: `dec_pay` / `INV-PAY` / `PAGAR`, `dec_esc` / `INV-ESC` / `ESCALAR`, `dec_stop` / `INV-STOP` / `FRENAR`. El builder copia el mismo `summary` en los tres: «Escalada: USD 4.200 llega al umbral de aprobación humana.» La UI lo muestra igual en los tres filtros. Lo que distingue el filtro es la factura que queda.

1. Abrir `/decisiones`. Filtro Pagadas activo. Una fila: factura `INV-PAY`, estado Pagada, motivo exactamente ese `summary`, en una línea.
2. Frenadas. Desaparece `INV-PAY`. Queda `INV-STOP`, estado Frenada, el mismo motivo.
3. Pendientes. Queda `INV-ESC`, estado Pendiente, el mismo motivo. No aparece un cuarto estado.
4. Volver a Pagadas. Otra vez solo `INV-PAY`.

No hace falta vaciar el almacén en el navegador. El estado vacío queda cubierto por la prueba de la función de copia y por un 200 `[]` si el proceso se levanta sin registros: la pantalla no debe mostrar un error.

Comprobar en el recorrido que el navegador pide la misma origen (`/api/decisions?decision=…`) y que no hay request a `:8000` desde la página.

## 8. Arranque del recorrido

El backend no tiene entrypoint (T4.9). Misma vía que T4.3 §8: la sesión levanta el API **sin commitear** un módulo nuevo y **sin** añadir `uvicorn` a `pyproject.toml`. Si `uvicorn` no está en el venv, se instala solo en local.

`PYTHONPATH=backend`, almacén en memoria, reglas desde `data/rules.json`, reloj consciente de zona, límite holgado. Host `127.0.0.1`, puerto 8000, alineado a `API_URL`.

Antes de escuchar, ese proceso local inserta los tres `DecisionRecord` del §7 (`add_decision`), con `severity` 0 / 1 / 2 según `PAGAR` / `ESCALAR` / `FRENAR`. No llama al procesador de facturas, ni a `decide()`, ni a la red. No usa `POST /invoices`.

El navegador habla con Next. Next reenvía al API. No hace falta cabecera CORS.

Ese proceso muere al cerrar la sesión. No afirmar que las tres facturas sobrevivieron a un reinicio: con `MemoryStore` no sobreviven. Probar `SqlStore` aquí no es obligatorio.

## 9. Diseño

Continuar lo ya enviado en T4.3. No elegir otra paleta ni otra tipografía.

Ya en código: lienzo `#e8ecf1`, superficie blanca, tinta `#152033`, línea `#c5cdd8`, acento cobre `#b45309`, Source Serif 4 para el título, DM Sans para el resto. Misma envoltura que `/reglas`: `max-w-4xl`, `px-4 py-10`, título en `font-display`. Foco visible con el anillo cobre de los campos de reglas (`focus:ring-2 focus:ring-accent/30`).

Una decisión visual de esta pantalla: el filtro activo lleva el cobre (borde o subrayado); los inactivos quedan en tinta apagada sobre superficie. La etiqueta de fila reutiliza tokens que ya existen: Pagada en `success`, Frenada en `danger`, Pendiente en `accent`. Sin colores nuevos.

Los tres filtros son un grupo con nombre accesible («Filtrar por estado»), teclado y foco visible (radios o botones con `aria-pressed`). En ancho de móvil, cada registro es un bloque (factura, estado, motivo) para que el motivo no quede fuera de pantalla. A partir de `sm`, la misma información va en tabla.

Copia en voz activa. Una frase fija junto al título: ver la lista no mueve dinero.

`vercel-react-best-practices`: un fetch por filtro activo, sin precargar los otros dos ni el detalle. No hace falta memoizar esta página por adelantado.

## 10. Qué no afirmar

- Que `/decisiones/[id]`, aprobaciones, métricas o la subida existen.
- Que un deploy público ya sirve `/decisiones`.
- Que Postgres o Render guardan la lista.
- Que «Pagada» es un pago ejecutado.
- Que Pendientes es un valor distinto de `ESCALAR`.
- Que hay auth.
- Que G3 o G4 están cerrados.
- Que las facturas del recorrido siguen ahí tras reiniciar el API.

## 11. Criterios de aceptación

1. Recorrido en navegador (no basta una captura): los tres filtros del §7, con el motivo de una línea igual al `summary` del API y una sola factura por filtro. Anotar la herramienta (Playwright u otra) y el resultado en el tablero.
2. `npx tsc --noEmit` en `frontend/` — ok. El lint del proyecto Next — ok. La prueba del frontend — ok.
3. La prueba del mapeo — verde. Pagadas → `PAGAR`, Frenadas → `FRENAR`, Pendientes → `ESCALAR`. Etiquetas de fila Pagada / Frenada / Pendiente. El motivo devuelto es el `summary` de entrada, carácter a carácter. Las tres copias de lista vacía son las del §6.
4. `git status` sin `.env`, sin `.env.local`, sin `node_modules`, sin secretos, sin el lanzador local del §8.
5. Diff de `backend/`, de `backend/openapi.json` y de `frontend/app/reglas/**` vacío.
6. Tablero: T4.4 HECHA con la nota del recorrido. T4.5–T4.9, G3 y G4 siguen PENDIENTE. T4.3 sigue HECHA.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit: `T4.4: decisions list with pay hold and pending filters`.

## 12. Subtareas

- T4.4.1 Proxy `GET /api/decisions` hacia `${API_URL}/decisions?decision=`. Sin otras pantallas.
- T4.4.2 Funciones puras del mapeo, la etiqueta y el motivo. Prueba roja y luego verde.
- T4.4.3 Página `/decisiones` con la continuidad visual de T4.3. Un fetch por filtro. Motivo = `summary`.
- T4.4.4 Recorrido del §7 en el navegador. Tablero. Commit y push.

## 13. Mensaje para la sesión que implementa

```text
Implementa T4.4 según docs/T4_4_SPEC.md.
Skill: frontend-design (léela). El plan visual es continuidad de /reglas:
lienzo gris frío, acento cobre, Source Serif 4 y DM Sans. No rediseñes la app.
Al escribir la página, vercel-react-best-practices.
No uses ui-ux-pro-max, supabase, langfuse ni langchain-rag.
No edites backend/, data/, openapi.json, models/, app/reglas ni app/page.tsx.
La pantalla habla con GET /decisions?decision= por un proxy same-origin.
Pagadas=PAGAR, Frenadas=FRENAR, Pendientes=ESCALAR.
El motivo de una línea es summary, sin reescribirlo y sin llamar a decide() ni a un LLM.
No construyas /decisiones/[id] ni el resto de rutas. G3 y G4 siguen abiertos.
Al terminar: recorrido en navegador, tsc, commit y push (sección 11.8).
```
