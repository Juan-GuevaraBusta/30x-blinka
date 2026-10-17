# Spec T4.3 — UI `/reglas`

Dueño: **Frontend**. Skill de dominio: `frontend-design` (TOTAL). Rendimiento al escribir la página: `vercel-react-best-practices` (PARCIAL). No usar `ui-ux-pro-max` (dos criterios visuales). No usar `supabase`, `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **implemente** T4.3. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D032**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (I2 el LLM no decide; I6 solo datos sintéticos; I8 cero dinero)
- `docs/04_RULES_AND_DECISION_SPEC.md` §2 (esquema editable) y §5 (el registro no se reescribe)
- `docs/07_OBSERVABILITY_LANGSMITH.md` último punto: un cambio de reglas no reescribe decisiones ya tomadas
- `docs/T4_1_SPEC.md` (`GET /rules`, `PUT /rules`, 422 no persiste)
- `docs/SKILLS_MAP.md` fila T4.3
- `backend/app/models/rules_config.py` (forma de `RulesConfig`; no editarlo)
- `backend/openapi.json` path `/rules`
- `data/rules.json` (documento de partida; no editarlo)
- `frontend/README.md`

Declarar la skill en una línea, leer `frontend-design` y seguir su proceso: plan visual corto (color, tipo, layout, principio) y revisión contra el brief **antes** de escribir componentes. Luego leer `vercel-react-best-practices` solo para no meter waterfalls ni renders de más en esta página.

No editar `backend/`, `data/`, `eval/`, `docs/04`, `pyproject.toml` ni `backend/openapi.json`. Si el recorrido exige CORS, un entrypoint o una columna nueva, **parar**: eso es T4.9 o un cambio de esquema.

G3 sigue PENDIENTE. Esta tarea es la pantalla mínima de reglas (`docs/05`: no se corta). No anticipar T4.4–T4.8 ni pulir otras rutas.

## 1. Qué es T4.3

Una sola pantalla, `/reglas`, en español. Carga el `RulesConfig` vigente, deja editarlo entero y lo guarda con `PUT /rules`. Una regla mal formada no se guarda. La pantalla muestra una versión de **contenido** del documento guardado. Las facturas ya decididas no se tocan.

| Pieza | Qué hace |
|---|---|
| App | Next.js (App Router) + TypeScript estricto, dentro de `frontend/` |
| Datos | `GET /rules` al abrir. `PUT /rules` solo con un cuerpo que es el documento completo |
| Validación | El cliente rechaza un borrador inválido y no llama al API. Un 422 del servidor tampoco cuenta como guardado |
| Versión | Etiqueta de 12 hex del SHA-256 del JSON canónico del último documento guardado. No es un campo del JSON |
| Error | El borrador inválido sigue en el formulario. La etiqueta de versión y el documento guardado no cambian |

El `PUT` sustituye el documento. Omitir un campo borra ese valor en el servidor o devuelve 422. El formulario muestra todos los campos de `RulesConfig` y reenvía los que el usuario no tocó.

## 2. Fuera de alcance

- Rutas `/decisiones`, `/decisiones/[id]`, `/aprobaciones`, `/metricas` y subida de factura (T4.4–T4.8). Un enlace o un cascarón vacío no cuenta como esas pantallas.
- Auth, API keys de cliente, JWT.
- CORS, `render.yaml`, Vercel, Postgres, bind `0.0.0.0:$PORT` (T4.9).
- Historial de reglas, botón de restaurar, Alembic. Hay un solo documento vigente (T4.2).
- Añadir `rules_version` u otro campo al JSON. `extra=forbid` lo rechaza con 422.
- Cambiar `versions.rules_version` de un `DecisionRecord`. El grafo sigue estampando el suyo (`RULES_VERSION` en `folder_batch.py`). Esta pantalla no lo incrementa.
- Reescribir `data/rules.json`. El `PUT` vive en el almacén del proceso API (memoria o SQL, según cómo se arranque el recorrido).
- Editar `backend/`, modelos, OpenAPI o el motor.
- LangChain, Langfuse, RAG, Supabase.
- Cerrar G3, G4 o G5.
- Mover dinero. Guardar un umbral no paga facturas (I8).

## 3. Archivos

Crear en `frontend/` (la app aún no existe; solo hay `README.md`):

- App Next.js, App Router, TypeScript estricto. `create-next-app` vale. Sin `src/` si el default del CLI ya usa `app/`.
- `frontend/.env.example` con `API_URL=http://127.0.0.1:8000`. Sin clave, sin host real.
- `frontend/.env.local` queda fuera de git (el `.gitignore` de Next lo cubre).
- Página `app/reglas/page.tsx` (o equivalente) y los componentes de esa pantalla.
- Funciones puras del formulario y de la etiqueta de versión, más una prueba de esas funciones (el runner lo elige la sesión; no hace falta Playwright en CI).
- Proxy same-origin hacia el API (rewrite de Next o route handler). El navegador no llama a otro origen. Así no hace falta CORS en el backend.

Modificar:

- `frontend/README.md`: esta pantalla ya se puede construir con el OpenAPI de T4.1. La frase que prohíbe toda UI hasta G3 queda limitada al resto de rutas.
- Al cerrar la implementación: `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`.

No tocar `backend/`, `data/`, `openapi.json`.

## 4. Invariantes

- I2. La pantalla no llama a un LLM ni a `decide()`. Solo lee y escribe `RulesConfig`.
- I6. Textos de ejemplo = los de `data/rules.json` (Acme Demo Inc., `*.demo.test`). No pegar datos reales ni claves. `API_URL` no se loguea si algún día trajera secreto.
- I8. Guardar reglas no dispara un pago.
- El 422 no persiste. Tras un rechazo, un `GET /rules` nuevo coincide con el último 200.

JSON de más en el borrador: el cliente lo rechaza y no lo envía. Si el servidor responde 422 igual, la etiqueta de versión no cambia.

## 5. Contrato HTTP que la UI consume

Sin prefijo en el API (`/rules`). El navegador pega a la misma origen, y el servidor Next reenvía a `${API_URL}/rules`.

| Llamada | Éxito | Fracaso |
|---|---|---|
| `GET /rules` | 200, cuerpo = `RulesConfig` | Mostrar el fallo en español. No inventar un documento |
| `PUT /rules` | 200, cuerpo = documento guardado | 422: no actualizar la versión ni el “último guardado” |

El cuerpo del `PUT` es el documento completo, claves y tipos de `RulesConfig`:

- `company.name`, `company.base_currency` (texto no vacío)
- `limits.per_payment` > 0
- `limits.per_period.type` = `calendar_month` (único valor)
- `limits.per_period.amount` > 0
- `human_approval_threshold` > 0
- `allowed_beneficiaries`: lista no vacía, entradas sin blanco
- `department_budgets`: montos > 0, claves sin blanco
- `approvers`: incluye `default`; nombres y correos sin blanco
- `manual_blocks`: lista, entradas sin blanco
- `on_fail`: exactamente R01–R13, cada una `FRENAR` o `ESCALAR`
- `jev_thresholds`: J1, J2, J3, J4, J6, J7 en (0, 1]. Sin J5

Campo desconocido, tipo mal o número que no cumple → no se guarda.

## 6. Versionado

`versionLabel(document) = primeros 12 caracteres hexadecimales de SHA-256 del JSON canónico.`

JSON canónico: UTF-8, claves ordenadas en todos los objetos, sin espacios de más. El mismo documento produce la misma etiqueta tras recargar. Dos documentos distintos producen etiquetas distintas.

- Al cargar, la etiqueta es la del `GET`.
- Solo un `PUT` 200 la sustituye, con el cuerpo de esa respuesta.
- Un borrador inválido o un 422 no la mueve.
- No se envía en el `PUT`. No se guarda en `localStorage` como fuente de verdad.
- Junto a la etiqueta, una frase fija: las facturas ya decididas conservan la versión con la que se registraron. Esta pantalla solo sustituye las reglas vigentes.

No hay lista de versiones anteriores ni botón de deshacer contra el servidor.

## 7. Recorrido

Textos de la interfaz en español. El botón de guardar dice qué hace (guardar las reglas vigentes).

1. Abrir `/reglas`. Se ven los valores del `GET` (umbral 3000 si el proceso arrancó con `data/rules.json`) y su etiqueta.
2. Cambiar `human_approval_threshold` a 2500. Guardar. La respuesta es 200. La etiqueta cambia. Recargar: el umbral sigue en 2500 y la etiqueta es la misma.
3. Poner `limits.per_payment` en `-1` (o vacío). Guardar. El cliente muestra el error y no manda el `PUT`, o el servidor responde 422. Recargar (o un `GET`): `per_payment` sigue en 5000 y el umbral sigue en 2500. La etiqueta no cambió respecto al paso 2.
4. Quitar `approvers.default` y guardar: mismo resultado, documento intacto.
5. Un beneficiario en blanco o un umbral J5 no se envían.

El formulario no pierde el resto de campos al editar uno. Listas (beneficiarios, bloqueos) se pueden sumar y quitar filas.

## 8. Arranque del recorrido

El backend no tiene entrypoint (T4.9). Para el navegador, la sesión levanta el API **sin commitear** un módulo nuevo y **sin** añadir `uvicorn` a `pyproject.toml`. Si `uvicorn` no está en el venv, se instala solo en local para el recorrido.

`PYTHONPATH=backend`, almacén en memoria, reglas desde `data/rules.json`, reloj y límite holgados. El procesador de facturas no se usa en esta tarea. Host `127.0.0.1`, puerto 8000, alineado a `API_URL`.

El navegador habla con Next. Next reenvía al API. No hace falta cabecera CORS.

Ese proceso muere al cerrar la sesión. No afirmar que el umbral 2500 sobrevivió a un reinicio del backend: con `MemoryStore` no sobrevive. Probar `SqlStore` aquí no es obligatorio.

## 9. Diseño

Seguir `frontend-design`. La pantalla es un puesto de control de pagos de una empresa ficticia, no un landing. Una sola decisión visual fuerte; el resto, quieto. Copiar en español, voz activa, el error dice qué corregir.

No fijar paleta en este spec: la fija el plan de la sesión, después de leer la skill. Accesible por teclado, foco visible, y usable en un ancho de móvil.

`vercel-react-best-practices`: un fetch al entrar, sin cadena de requests. No hace falta memoizar esta página por adelantado.

## 10. Qué no afirmar

- Que las otras pantallas existen.
- Que un deploy público ya sirve `/reglas`.
- Que Postgres o Render guardan el `PUT`.
- Que `versions.rules_version` de una factura sube al guardar.
- Que se puede volver a una versión anterior.
- Que hay auth.
- Que G3 o G4 están cerrados.

## 11. Criterios de aceptación

1. Recorrido en navegador (no basta una captura): guardar umbral 2500, recargar y verlo; rechazar `per_payment` inválido y comprobar que el documento guardado no cambió. Anotar la herramienta (Playwright u otra) y el resultado en el tablero.
2. `npx tsc --noEmit` en `frontend/` — ok. El lint del proyecto Next — ok.
3. La prueba de `versionLabel` y del validador del borrador — verde. Mismo documento → misma etiqueta; documento distinto → otra; `per_payment` ≤ 0 y `approvers` sin `default` → inválido.
4. `git status` sin `.env`, sin `.env.local`, sin `node_modules`, sin secretos.
5. Diff de `backend/` y de `backend/openapi.json` vacío.
6. Tablero: T4.3 HECHA con la nota del recorrido. T4.4–T4.9, G3 y G4 siguen PENDIENTE.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit: `T4.3: rules screen with validation and content version`.

## 12. Subtareas

- T4.3.1 App Next.js en `frontend/`, TypeScript estricto, `API_URL` en `.env.example`, proxy same-origin. Sin otras pantallas.
- T4.3.2 Funciones puras: documento completo, validación, `versionLabel`. Prueba roja y luego verde.
- T4.3.3 Página `/reglas` según el plan de `frontend-design`. GET al entrar. PUT solo si el borrador valida.
- T4.3.4 Recorrido del §7 en el navegador. Tablero. Commit y push.

## 13. Mensaje para la sesión que implementa

```text
Implementa T4.3 según docs/T4_3_SPEC.md.
Skill: frontend-design (léela y escribe el plan visual antes del código).
Al escribir la página, vercel-react-best-practices.
No uses ui-ux-pro-max, supabase, langfuse ni langchain-rag.
No edites backend/, data/ ni openapi.json.
La pantalla habla con GET/PUT /rules por un proxy same-origin.
Un borrador inválido no se guarda. La etiqueta de versión solo cambia con un PUT 200.
No construyas las otras rutas. G3 y G4 siguen abiertos.
Al terminar: recorrido en navegador, tsc, commit y push (sección 11.8).
```
