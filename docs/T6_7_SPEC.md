# Spec T6.7 — Navegación, panel de inicio y decisiones con enlace al detalle

Dueño: **Frontend**. Carril: B. Skill de dominio: `frontend-design` (`docs/SKILLS_MAP.md`).

Depende de: T4.3–T4.7 (pantallas ya entregadas: `/reglas`, `/decisiones`, `/decisiones/[id]`, `/aprobaciones`, `/metricas`, `/subir`) y T5.9 (D055, inyección de `X-Admin-Key` server-side en `approve`/`reject`/`PUT /rules`, que este spec no toca). No bloquea ninguna tarea posterior conocida.

Estado: contrato para la sesión que **implementa** T6.7. Este archivo no corre el comando ni cierra la tarea.

Decisión que fija este contrato: **D057** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio `frontend-design`: leerla antes de tocar `layout.tsx` o cualquier pantalla nueva.

Lecturas:

- `AGENTS.md` §3 (idioma: UI y explicaciones en español; código e identificadores en inglés) y §2 invariantes I2/I8 (el agente nunca paga; "PAGAR" es un registro, no un movimiento de dinero)
- `frontend/app/layout.tsx`, `frontend/app/page.tsx` (hoy redirige a `/reglas`)
- `frontend/app/decisiones/DecisionsScreen.tsx`, `frontend/lib/decisions-list.ts`, `frontend/app/decisiones/[id]/DecisionDetailScreen.tsx`, `frontend/lib/decision-present.ts`, `frontend/lib/decision-types.ts`
- `frontend/app/api/**/route.ts` (7 proxies: `rules`, `decisions`, `decisions/[id]`, `decisions/[id]/approve`, `decisions/[id]/reject`, `invoices`, `metrics`) y los tests existentes `frontend/app/api/rules/route.test.ts`, `frontend/app/api/decisions/[id]/approve/route.test.ts`, `frontend/app/api/decisions/[id]/reject/route.test.ts`
- `frontend/app/globals.css` y `frontend/tailwind.config.ts` (tokens `--canvas/--surface/--ink/--ink-muted/--line/--accent/--danger/--success`; no se agregan tokens nuevos)
- `backend/app/models/domain.py` línea con `SEVERITY: dict[str, int] = {"PAGAR": 0, "ESCALAR": 1, "FRENAR": 2}` (fija el significado de la severidad guardada: 0 = OK/PAGAR, 1 = Advertencia/ESCALAR, 2 = Bloqueo/FRENAR)

## 1. Qué es T6.7

Hoy el frontend no tiene navegación global: cada pantalla es una isla y `/` solo redirige a `/reglas`. T6.7 agrega (a) una barra de navegación global en `app/layout.tsx` con enlace a las seis pantallas existentes, (b) un panel de inicio en `/` que explica el producto en lenguaje llano y muestra conteos de decisiones con enlace a la lista filtrada, (c) en `/decisiones`, orden de pestañas y filtro por defecto centrados en lo pendiente, con filas que enlazan a la ficha de detalle, (d) en la ficha de detalle, la severidad mostrada también en palabras, y (e) que los 7 proxies de API respondan con un error controlado (502 `upstream_unreachable`) en vez de propagar una excepción no capturada cuando el backend no responde.

## 2. Alcance

1. **Navegación global** (`frontend/app/layout.tsx` + `frontend/lib/nav.ts` + `frontend/app/GlobalNav.tsx` nuevos): marca "Agente de pagos · Hackathon Blinka" en texto plano (sin logo ni imitación del diseño de la app de Blinka — eso queda fuera del alcance del challenge) y enlaces Inicio, Reglas, Decisiones, Aprobaciones, Métricas, Subir factura. Landmark `<nav aria-label="Principal">`, `aria-current="page"` en el enlace activo (comparación de ruta en `lib/nav.ts`, testeable), `flex-wrap` para que no rompa en móvil.
2. **Panel de inicio** (`frontend/app/page.tsx` reemplaza el `redirect`, nuevo `frontend/app/OverviewScreen.tsx` + `frontend/lib/overview.ts`): un párrafo en lenguaje llano (el agente decide PAGAR/FRENAR/ESCALAR según las reglas de la empresa; nunca paga fuera de esas reglas; toda decisión queda explicada), tres tarjetas de conteo (Pagadas, Frenadas, Pendientes de aprobación) obtenidas con `fetch` en cliente a `GET /api/decisions?decision=…` (mismo patrón que `DecisionsScreen`, con estados cargando/error/vacío), cada tarjeta enlaza a `/decisiones` filtrada, y una franja "Cómo funciona" de 4 pasos.
3. **`frontend/lib/decisions-list.ts`**: `DECISION_LIST_FILTERS` pasa a `["pendientes", "frenadas", "pagadas"]` y `DEFAULT_DECISION_LIST_FILTER` a `"pendientes"`; nueva función pura `parseInitialFilter` que lee un parámetro de búsqueda (`estado`) y cae al default si no es uno de los tres valores válidos. `frontend/app/decisiones/page.tsx` lee `searchParams` y pasa `initialFilter` a `DecisionsScreen`. `DecisionsScreen` acepta esa prop, muestra el conteo por pestaña (una petición adicional por pestaña al montar; aceptable por ser listas sintéticas pequeñas) y cada fila/tarjeta enlaza con `next/link` a `/decisiones/[id]` usando el `id` del registro (ya viene en la respuesta de `GET /decisions`, aunque antes no se validaba en el frontend).
4. **`frontend/app/decisiones/[id]/DecisionDetailScreen.tsx`**: la severidad se muestra como `{entero} · {palabra}` usando una función pura nueva en `frontend/lib/decision-present.ts` (`severityLabel`) con la tabla confirmada en `backend/app/models/domain.py`: 0 → "OK", 1 → "Advertencia (Escalar)", 2 → "Bloqueo (Frenar)".
5. **Los 7 proxies** (`frontend/app/api/rules/route.ts`, `.../decisions/route.ts`, `.../decisions/[id]/route.ts`, `.../decisions/[id]/approve/route.ts`, `.../decisions/[id]/reject/route.ts`, `.../invoices/route.ts`, `.../metrics/route.ts`): envolver la llamada `fetch` al upstream en `try/catch`; si lanza, responder `NextResponse.json({ detail: "upstream_unreachable" }, { status: 502 })` (helper nuevo `frontend/lib/upstream-error.ts`). No cambia la inyección de `X-Admin-Key` en `rules` PUT, `approve` y `reject` (T5.9, D055). Pruebas nuevas para los 4 proxies sin test (`decisions` GET, `decisions/[id]` GET, `invoices` POST, `metrics` GET) siguiendo el patrón de `frontend/app/api/rules/route.test.ts` (mock de `fetch` con `vi.stubGlobal`, un caso feliz de paso de parámetros/headers y un caso de red caída → 502 `upstream_unreachable`).

## 3. Fuera de alcance

- Tocar `docs/TASK_BOARD.md`, `docs/DECISIONS_LOG.md`, `docs/AI_USAGE_LOG.md`, `backend/`, `data/` o `.github/` (otro agente trabaja CI ahí).
- Commit, push o cualquier registro de cierre de tarea: esta sesión implementa; no cierra el tablero.
- Rediseñar el look & feel existente, cambiar los tokens de `globals.css`/`tailwind.config.ts`, o usar el logo o estilo visual de Blinka.
- Cambiar la lógica de `AprobacionesScreen.tsx`, `ReglasScreen.tsx`, `SubirScreen.tsx`, `MetricasScreen.tsx` más allá de lo que ya haga el proxy compartido.
- Añadir autenticación, sincronizar el filtro de `/decisiones` con el historial del navegador más allá de un parámetro `estado` en la URL, o cachear conteos entre pantallas.

## 4. Criterios de aceptación

1. `npm run lint` y `npx tsc --noEmit` (en `frontend/`) sin errores nuevos.
2. `npm test` (en `frontend/`) ≥ 59 pruebas (baseline) + las nuevas de este spec, 0 failed.
3. `npm run build` (en `frontend/`) compila sin error.
4. `GlobalNav`: landmark de navegación, `aria-current="page"` en el enlace activo, visible en móvil sin desbordar horizontalmente la página.
5. `/`: ya no redirige; muestra el párrafo explicativo, las tres tarjetas de conteo (con estado de carga/error/vacío) y la franja de 4 pasos; cada tarjeta enlaza a `/decisiones` ya filtrada.
6. `/decisiones`: pestañas en el orden Pendientes, Frenadas, Pagadas; filtro inicial Pendientes salvo que la URL traiga `?estado=` válido; filas/tarjetas navegan a `/decisiones/[id]`.
7. `/decisiones/[id]`: la severidad guardada se lee en palabras además del entero, coherente con `SEVERITY` del backend.
8. Los 7 proxies devuelven `502 {"detail":"upstream_unreachable"}` cuando el `fetch` al backend lanza (upstream caído/DNS), sin romper los tests ya existentes de `rules`, `approve` y `reject`.
9. Diff limpio: solo archivos bajo `frontend/` y este spec. Sin cambios en `backend/`, `data/`, `.github/` ni en los registros de seguimiento.

## 5. Commit

```text
T6.7: add navigation, overview dashboard and clickable decisions
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T6.7 según docs/T6_7_SPEC.md. Decisión D057.
Agrega navegación global en app/layout.tsx (marca de texto, sin logo de
Blinka), un panel de inicio en app/page.tsx con conteos enlazados a
/decisiones filtrada, reordena las pestañas de /decisiones a
Pendientes/Frenadas/Pagadas con Pendientes por defecto y filas que
enlazan a /decisiones/[id], muestra la severidad guardada en palabras en
la ficha de detalle (0 OK, 1 Advertencia/Escalar, 2 Bloqueo/Frenar, según
SEVERITY en backend/app/models/domain.py), y envuelve los 7 proxies de
app/api/**/route.ts en try/catch devolviendo 502
{"detail":"upstream_unreachable"} cuando el backend no responde, con
pruebas nuevas para los 4 proxies sin test. No toques backend/, data/,
.github/ ni los registros de seguimiento; no hagas commit ni push.
Al terminar: npm run lint; npx tsc --noEmit; npm test; npm run build.
```
