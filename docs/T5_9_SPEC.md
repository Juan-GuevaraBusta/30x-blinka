# Spec T5.9 — Exigir clave de administrador en los endpoints que mutan y validar el aprobador

Dueño: **API**. Carril: B. Colabora: **Frontend** (proxies de Next.js inyectan la clave server-side). Skill de dominio: `api-engineer` (PARCIAL, igual que T4.1); proceso: `python-testing-patterns` PARCIAL.

Depende de: ninguna tarea de F5 previa. **G5 depende también de esta tarea** (además de T5.1, T5.3, T5.6 y T5.8): un API sin autenticación que permite a cualquier visitante editar reglas y aprobar/rechazar pagos es un riesgo de seguridad desproporcionado para el gate final.

Estado: contrato para la sesión que **implemente** T5.9. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D055** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill `api-engineer` PARCIAL: declarar en una línea y leerla antes de tocar `app.py`. No crear workspace Postman.

Lecturas:

- `backend/openapi.json` (confirmar antes de empezar: no trae `security` ni `securitySchemes` en ningún path — así está hoy)
- `backend/app/api/app.py` líneas 52–55 (`put_rules`, sin chequeo de autor), 110–116 (`approve`/`reject`) y 139–153 (`_add_human_event`): ningún endpoint mutante comprueba quién llama
- `backend/app/api/schemas.py` línea 42 en adelante (`HumanDecisionBody.author`: `str` libre, sin validar contra una lista)
- `data/company.json` (`approvers`: hoy `{"Ingenieria": "finanzas@demo.test", "default": "cfo@demo.test"}` — los valores son los correos válidos, no las claves de departamento)
- `backend/app/models/rules_config.py` (`RulesConfig.human_approval_threshold`, `Limits.per_payment`: hoy sin validador cruzado entre los dos)
- `frontend/app/api/rules/route.ts` y las rutas equivalentes de aprobar/rechazar/subir bajo `frontend/app/api/` (proxies same-origin que ya reenvían a `API_URL`, T4.3/T4.9)
- `docs/T4_9_SPEC.md` §7–8 (same-origin, `CORS_ORIGINS`, nunca `*`)
- `docs/DECISIONS_LOG.md` D007 (`config.py` no lo edita API) y D038 (secretos con `sync: false` en Render)

## 1. El problema

`backend/openapi.json` no declara ningún esquema de seguridad: todo endpoint responde a cualquier llamada sin credenciales. `PUT /rules` reemplaza el documento completo de reglas. `POST /decisions/{id}/approve` y `POST /decisions/{id}/reject` aceptan un `author` de texto libre (`HumanDecisionBody.author`, sin validar contra nada) y producen un `HumanEvent` real en el registro. Con la URL pública de G4 (`https://blinka-invoice-api.onrender.com`), cualquier visitante puede cambiar el umbral de aprobación o aprobar una factura escalada a nombre de quien quiera.

## 2. Alcance

- Variable de entorno nueva `ADMIN_API_KEY` (nombre en `.env.example`, raíz; sin valor real). Se lee fuera de `backend/app/config.py` (D007), igual que `DATABASE_URL` y `CORS_ORIGINS` en `backend/app/api/asgi.py` / `production_processor.py`.
- `PUT /rules`, `POST /decisions/{id}/approve` y `POST /decisions/{id}/reject` exigen la cabecera `X-Admin-Key`. Comparación en tiempo constante (`hmac.compare_digest` o equivalente, nunca `==` directo sobre la clave).
- `ADMIN_API_KEY` ausente en el entorno → esos tres endpoints responden **503** (`{"detail": "admin_key_not_configured"}`) sin ejecutar la mutación. Fail-closed: sin clave configurada, nadie muta, ni siquiera con una cabecera cualquiera.
- `ADMIN_API_KEY` configurada y cabecera ausente, vacía o distinta → **401** (`{"detail": "missing_admin_key"}` si falta la cabecera, `{"detail": "invalid_admin_key"}` si no coincide). Usar 401, no 403: no hay sesión de usuario que distinga "no autenticado" de "autenticado sin permiso".
- `GET /rules`, `GET /decisions`, `GET /decisions/{id}`, `GET /metrics`, `GET /health` y `POST /invoices` **siguen públicos**, sin cabecera. `POST /invoices` conserva el límite de 2 MB (`MAX_INVOICE_BYTES`) y el rate limit por IP ya existentes (T4.1); esta tarea no les añade autenticación.
- `author` en `approve`/`reject` debe coincidir exactamente con uno de los **valores** del diccionario `approvers` de `data/company.json` (los correos: `finanzas@demo.test`, `cfo@demo.test` en el estado actual). Si no coincide, **422** (`{"detail": "unknown_approver"}`), antes de tocar el store.
- Validación cruzada en `RulesConfig` (`backend/app/models/rules_config.py`): si al leer el archivo no existe ya un `model_validator` que compare `human_approval_threshold` con `limits.per_payment`, añadir uno: `human_approval_threshold` debe ser `> 0` y `<= limits.per_payment`. Confirmado al escribir este spec: ese validador cruzado **no existe** (solo `Field(gt=0)` en cada campo por separado). Si al implementar ya existiera, no duplicarlo: decirlo en el diff y no tocar el modelo.
- Proxies de `frontend/app/api/` para `PUT /rules`, `approve` y `reject` inyectan `X-Admin-Key` desde una variable de entorno server-side (`ADMIN_API_KEY` en Vercel, nunca `NEXT_PUBLIC_`). El navegador no ve la clave. Añadir el nombre a `frontend/.env.example` sin valor.
- Actualizar `.env.example` (raíz) y `frontend/.env.example` con los nombres nuevos, sin valores reales.

## 3. Fuera de alcance

- JWT, OAuth, sesiones de usuario, roles o un sistema de permisos general. Una sola clave compartida de administrador basta para el tamaño de este hackathon.
- Autenticar `GET` o `POST /invoices`. El riesgo residual de que cualquier visitante siga pudiendo subir facturas y disparar el grafo público queda igual; se documenta, no se cierra aquí (T5.5/README ya cubre limitaciones del demo).
- Rotar o generar el valor real de `ADMIN_API_KEY` en Render o Vercel: eso es un paso humano en el dashboard (`sync: false`, igual que D038), no un cambio de código.
- Cambiar `render.yaml` más allá de añadir la entrada `ADMIN_API_KEY` con `sync: false`, en el mismo estilo que `CORS_ORIGINS`.
- Tocar el motor, el grafo, `decide()` o el ledger (eso es T5.8, un spec distinto aunque toque el mismo `app.py`).
- Añadir rate limit nuevo o cambiar el existente.

## 4. Criterios de aceptación

1. `PUT /rules` sin `X-Admin-Key` → 401 cuando `ADMIN_API_KEY` está configurada; → 503 cuando no lo está. Igual para `approve` y `reject`.
2. `PUT /rules` con `X-Admin-Key` correcta → 200, igual que antes de este spec.
3. `approve`/`reject` con `author` que no es un valor de `approvers` → 422 `unknown_approver`, sin crear `HumanEvent`. Con un valor válido y la clave correcta → 200, igual que antes.
4. `RulesConfig` rechaza (`ValidationError`) un documento con `human_approval_threshold > limits.per_payment`. Un documento con `human_approval_threshold <= limits.per_payment` sigue validando igual que hoy.
5. Comparación de la clave es de tiempo constante; un test puede documentar la elección (no medir tiempos reales, solo que se usa `hmac.compare_digest` o equivalente).
6. `GET /rules`, `GET /decisions`, `GET /decisions/{id}`, `GET /metrics`, `GET /health`, `POST /invoices` siguen sin exigir cabecera, con el mismo comportamiento previo (límite de 2 MB y rate limit intactos).
7. Proxies de `frontend/app/api/rules`, aprobar y rechazar inyectan la cabecera desde una variable server-side; ningún test ni código de cliente la expone en `NEXT_PUBLIC_*` ni en el bundle.
8. `.env.example` (raíz) y `frontend/.env.example` listan `ADMIN_API_KEY` sin valor. `render.yaml` la añade con `sync: false`.
9. `cd backend && python -m pytest -q` — 0 failed, con los tests nuevos de 401/503/422 y del validador cruzado. `python -m ruff check .` — ok. `cd frontend && npx tsc --noEmit && npm run lint && npm test` — ok si el proxy cambia.
10. README (sección que ya dejó T4.9/T5.5) documenta en una frase el riesgo residual: la UI pública sigue dejando que cualquier visitante actúe a través del proxy, con la clave ya puesta por el servidor; es una limitación de demo, no un acceso restringido a personas.
11. Diff limpio: `backend/app/api/`, `backend/app/models/rules_config.py` (solo si el validador faltaba), `backend/tests/api/`, `frontend/app/api/`, `.env.example`, `frontend/.env.example`, `render.yaml`, README, tablero y `AI_USAGE_LOG.md`. Sin tocar el grafo, el motor ni `data/rules.json`.
12. `docs/TASK_BOARD.md`: T5.9 pasa a HECHA. G5 sigue PENDIENTE.
13. Fila en `docs/AI_USAGE_LOG.md`.
14. Commit y push con el mensaje del §5.

## 5. Commit

```text
T5.9: require admin key on mutating endpoints and validate approver
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T5.9 según docs/T5_9_SPEC.md. Decisión D055.
backend/openapi.json no declara ningún esquema de seguridad. PUT /rules,
POST /decisions/{id}/approve y POST /decisions/{id}/reject (app.py líneas
52-55, 110-116, 139-153) no comprueban quién llama; HumanDecisionBody.author
(schemas.py) es texto libre sin validar contra data/company.json approvers.
Exige cabecera X-Admin-Key en esos tres endpoints, comparada en tiempo
constante contra ADMIN_API_KEY del entorno (fuera de config.py, D007). Sin
la variable configurada: 503 fail-closed. Con la variable y sin cabecera o
con cabecera incorrecta: 401. GET y POST /invoices siguen públicos. author
en approve/reject debe ser uno de los valores de approvers en
data/company.json, si no 422. Revisa si RulesConfig ya valida
human_approval_threshold <= limits.per_payment; si no, añade ese validador
cruzado (hoy no existe). Actualiza los proxies de frontend/app/api/ para que
inyecten la clave server-side, nunca en NEXT_PUBLIC_. Actualiza
.env.example, frontend/.env.example y render.yaml (sync: false) con el
nombre, sin valores. Documenta en README el riesgo residual de la demo
pública. No toques el grafo ni data/rules.json.
Al terminar: pytest, ruff, tsc/lint/vitest si cambia el frontend, tablero y
AI_USAGE_LOG. Commit y push:
T5.9: require admin key on mutating endpoints and validate approver
```
