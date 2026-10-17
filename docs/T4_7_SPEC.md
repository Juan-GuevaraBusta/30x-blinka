# Spec T4.7 — UI `/metricas`

Dueño: **Frontend**. Skill de dominio: `frontend-design` (TOTAL). Rendimiento al escribir la página: `vercel-react-best-practices` (PARCIAL). No usar `ui-ux-pro-max` (dos criterios visuales). No usar `supabase`, `langfuse` ni `langchain-rag` (D004).

Estado: contrato para la sesión que **implemente** T4.7. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D036**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (I6 solo datos sintéticos; I8 cero dinero; I9 `unsafe_pay > 0` bloquea el despliegue — esta pantalla solo muestra)
- `docs/05_PHASES_AND_ROADMAP.md` T4.7 y la línea de corte 2 (`/metricas` es la primera candidata a corte si hay retraso; el reporte, cuando exista, se queda en `eval/`)
- `docs/T4_1_SPEC.md` §5.5 (`GET /metrics`)
- `docs/T4_3_SPEC.md` (proxy same-origin y continuidad visual)
- `docs/SKILLS_MAP.md` fila T4.7
- `backend/openapi.json` schema `MetricsBody`
- `backend/app/api/schemas.py` (`MetricsBody`, `MetricsReading`; no editarlos)
- `backend/app/api/app.py` `GET /metrics` (no editarlo)
- `eval/` — no hay reporte en disco. `eval/run_motor.py` imprime una línea de stdout del motor; no es la fuente de esta pantalla
- `frontend/README.md`, `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/app/api/rules/route.ts`

Declarar la skill en una línea, leer `frontend-design` y seguir su proceso: plan visual corto (color, tipo, layout, principio) y revisión contra el brief **antes** de escribir componentes. Los tokens de §9 ya están fijados: el plan los reutiliza. Luego leer `vercel-react-best-practices` solo para no meter waterfalls, un segundo fetch ni una librería de datos.

No editar `backend/`, `data/`, `eval/`, `pyproject.toml` ni `backend/openapi.json`. No generar un reporte. Si el recorrido exige CORS, un entrypoint, Postgres o una columna nueva, **parar**: eso es T4.9 o un cambio de esquema.

G3 y G4 siguen PENDIENTE. Esta tarea es solo `/metricas`. No anticipar T4.4, T4.5, T4.6, T4.8 ni T4.9.

## 1. Qué es T4.7

Una sola pantalla, `/metricas`, en español. Al entrar hace **un** `GET` del último reporte que el API ya sabe leer. Muestra la autonomía y el conteo `unsafe_pay`. Si ese conteo no es 0, la pantalla lo marca como bloqueo de despliegue (I9). No dispara un deploy, no llama a Render y no escribe en `eval/`.

| Pieza | Qué hace |
|---|---|
| App | La de T4.3, ya en `frontend/` (Next.js, App Router, TypeScript estricto) |
| Datos | Un `GET /metrics` al abrir. El cuerpo es `MetricsBody` |
| Vacío | `source` `"none"`, o `unsafe_pay` null, o `autonomy_pct` null → frase en español de que no hay medición. No se pintan ceros |
| Lectura | `source` `"report"` y los dos números presentes → se muestran tal cual |
| Bloqueo | Esos números, y `unsafe_pay` distinto de 0 → marca visible de bloqueo. La pantalla no despliega |
| Cero | `unsafe_pay` es 0 → se muestra el cero. No lleva marca de bloqueo |

El HTTP 200 no es un cuerpo null. Es un objeto. Los campos `unsafe_pay` y `autonomy_pct` sí pueden ser null. Null significa «no hay reporte», no «cero pagos indebidos».

Nombres reales del schema (no traducir las claves JSON):

- `unsafe_pay`: entero, número o null
- `autonomy_pct`: entero, número o null
- `source`: `"none"` o `"report"`

`extra` está prohibido en el modelo. La UI no envía un cuerpo: el endpoint es solo GET.

## 2. Fuera de alcance

- Rutas `/decisiones`, `/decisiones/[id]`, `/aprobaciones` y subida de factura (T4.4–T4.6, T4.8). Un enlace o un cascarón vacío no cuenta como esas pantallas.
- Cambiar el redirect de `/` (sigue yendo a `/reglas`) ni el comportamiento de `/reglas`.
- Auth, API keys de cliente, JWT.
- CORS, `render.yaml`, Vercel, Postgres, bind `0.0.0.0:$PORT` (T4.9).
- Calcular autonomía o `unsafe_pay` en el cliente a partir de `GET /decisions` o de cualquier otra lista. El API es la fuente. Una cuenta local mentiría si el reporte y las decisiones divergen.
- Leer o escribir `eval/reports/`. No existe un reporte de ejemplo. No generar `eval/reports/latest.md` (eso es T5.1 / G3 / G5).
- Correr el holdout. Reajustar umbrales de JEV o de reglas (T5.2).
- Editar `backend/`, modelos, OpenAPI, el motor o `eval/run_motor.py`.
- Disparar, simular o bloquear un deploy. I9 se aplica en `eval/`; aquí solo se ve.
- LangChain, Langfuse, RAG, Supabase.
- Cerrar G3, G4 o G5.
- Mover dinero (I8).

`docs/05` puede cortar esta pantalla si el hackathon va tarde. Quien implemente este spec igual entrega solo esta pantalla, mínima, sin convertirla en un tablero de varias tarjetas.

## 3. Archivos

La app ya existe. No correr `create-next-app`.

Crear en `frontend/`:

- `app/metricas/page.tsx` (o equivalente) y los componentes de esa pantalla.
- `app/api/metrics/route.ts`: proxy GET. El navegador llama a `/api/metrics`; Next reenvía a `${API_URL}/metrics` con `cache: "no-store"`. Mismo patrón que `app/api/rules/route.ts`. Sin PUT.
- Función pura que clasifica un `MetricsBody` (vacío, cero, bloqueo, inválido) y una prueba vitest de esa función.

Modificar:

- `frontend/README.md`: queda dicha `/metricas`. El resto de rutas T4.x sigue fuera.
- Al cerrar la implementación: `docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`.

`frontend/.env.example` ya tiene `API_URL`. No añadir claves. `.env.local` sigue fuera de git.

No tocar `backend/`, `data/`, `eval/`, `pyproject.toml`, `backend/openapi.json`.

## 4. Invariantes

- I6. Números de ejemplo del recorrido opcional = los del test ya commiteado (`unsafe_pay` 2, `autonomy_pct` 15.5). No pegar datos reales ni claves. No loguear `API_URL` si algún día trajera secreto.
- I8. Ver la métrica no paga una factura.
- I9. `unsafe_pay > 0` en la evaluación bloquea el despliegue. Esta pantalla **muestra** esa condición. No llama a un pipeline, no escribe un artefacto de gate y no afirma que un deploy ocurrió.
- Un null no se convierte en 0. Un 0 que el API envió con `source: "report"` sí se muestra, y no lleva marca de bloqueo.
- Un conteo distinto de 0 (incluido un negativo, que el lector no debería emitir) lleva la marca. I9 nombra el caso `> 0`; la marca cubre cualquier valor que no sea cero para no pintarlo como pase.

## 5. Contrato HTTP que la UI consume

Sin prefijo en el API (`/metrics`). El navegador pega a la misma origen, y el servidor Next reenvía a `${API_URL}/metrics`.

| Llamada | Éxito | Fracaso |
|---|---|---|
| `GET /metrics` | 200, cuerpo = `MetricsBody` | Mostrar el fallo en español. No inventar ceros ni autonomía |

Sin reporte (el `create_app` de memoria no recibe lector):

```json
{"unsafe_pay": null, "autonomy_pct": null, "source": "none"}
```

Con lector inyectado, los números salen tal cual y `source` es `"report"`. Ejemplo ya cubierto por `backend/tests/api/test_openapi.py`:

```json
{"unsafe_pay": 2, "autonomy_pct": 15.5, "source": "report"}
```

Un 429 del límite por IP (`{"detail":"rate_limited"}`) se muestra en español. No reintentar en bucle. Un solo fetch al entrar no debería acercarse al límite por defecto (60 por minuto); el recorrido usa un límite holgado.

La pantalla no llama a `/decisions`, `/rules` ni `/invoices`.

## 6. Cómo se lee el cuerpo

Función pura. Entrada: el JSON ya parseado (o el fallo de red). No recibe decisiones.

1. Respuesta que no es 200, JSON ilegible, o un objeto sin las tres claves → estado de error. Sin números.
2. `source` es `"none"`, o `unsafe_pay` es null, o `autonomy_pct` es null → estado vacío. Sin cifras, sin marca de bloqueo.
3. `source` es `"report"` y los dos valores son números:
   - se muestran esos números, sin redondear a un entero que cambie el valor (15.5 sigue siendo 15.5);
   - `unsafe_pay` igual a 0 (también 0.0) → sin marca de bloqueo;
   - cualquier otro número → marca de bloqueo.

La autonomía es el campo `autonomy_pct`. No se calcula como `matched / total`. Esos campos no están en `MetricsBody` y la UI no los inventa.

`source: "none"` manda sobre un número que viniera al lado: se trata como vacío. El servidor de hoy no mezcla las dos cosas; la función igual no pinta un cero.

## 7. Recorrido

Textos de la interfaz en español. No hay botón de desplegar ni de recalcular.

1. Arranque del §8 **sin** lector. Abrir `/metricas`. Se lee el texto de que no hay reporte. No aparece un 0 ni un 0 % como si estuvieran medidos. Recargar: un solo fetch nuevo, el mismo vacío.
2. Opcional, si la sesión inyectó el lector del §8: la cifra fuerte es 2, la autonomía es 15.5, y se ve la marca de bloqueo. La frase deja claro que la pantalla no inicia un despliegue. Esos números son sintéticos (el test de T4.1), no un reporte de G3.
3. No hace falta un tercer caso con `unsafe_pay` 0 en el navegador. La prueba de la función pura cubre el cero sin marca. Si la sesión lo inyecta igual, el cero se ve y la marca no.

El recorrido 1 basta para aceptar la tarea. El 2 es opcional y se anota como inyección, no como reporte commiteado.

## 8. Arranque del recorrido

El backend no tiene entrypoint (T4.9). Mismo arreglo que `docs/T4_3_SPEC.md` §8: la sesión levanta el API **sin commitear** un módulo nuevo y **sin** añadir `uvicorn` a `pyproject.toml`. Si `uvicorn` no está en el venv, se instala solo en local para el recorrido.

`PYTHONPATH=backend`, `MemoryStore` con `load_rules_config` de `data/rules.json`, reloj y límite holgados, host `127.0.0.1`, puerto 8000, alineado a `API_URL`. El procesador de facturas no se usa. **No** pasar `metrics_reader` (queda `None`). Eso produce el JSON null de §5. No hace falta Postgres ni `SqlStore`.

El navegador habla con Next. Next reenvía al API. No hace falta cabecera CORS.

Opcional, en ese mismo proceso no commiteado: el argumento `metrics_reader` de `create_app` devuelve `MetricsReading(unsafe_pay=2, autonomy_pct=15.5)`. Sirve para ver la marca. No se guarda como archivo en `eval/`, no entra en el commit y desaparece al matar el proceso. No afirmar que sobrevivió a un reinicio.

## 9. Diseño

Continuidad con `/reglas`. Reutilizar lo que ya está en `frontend/app/globals.css` y `layout.tsx`. El plan de la sesión no abre otra paleta ni otra pareja de fuentes.

| Token | Valor | Uso en esta pantalla |
|---|---|---|
| Lienzo | `#e8ecf1` | Fondo |
| Tinta | `#152033` | Cifra y texto |
| Tinta suave | `#5c6778` | Autonomía y la frase secundaria |
| Acento | `#b45309` | Un solo acento, heredado de reglas |
| Peligro | `#9f1239` | La marca de bloqueo, ya definida |
| Display | Source Serif 4 | Solo la cifra `unsafe_pay` |
| Texto | DM Sans | El resto |

La cifra de `unsafe_pay` es el elemento fuerte: grande, en la serif, alineada a la izquierda del mismo ancho que `/reglas`. La autonomía va en una línea secundaria, no en una tarjeta gemela. En el vacío no hay cifra grande: una frase ocupa ese lugar, para que un 0 gigante no mienta.

La marca de bloqueo es una frase junto a esa cifra, en el color de peligro ya existente. Dice que ese conteo bloquea el despliegue y que esta pantalla solo lo muestra. No es un botón.

El aviso de `frontend-design` contra «número grande con etiqueta pequeña» no veta esta página: el brief pide esa cifra como sujeto. El plan sí evita el kit de tarjetas iguales, las cejas en mayúsculas, el lavado en degradado y una tercera familia tipográfica.

Copiar en español, voz activa, frase en caja de oración. El vacío dice que no hay reporte y que los dos valores no están medidos. El error de red dice que la lectura falló. Accesible por teclado, foco visible, usable en un ancho de móvil, y la cifra tiene nombre para el lector de pantalla («pagos indebidos»). `prefers-reduced-motion` ya está en el CSS global; no añadir una entrada animada.

`vercel-react-best-practices`: un fetch al entrar, sin cadena de requests. No añadir SWR ni otra dependencia. No hace falta memoizar esta página. No pedir `/metrics` en el servidor y otra vez en el cliente.

## 10. Qué no afirmar

- Que `unsafe_pay` del producto es 0. G2 lo midió en el motor; esta pantalla no lo hereda si el API responde null.
- Que existe `eval/reports/latest.md` o un reporte de G3.
- Que la autonomía salió de las decisiones visibles en otras pantallas.
- Que un deploy quedó bloqueado o ejecutado.
- Que Postgres o Render guardan la métrica.
- Que las otras pantallas existen.
- Que hay auth.
- Que G3 o G4 están cerrados.
- Que se corrió el holdout o se calibraron umbrales.

## 11. Criterios de aceptación

1. Recorrido en navegador (no basta una captura): `/metricas` con el API sin lector muestra el vacío en español y no inventa ceros. Anotar la herramienta (Playwright u otra) y el resultado en el tablero. Si se usó el lector opcional, la nota dice «inyección sintética 2 / 15.5» y que no hay archivo nuevo en `eval/`.
2. `npx tsc --noEmit` en `frontend/` — ok. El lint del proyecto Next — ok.
3. La prueba de la función de §6 — verde. Null o `source: "none"` → vacío; `unsafe_pay` 0 con `source: "report"` → cero sin bloqueo; 2 y 15.5 → bloqueo y autonomía 15.5; un cuerpo inválido no se lee como cero.
4. `git status` sin `.env`, sin `.env.local`, sin `node_modules`, sin secretos.
5. Diff de `backend/`, `backend/openapi.json`, `eval/` y `pyproject.toml` vacío.
6. Tablero: T4.7 HECHA con la nota del recorrido. T4.4, T4.5, T4.6, T4.8, T4.9, G3 y G4 siguen PENDIENTE. La línea de corte de `docs/05` no se borra: esta tarea se hizo; el corte sigue escrito para un retraso futuro.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit: `T4.7: metrics screen shows autonomy and unsafe pay`.

## 12. Subtareas

- T4.7.1 Proxy `GET /api/metrics` hacia `${API_URL}/metrics`. Sin otras pantallas.
- T4.7.2 Función pura de §6. Prueba roja y luego verde.
- T4.7.3 Página `/metricas` según el plan de `frontend-design` y los tokens de §9. Un fetch al entrar.
- T4.7.4 Recorrido del §7 en el navegador. Tablero. Commit y push.

## 13. Mensaje para la sesión que implementa

```text
Implementa T4.7 según docs/T4_7_SPEC.md.
Skill: frontend-design (léela y escribe el plan visual antes del código; paleta y fuentes ya fijadas en §9).
Al escribir la página, vercel-react-best-practices.
No uses ui-ux-pro-max, supabase, langfuse ni langchain-rag.
No edites backend/, data/, eval/, pyproject.toml ni openapi.json.
No generes un reporte. No calcules métricas desde las decisiones.
La pantalla habla con GET /metrics por un proxy same-origin, un solo fetch.
Null no es cero. Si unsafe_pay no es 0, marca el bloqueo I9 y no despliegues.
El vacío del API sin lector basta para aceptar. La inyección sintética es opcional y no se commitea.
No construyas las otras rutas. G3 y G4 siguen abiertos.
Al terminar: recorrido en navegador, tsc, commit y push (sección 11.8).
```
