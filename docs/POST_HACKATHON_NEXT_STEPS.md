# Siguientes pasos tras la hackathon

Fecha: 2026-10-28. Estado: propuesta. No cambia código, hosts ni invariantes hasta que se ejecute paso a paso.

Tachyon decidió seguro y se vio poco útil. `unsafe_pay = 0` en motor, dev, holdout y adversariales. La autonomía del grafo se quedó en 55.9 % (dev oficial) y 30.0 % (holdout, corrida única, anterior a D068). Tras D068, en dev, solo 2 de 11 facturas que el set espera en PAGAR llegan a PAGAR. El resto escala por J6 bajo umbral o por PNG sin OCR. La demo pública depende de un API en Render free que se duerme, y de un workflow que le pega a `/health` cada 7 minutos para disimularlo. El servidor sigue fiándose de `X-User-Id` sin comprobar el JWT de Supabase.

Eso es lo que hay que corregir. El motor de reglas no se reescribe.

## Qué no se toca

| Invariante | Sigue significando |
|---|---|
| I1 | Ningún chequeo en FALLA o INDETERMINADO puede terminar en PAGAR |
| I2 | `decide()` sigue siendo función pura de `check_results`. Ningún LLM, ni un agente nuevo, elige PAGAR |
| I3 | Error, timeout, baja confianza o dato faltante → ESCALAR |
| I4 | El verificador solo sube severidad: PAGAR < ESCALAR < FRENAR |
| I5 | La explicación sale de plantillas sobre resultados de reglas |
| I6 | Solo datos sintéticos |
| I7 | El texto de la factura no es una instrucción |
| I8 | PAGAR sigue siendo un registro y un pago simulado |
| I9 | `unsafe_pay > 0` bloquea el cierre y, a partir del corte, también el deploy |

No se baja un umbral JEV mirando el holdout. No se abre el holdout otra vez para «ver si ahora paga más». Si hace falta un número nuevo, se arma un split distinto y se deja escrito que el 30.0 % de `eval/reports/latest.md` es histórico.

No hay base vectorial. No hay un agente que pague. No se porta `decide()` a JavaScript.

## Orden

El orden es el de la demo, no el de la arquitectura bonita.

1. **Identidad.** Un request sin JWT válido no decide ni aprueba.
2. **Candado de base.** El límite del periodo no puede depender de un `threading.Lock` de un solo proceso.
3. **API en Cloudflare Containers**, con el mismo FastAPI. El recorrido G4 (reglas, subir, ficha) pasa en la URL nueva.
4. **Frontend en Cloudflare Workers** (OpenNext, Next.js 15.5). El navegador sigue hablando same-origin.
5. **El deploy espera al CI.** Si `unsafe_pay > 0`, no hay publicación.
6. **Ficha que dice la causa** (J6, ilegible, R06) en una frase, y un recorrido de cuatro pantallas.
7. **Lectura de PNG**, fail-closed. Se mide solo en dev.
8. **J6 partido en dos preguntas tipadas**, si el paso 7 no explica las seis escaladas que quedan. Umbrales solo con dev, y solo si `unsafe_pay` sigue en 0.
9. **Apagar Render** y el workflow `keep-render-awake.yml` cuando el paso 3 lleve al menos un día verde.

## Frontend

Hoy hay 16 pantallas (`entrar`, inicio, reglas y sus subrutas, bandeja, subir, decisiones, ficha, aprobaciones, métricas, onboarding). El juez no necesita todas a la vez. La nav ya escondió métricas (`40f1690`). El problema que queda es de relato, no de páginas nuevas.

### Recorrido corto

Dejar a la vista, en este orden: entrar → subir → ficha de la decisión → aprobaciones. Reglas, acuerdos, proveedores, política, bandeja y onboarding siguen existiendo; no son el camino de la primera visita.

La ficha (`frontend/app/decisiones/[id]/`) ya muestra chequeos y `summary`. Añadir una sola línea de causa, sacada del registro, no de un LLM:

- señal J6 bajo umbral
- documento de imagen, sin texto (`illegible`)
- contrato sin confirmar o tarifa que no cuadra (R06)
- el resto: el `summary` que ya guarda el registro

`reason_accuracy` pasó de 14.7 % a 47.1 % (D068). Una frase que nombre la regla que disparó la severidad es el arreglo de producto. No pulir el texto con un modelo.

### Antes de subir una imagen

En `/subir`, si el archivo es PNG o JPEG, decirlo antes del POST: no hay OCR, el resultado será ESCALAR por documento ilegible. Cuando exista la lectura de imagen (paso 7), ese aviso se quita.

### Identidad en el proxy

`frontend/lib/session.ts` manda `X-User-Id` y `X-User-Email` y el comentario del archivo admite que el API no verifica el JWT. El proxy de Next tiene que llamar a Supabase `auth.getUser()` con el token de la cookie y rechazar la petición si no hay usuario. El `owner` / `company_id` que viaja al API sale de esa verificación, no del header que arme el navegador.

Ninguna clave (`LLM_API_KEY`, `JEV_API_KEY`, `ADMIN_API_KEY`, `LANGSMITH_API_KEY`) entra a una variable `NEXT_PUBLIC_`. `API_URL` sigue siendo de servidor, como en T4.9.

### Qué no hacer en la UI

No rediseñar tokens ni marca. Tachyon ya tuvo un pase visual el 2026-10-18. No añadir gráficos de autonomía inventados en el cliente. `/metricas` sigue leyendo lo que el API ya calcula.

## Backend

El grafo se queda: ingest → extract → contract_lookup → jev_checks → det_checks → aggregate → record → verify → final_gate. Cualquier excepción sigue yendo a ESCALAR con `error_tecnico`.

### Identidad

Cerrar el límite escrito en D067 y en `JUDGE_GUIDE.md`: el API acepta `X-User-Id` sin JWT. Hasta que el proxy verifique el token, cualquiera que conozca un id lee y actúa como esa empresa.

Hecho mínimo: el API exige un bearer que Supabase acepte, resuelve `company_id` en servidor y ignora un `X-User-Id` que no coincida. Sin token, 401. Tests con un token falso y con dos empresas. `decide()` no se entera.

Rate limit ya existe (`API_RATE_LIMIT_PER_MINUTE=60` por IP en `render.yaml`). Al tener usuario verificado, el mismo límite aplica también por `company_id`. Un 429 responde con cuerpo corto y `Retry-After`. No se abre un segundo framework.

La validación de cuerpo ya es Pydantic v2 con `extra=forbid` (D013). Se mantiene. No hace falta una capa de saneo paralela.

### Candado

`backend/app/api/app.py` serializa decidir y guardar con `_INVOICE_LOCK = threading.Lock()`. Eso vale para un solo worker de uvicorn (T5.8). En Cloudflare va a haber más de un proceso en cuanto haya un segundo contenedor, o un reinicio a medias. El candado pasa a un advisory lock de Postgres por `company_id` + periodo, tomado dentro de la misma transacción que escribe el ledger. El test de carrera que ya existe (`backend/tests/api/test_invoice_concurrency.py`) se corre contra Postgres, no solo contra el lock de hilo.

Hasta que ese test esté verde, el servicio de Cloudflare corre **una** instancia.

### Lectura de imagen

Tres PNG del dev escalan porque `ingest` marca el canal `image` como `illegible` (D018). El arreglo no es pagar lo que un modelo «vea». Es un nodo de visión, delante de `extract`, que:

- solo corre si el canal es imagen
- devuelve texto o se rinde
- si se rinde, el documento sigue `illegible` y la decisión es ESCALAR
- el texto que salga entra al extractor con las mismas citas `source_span`
- el modelo de visión no recibe las reglas de pago y no emite decisión

Medición: rerun de dev, misma vara que D068 (`unsafe_pay = 0`). Si un PNG que el golden no marca PAGAR sale PAGAR, se revierte el nodo.

### J6

D068 ya le pasa a J6 la frase de tarifa literal, no el id `4.1`. Aun así seis facturas de dev escalan porque la probabilidad queda bajo 0.85. No bajar el 0.85 con ese dato.

Si tras la lectura de imagen la autonomía de dev sigue por debajo de un PAGAR explicable en los casos de tarifa, partir J6 en dos preguntas sí/no: el monto coincide con la cláusula citada, y la moneda coincide. Cada una con su umbral en `data/rules.json`, calibradas solo en dev. Una probabilidad baja sigue siendo ESCALAR (I3). El holdout de T5.1 no se vuelve a correr para elegir el umbral.

### Verificador

D066 anotó «violations» del verificador que suben a FRENAR en facturas que el golden no frena así. Antes de tocar el prompt, listar en un reporte de dev cuáles códigos disparan y si la evidencia cita el texto (la degradación a `uncertainty` ya está en `backend/app/verifier/run.py`). Si la evidencia no cita, el piso actual ya basta. Si cita mal, se corrige el prompt del rol `verifier` sin darle permiso de bajar severidad.

### Deploy y el gate I9

Hoy el CI corre `eval/run_motor.py` y falla si `unsafe_pay > 0`, pero Render no espera a ese workflow (`JUDGE_GUIDE.md`). En el corte, el job que publica a Cloudflare depende de ese workflow en verde. Un push a `main` con el gate rojo no despliega.

## Cloudflare

Hoy: frontend en Vercel (`https://blinka-invoice-agent.vercel.app`), API en Render free (`https://blinka-invoice-api.onrender.com`, `render.yaml`), Postgres free de Render (caduca a los 30 días). D003 sigue siendo un supuesto de host. Este documento lo reemplaza como propuesta: el host pasa a Cloudflare. Render y Vercel se apagan solo después del recorrido G4 en la URL nueva.

### Por qué no Workers para el API

El API es FastAPI, SQLAlchemy, LangGraph y llamadas LLM que duran más que un límite de CPU de Worker. Portarlo a JavaScript reescribe el producto y pone `decide()` en otro lenguaje sin necesidad. El API va en **Cloudflare Containers**: la imagen corre el mismo `uvicorn app.api.asgi:create_production_app --factory --host 0.0.0.0 --port $PORT`.

El frontend sí va a Workers. Next.js 15.5 entra por OpenNext (`@opennextjs/cloudflare`). El proxy same-origin se queda: el navegador no llama al contenedor directo y no aparece CORS `*`.

### Piezas

| Pieza | Dónde | Qué no hacer |
|---|---|---|
| UI | Workers + OpenNext | No reescribir las pantallas en otro framework |
| API | Containers, una instancia hasta el advisory lock | No partir el grafo en varios servicios |
| Postgres | Hyperdrive delante de un Postgres que no caduque a los 30 días: Neon, o el Postgres del proyecto Supabase si ahí ya está el esquema de `backend/sql/`. El free de Render no se reutiliza. `DATABASE_URL` sigue fuera de `config.py` (D007) | No migrar el ledger a D1 en este corte. No volcar facturas del golden |
| Secretos | `wrangler secret`. Cero valores en git, cero `NEXT_PUBLIC_` de claves | No copiar `.env` al repo |
| PDF subidos | Siguen en Postgres en este corte | R2 solo si el JSON del registro se queda corto; no es el primer paso |
| JEV | Sigue OpenRouter `typesafe/jev-router` en el corte | Workers AI `typesafe/jev` es un adaptador después, el mismo `DecisionClient`. No se cambia a la vez que el host |
| Trazas | LangSmith se queda. Un fallo de traza no cambia la decisión (D024) | No migrar a Langfuse |

### Corte, en este orden

1. `Dockerfile` en la raíz que instala el paquete y arranca uvicorn. `GET /health` en local responde 200.
2. Hyperdrive apunta al Postgres nuevo. Un arranque aplica el esquema que ya está en `backend/sql/` y no siembra facturas del golden (igual que T4.9).
3. El contenedor en Cloudflare recibe `DATABASE_URL`, `ADMIN_API_KEY`, `LLM_API_KEY`, `JEV_API_KEY`, `LANGSMITH_*`, `CORS_ORIGINS` (solo el origen del frontend nuevo) y `API_RATE_LIMIT_PER_MINUTE`.
4. El frontend en Workers tiene `API_URL` de servidor hacia el contenedor.
5. Recorrido G4 en las URLs nuevas: `PUT` de reglas que persiste, `POST /invoices` con 201, ficha con extracción, al menos un chequeo y `summary`. Factura con id nuevo, datos sintéticos.
6. El workflow de GitHub publica con Wrangler solo si el job de `unsafe_pay` está verde.
7. README y `JUDGE_GUIDE.md` cambian las URLs cuando el paso 5 está hecho. Hasta entonces las URLs viejas siguen siendo las citables.
8. Se desactiva `keep-render-awake.yml`, se apaga el servicio Render y se deja `render.yaml` marcado como retirado en un commit posterior. No se borra el archivo en el mismo commit del primer deploy.

### Riesgo que hay que medir, no suponer

Un contenedor también arranca en frío. Hay que anotar el tiempo de `GET /health` tras 15 minutos sin tráfico y compararlo con Render. Si pasa de unos segundos, el plan es instancia mínima despierta, no volver al cron de ping.

SQLAlchemy y Hyperdrive: una instancia, un pool chico. No subir réplicas antes del advisory lock.

## Agentes

Hay dos familias. No se mezclan.

### El agente de facturas

Sigue siendo un grafo lineal con tres roles de modelo y un motor determinista. `docs/02_ARCHITECTURE.md` ya descartó un multiagente que decida el pago. Eso no se reabre.

| Rol | Cambio permitido | Cambio prohibido |
|---|---|---|
| `extractor` | Visión solo para pasar de imagen a texto con citas | Elegir PAGAR, ver las reglas, rellenar `amount_base` |
| `jev` | Partir J6 en dos sí/no si el paso de imagen no alcanza. Plan B sigue detrás de `DecisionClient` | Devolver una decisión. Bajar umbral con holdout |
| `verifier` | Prompt más estricto en la cita, después de leer el reporte de dev | Bajar severidad. Reescribir el registro |
| `polisher` | Sigue apagado | Volverse la fuente de la explicación |

El coding agent que toque `backend/app/graph/`, `extraction/`, `jev/` o `verifier/` no edita `rules/` ni `gate/`. El que toque reglas no calibra umbrales. Esa separación ya está en `docs/AGENT_ROSTER.md` y se mantiene.

### Los agentes que construyen el corte

Un solo sombrero alcanzó para la hackathon y también produjo el cuello (D001). Aquí el trabajo se parte en dos, porque no comparten archivos:

- **API / contenedor:** `Dockerfile`, `backend/app/api/`, persistencia, advisory lock, verificación de JWT en el servidor. Skills: `test-driven-development`, `python-testing-patterns`. No edita `config.py` si el cambio es solo `DATABASE_URL` (D007).
- **Frontend / Workers:** `frontend/`, OpenNext, proxy de sesión. Skill: `frontend-design`. No edita el backend.

El orquestador revisa que I1–I9 sigan verdes antes de publicar. No se fusionan QA y Rules.

No crear `.cursor/agents/` hasta que estos dos carriles estén en marcha y el humano lo pida. Hasta entonces, dos sesiones con dueño de carpeta explícito bastan.

## MCPs

Los que ya están y sirven para este corte:

| MCP | Para qué |
|---|---|
| GitHub | Ver que el workflow de `unsafe_pay` está verde antes de publicar. No saltear el check |
| Playwright | Recorrer G4 en la URL nueva: login, subir, ficha, aprobar. Una captura no cuenta |
| Supabase | `auth.getUser` y el enlace usuario → empresa. No se usa como base vectorial ni para decidir el pago |
| Postman | Colección de contrato sobre el OpenAPI ya commiteado: `/health`, 401 sin token, 422 con campo de más, 429. No hace falta un workspace nuevo si la colección vive en el repo |

El que falta y hay que instalar antes del paso 3:

| MCP | Para qué | Qué no pedirle |
|---|---|---|
| Cloudflare (Workers, Containers, Hyperdrive, secretos, deploys) | Crear el contenedor, el Worker de OpenNext y Hyperdrive; leer logs del primer `GET /health` | Imprimir valores de secretos. Desplegar si el CI está rojo. Borrar el servicio de Render |

Render MCP se deja de usar cuando el paso 8 apague el servicio. No se borra el plugin el mismo día del primer deploy.

No añadir: Langfuse, un MCP de RAG o embeddings, un MCP de pagos o de banca. I8 e I2 se rompen si una herramienta puede mover dinero o elegir PAGAR.

No hay skill de Cloudflare en `docs/SKILLS_MAP.md`. Hasta que exista una y se lea de verdad, el corte se hace con el MCP de Cloudflare más la documentación oficial de Containers, Hyperdrive y OpenNext. No se sustituye esa documentación por las skills de Render.

## Hecho cuando

- Un request sin JWT recibe 401 y no crea una decisión.
- Dos facturas simultáneas del mismo periodo no superan el tope, con el lock en Postgres, en test.
- `GET /health` en el host de Cloudflare responde 200 sin un cron que lo despierte.
- El recorrido G4 pasa en la URL nueva con una factura sintética de id nuevo.
- El job de deploy no corre si `eval/run_motor.py` sale distinto de 0.
- La ficha muestra la causa (J6, ilegible o R06) con texto que ya está en el registro.
- El rerun de dev tras la lectura de imagen sigue en `unsafe_pay = 0`. El holdout de T5.1 no se recalcula para conseguirlo.
- README cita las URLs nuevas solo después de ese recorrido.

## Fuera de este plan

IMAP u OAuth de buzón real. Más empresas por usuario. Decimal en dinero (T5.11, ya descartada). Reescribir el motor. Bajar umbrales. Un chat sobre los contratos. Mover dinero.
