# Spec T9.6 — Configuración por cuenta: cada empresa nueva empieza vacía

Dueño: **API** (configuración por dueño en `backend/app/api/` y `backend/app/persistence/`) y **Frontend** (`/reglas`, `/ajustes`, proxies de `frontend/app/api/`). Carril: B. Colabora: **Spec & Data** (modelo de borrador en `backend/app/models/rules_config.py`), **Rules Engine** (comportamiento de R01–R20 con listas vacías), **QA & Eval** (property test). Skill de dominio: NINGUNA; proceso: `test-driven-development`, `api-engineer` PARCIAL, `frontend-design` PARCIAL, `python-testing-patterns` PARCIAL.

Prioridad: **P0**. Depende de: **T9.1** (debe aterrizar primero: comparte `store.py`, `sql_store.py`, `app.py`, `tables.py`, `rules_config.py` y `/ajustes`). Coordina con T9.3 (dueño semilla de la demo). No bloquea G9 si la demo usa el dueño semilla (§6).

Estado: contrato para la sesión que **implemente** T9.6. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D062** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Lecturas:

- `AGENTS.md` §2 (I1–I4) y `docs/04_RULES_AND_DECISION_SPEC.md` (severidad `PAGAR < ESCALAR < FRENAR`, textos de explicación).
- `backend/app/models/rules_config.py` (`RulesConfig`, `CompanyRef`, validadores de `allowed_beneficiaries`, `department_budgets`, `approvers`, `threshold_within_per_payment_limit`).
- `backend/app/api/store.py` (`MemoryStore.rules`, `put_rules`, `add_beneficiary_from_decision`) y `backend/app/persistence/sql_store.py` (`RulesDocument` id=1) y `tables.py`.
- `backend/app/api/app.py` (`get_rules`, `put_rules`, `_check_admin_key`, `approve`/`reject`, `build_approval_status`) y `backend/app/api/asgi.py` (lectura de `approvers` y `approver_groups` desde `data/company.json`).
- `backend/app/api/user_scope.py` (`require_user_id`: confía en `X-User-Id` sin verificar).
- `frontend/lib/session.ts`, `frontend/lib/upstream-request.ts`, `frontend/app/AuthGate.tsx`, `frontend/app/entrar/page.tsx`, `frontend/app/api/rules/route.ts`, `frontend/app/reglas/ReglasScreen.tsx`, `frontend/app/ajustes/`.
- `docs/SUPABASE_SETUP.md` (§Seguridad), `docs/T5_9_SPEC.md` y `docs/T7_1_SPEC.md` (lista de aprobadores fuera de `PUT /rules`), `docs/T9_1_SPEC.md`, `docs/T9_3_SPEC.md`.

## 1. Qué es T9.6

Hoy hay **una sola** configuración global (`store.rules`, `GET/PUT /rules` sin dueño), cargada de `data/rules.json`, y los aprobadores salen de `data/company.json`. Cualquier cuenta nueva de Supabase ve el nombre de empresa, los beneficiarios, los presupuestos y los aprobadores de Acme Demo Inc. y sus facturas se deciden con esas reglas ajenas.

T9.6 hace la configuración **por cuenta** (`owner_id`): una cuenta nueva empieza con un **borrador vacío** en estado `configuracion_incompleta`; mientras siga incompleta, **ninguna factura de esa cuenta termina en PAGAR**. La configuración global actual pasa a ser la del dueño semilla de la demo (T9.3), así que la demo en vivo y el eval no cambian.

## 2. Modelo (Spec & Data)

- `RulesConfig` **no cambia** (estricto: lo usan `eval/run_motor.py`, golden y los archivos de `data/`). El motor y el eval siguen leyendo archivos.
- Nuevo `WorkspaceRules` (`extra=forbid`): mismos campos que `RulesConfig`, con restricciones relajadas solo donde una cuenta nueva no tiene datos:
  - `company.name: str` (puede ser `""`); `company.base_currency` por defecto `"USD"`.
  - `allowed_beneficiaries: list[str] = []`, `department_budgets: dict[str, float] = {}`, `approvers: dict[str, str] = {}`, `manual_blocks = []`, `approval_policy = None`, series, precios variables y altas vacíos.
  - Se conservan los validadores de forma (sin entradas en blanco, montos > 0, umbral ≤ límite por pago).
- `RulesConfig` pasa a validarse como «`WorkspaceRules` completo»: el motor recibe siempre un `RulesConfig` o un `WorkspaceRules` con la marca de incompleto (§4). El tipado del motor acepta la base común; ningún validador estricto existente se debilita.
- Nuevo `WorkspaceConfig`: `{owner_id, version: int, status: "configuracion_incompleta" | "completa", missing: list[str], rules: WorkspaceRules, updated_at}`.
- `status` es **calculado**, nunca enviado por el cliente: `completa` si y solo si `RulesConfig.model_validate(rules)` pasa **y** hay al menos un aprobador. `missing` usa las claves fijas `empresa`, `beneficiarios`, `presupuestos`, `aprobadores` (las del checklist de §7).

### Decisión sobre límites y umbral

`limits`, `human_approval_threshold`, `on_fail` y `jev_thresholds` del borrador **llevan valores por defecto seguros** (los de `data/rules.json`: límite por pago USD 5.000, umbral USD 3.000, `on_fail` y JEV actuales), no vacíos. Motivos: (1) no identifican a la empresa, así que no filtran datos de Acme; (2) dejarlos vacíos obliga a volver opcionales campos que hoy son `gt=0`, y un `None` en un límite es justo el tipo de hueco por el que se cuela un PAGAR; (3) mientras la cuenta esté incompleta el fail-closed de §4 manda igual. La pantalla los muestra como «Valores sugeridos, revíselos» y no cuentan para `completa`.

## 3. Persistencia y migración (API)

- Tabla nueva `workspace_rules`: `owner_id` (PK, texto), `version` (entero), `payload` (JSON de `WorkspaceRules`), `updated_at`. Sin columna `status` (se calcula al leer).
- Arranque **idempotente** contra Postgres y SQLite: `create_all` de la tabla y, si no existe la fila de `DEMO_OWNER_ID`, copiar el `payload` de `rules_document` id=1 (o de `data/rules.json` si tampoco existe) con `INSERT … ON CONFLICT DO NOTHING`. Dos arranques seguidos dejan una sola fila y no pisan cambios hechos por el dueño semilla. RLS y `REVOKE` como el resto de tablas (`docs/SUPABASE_SETUP.md`).
- `rules_document` se conserva solo para esa migración; ningún camino nuevo lo escribe.
- `DEMO_OWNER_ID`: variable de entorno con el id de Supabase de la cuenta de la demo (la misma que usa T9.3). Sin variable, `"demo-seed-owner"`.
- `MemoryStore(rules)` y `SqlStore` conservan su constructor: `rules` pasa a ser la configuración de `DEMO_OWNER_ID`, para que los tests existentes no cambien. Métodos nuevos `get_workspace(owner_id)` (crea el borrador vacío en la primera lectura) y `put_workspace(owner_id, rules, expected_version)`.
- `add_beneficiary_from_decision` (T7.4) y la compilación de acuerdos de T9.1 operan sobre la configuración del dueño de la decisión o del acuerdo, nunca sobre la global.

## 4. Fail-closed mientras la configuración está incompleta

Al procesar una factura (`POST /invoices`, bandeja de T9.2, reprocesos), el API carga la configuración **del dueño** de la factura:

- `status = configuracion_incompleta` ⇒ la decisión final es **ESCALAR o más severa, nunca PAGAR**. El motor corre igual (para que la ficha muestre cada regla) y el resultado final es `max(ESCALAR, resultado del motor)`.
- **R01 con lista vacía → FALLA**, con detalle «La lista de beneficiarios permitidos está vacía.». En estado incompleto, la severidad de ese fallo de R01 se fija en **ESCALAR** (causa `configuracion_incompleta`); los demás fallos conservan su `on_fail` (R05 duplicado, R07, R12 y los hallazgos del verificador siguen en FRENAR). Motivo: una cuenta recién creada que sube su primera factura no tiene un proveedor bloqueado, tiene una empresa sin configurar; «Frenada: Globex no está en la lista» sería falso para el usuario. Ninguna de las dos salidas paga. En cuanto la cuenta está `completa`, R01 vuelve a FRENAR como siempre.
- Reglas con datos vacíos (R03 sin presupuesto del departamento, R14 sin aprobadores) → FALLA o indeterminado ⇒ ESCALAR. La sesión que implementa comprueba regla por regla y lo cubre el property test de §9.
- Primera línea de la explicación (español sencillo, sin códigos): «Configura tu empresa para que el agente pueda decidir pagos: faltan {lista de `missing` en palabras}. Mientras tanto, cada factura queda en revisión humana.» Luego las reglas como hoy.
- `DecisionRecord` **no cambia**: la causa va en el texto de explicación y en el detalle de R01. No se agrega `RuleCode`.
- Aprobar o rechazar (`POST /decisions/{id}/approve|reject`) de una decisión cuyo dueño no tiene **ningún** aprobador configurado → **409** `no_approvers_configured` con «Agrega al menos un aprobador en Ajustes antes de aprobar o rechazar.». Con aprobadores, `author` debe estar entre los aprobadores **de ese dueño** (§5).

## 5. Aprobadores por cuenta y relación con T5.9 / T7.1

T5.9 (D055) y T7.1 decidieron que la lista que autoriza aprobar/rechazar sale de `data/company.json` y **no** se edita por `PUT /rules`, porque el proxy de Next inyecta la clave de admin en todo `PUT` y cualquier visitante podría ampliarse a sí mismo. T9.6 lo reconcilia así:

- **Dueño semilla (`DEMO_OWNER_ID`):** sin cambios. Sus aprobadores y `approver_groups` siguen saliendo de `data/company.json` y **no** se editan por `PUT /rules` (422 `approvers_locked_for_demo` si el cuerpo los cambia).
- **Otras cuentas:** `approvers` y `approver_groups` viven en su `WorkspaceRules` y se editan por `PUT /rules` **solo para su propio `owner_id`** y con la clave de admin (inyectada por el proxy). La clave de admin no distingue usuarios; lo que protege es la identidad del dueño.
- **Hecho honesto:** hoy la identidad del dueño es `X-User-Id` enviado por el navegador y el API **no verifica el JWT de Supabase** (`user_scope.py`, `docs/SUPABASE_SETUP.md`). Quien conozca o adivine el id de otra cuenta podría leer o editar su configuración y sus aprobadores. Los ids son UUID (no enumerables), pero eso no es control de acceso.
- Por eso la edición de aprobadores por cuenta **no se activa** sin el sub-ítem **T9.6.0** (P0, dentro de esta tarea, va primero):
  1. Cada proxy de `frontend/app/api/**` lee el token de acceso de Supabase (cabecera `Authorization: Bearer`, que `apiFetch` empieza a enviar desde `supabase.auth.getSession()`; hoy no la envía), lo verifica en el servidor con `supabase.auth.getUser(token)` y toma `owner_id = user.id`. Token ausente o inválido → 401 sin llamar al API.
  2. El proxy **descarta** cualquier `X-User-Id` del cliente y escribe el suyo. `apiFetch` deja de enviar `X-User-Id`; `localStorage` deja de ser fuente de identidad (solo sirve para `AuthGate`).
  3. El proxy agrega `X-Proxy-Key` (secreto de servidor `PROXY_SHARED_SECRET`); con la variable configurada, el API rechaza con 401 cualquier `X-User-Id` sin esa cabecera, para que una llamada directa a la URL pública del API no salte el proxy. Sin variable (tests, local), comportamiento actual.
  4. Actualizar `docs/SUPABASE_SETUP.md` §Seguridad.
- Si T9.6.0 no llega, T9.6 se entrega con aprobadores **solo de lectura** para cuentas nuevas (no hay quien apruebe; todo queda en ESCALAR) y se anota como deuda en el tablero. Nunca se habilita la edición confiando en `X-User-Id`.

## 6. Legado y demo

- La configuración global actual = configuración de `DEMO_OWNER_ID`. La cuenta de la demo y el comando `demo_seed --reset` de T9.3 escriben sobre ese dueño.
- `eval/run_motor.py`, golden y los splits leen `data/*.json` directo: **motor dev 34/34, f7 16/16, `unsafe_pay=0` sin cambios**. `data/rules.json`, `data/company.json`, dev, holdout, golden y f7 no se tocan.
- Decisiones: ya se recortan por `owner_id` en SQL; no cambia. **Cadena de hashes:** hoy `chain_entries` es **una sola cadena global** y `GET /decisions/verify-chain` no recorta por dueño. T9.6 no la parte; se anota como seguimiento (cadena por dueño o `verify-chain` filtrado) y no se afirma que ya sea por cuenta.

## 7. Endpoints y Frontend

- `GET /rules` (requiere dueño): devuelve el `WorkspaceConfig` del dueño; cuenta nueva → borrador vacío `configuracion_incompleta` con `missing` = las cuatro claves.
- `PUT /rules` (clave de admin + dueño): cuerpo `{rules: WorkspaceRules, expected_version}`; versión vieja → 409 `version_conflict`; validación → 422 con el campo. Guardar incompleto está permitido (es un borrador); la respuesta trae el `status` recalculado.
- Un dueño nunca lee ni escribe la configuración de otro: no hay `owner_id` en la ruta ni en el cuerpo; sale solo de la identidad (§5).
- `/reglas` y `/ajustes` para una cuenta incompleta: campos vacíos (sin prellenar con Acme), aviso fijo «Tu empresa todavía no está configurada. Mientras tanto, cada factura queda en revisión humana.» y un checklist de 4 pasos con enlace a cada sección: **Empresa** (nombre), **Beneficiarios permitidos** (al menos uno), **Presupuestos por departamento** (al menos uno), **Aprobadores** (al menos uno, con correo). Cada paso marca hecho según `missing`. Límites y umbral aparecen con «Valores sugeridos, revíselos».
- La página de inicio y la ficha de decisión muestran el mismo aviso cuando el dueño está incompleto.

## 8. Fuera de alcance

Multiempresa por usuario o invitaciones; roles dentro de una cuenta; partir la cadena de hashes por dueño; cambiar `RulesConfig`, `DecisionRecord`, `data/*.json` o los splits; copiar la configuración de la demo a una cuenta nueva («usar plantilla» puede ser un P2 aparte).

## 9. Criterios de aceptación

1. **Borrador vacío:** dueño nuevo `GET /rules` → `status=configuracion_incompleta`, nombre vacío, beneficiarios, presupuestos y aprobadores vacíos, `missing` con las 4 claves; ningún valor de `data/rules.json`/`company.json` salvo límites, umbral, `on_fail` y JEV.
2. **Factura de dueño incompleto → ESCALAR:** con dobles deterministas, una factura limpia de Globex da ESCALAR, R01 FALLA con el detalle de lista vacía y la explicación empieza por «Configura tu empresa…»; una factura duplicada sigue en FRENAR.
3. **Aislamiento:** el dueño A no lee ni modifica la configuración de B (`GET`/`PUT` con identidad A nunca tocan la fila de B); una factura de A se decide con las reglas de A; aprobar una decisión de B con identidad A → 404 como hoy.
4. **Aprobadores:** dueño sin aprobadores → approve/reject 409 `no_approvers_configured`; `author` fuera de los aprobadores del dueño → 422; cambiar aprobadores del dueño semilla por `PUT /rules` → 422 `approvers_locked_for_demo`.
5. **T9.6.0:** proxy sin token o con token inválido → 401 sin llamar al API (`supabase.auth.getUser` simulado); `X-User-Id` del cliente se ignora; con `PROXY_SHARED_SECRET`, API sin `X-Proxy-Key` → 401.
6. **Dueño semilla sin cambios:** `GET /rules` del dueño semilla == configuración global anterior (igualdad de JSON canónico); los tests existentes de API pasan sin editarse salvo el cambio de forma de `GET /rules`.
7. **Migración idempotente:** dos arranques seguidos contra SQLite (y Postgres si hay `DATABASE_URL` de prueba) → una sola fila del dueño semilla con el payload de `rules_document`.
8. **Property test** (≥ 500 casos, semilla fija): para cualquier `WorkspaceRules` incompleto y cualquier factura/contexto, la decisión nunca es PAGAR; y para cualquier configuración `completa`, el resultado es idéntico al del motor con el `RulesConfig` equivalente.
9. Motor dev 34/34 y f7 16/16, `unsafe_pay=0`; `pytest -q` 0 failed; `ruff check .` ok; frontend `npx tsc --noEmit && npm run lint && npm test` ok; `backend/openapi.json` actualizado.
10. Tablero T9.6 → HECHA con evidencia; fila en `docs/AI_USAGE_LOG.md`; commit y push con el §10.

## 10. Commit

```text
T9.6: per-account workspace rules start empty and fail closed
```

## 11. Mensaje para la sesión que implementa

```text
Implementa T9.6 según docs/T9_6_SPEC.md. Decisión D062. Requiere T9.1
ya integrada. Primero T9.6.0: el proxy de Next verifica el token de
Supabase con auth.getUser y deriva owner_id; nunca confía en X-User-Id
del cliente. Luego configuración por owner_id (tabla workspace_rules,
migración idempotente que copia la global al DEMO_OWNER_ID). Cuenta
nueva = borrador vacío configuracion_incompleta; mientras esté
incompleta ninguna factura termina en PAGAR («Configura tu empresa…»),
R01 con lista vacía FALLA, approve/reject exigen un aprobador del
dueño. RulesConfig, data/*.json y el eval no cambian. Tests primero,
incluido el property test. Al terminar: pytest, ruff, run_motor dev y
f7, frontend checks, openapi.json, tablero y AI_USAGE_LOG. Commit y push:
T9.6: per-account workspace rules start empty and fail closed
```
