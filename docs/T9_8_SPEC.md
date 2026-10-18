# Spec T9.8 — Multiempresa: cada usuario pertenece a una empresa

Dueño: **API** (`backend/app/api/`, `backend/app/persistence/`) y **Frontend** (`/onboarding`, `AuthGate`, proxies de `frontend/app/api/`). Carril: B. Skill de dominio: NINGUNA; proceso: `test-driven-development`.

Prioridad: **P0** (demo). Reemplaza el diseño por cuenta de **T9.6** (`docs/T9_6_SPEC.md`, D062): la unidad de configuración ya no es el usuario sino la **empresa**.

Decisión que fija este contrato: **D067** (`docs/DECISIONS_LOG.md`).

## 1. Qué es T9.8

Hoy hay una sola configuración global y las decisiones se separan por usuario. T9.8 introduce **empresas**: el usuario se registra en `/entrar` (Supabase Auth, sin tocar `auth.users`), elige su empresa de una lista o la crea (nombre, **moneda base** y casilla «empresa demo») y queda vinculado con sus compañeros. La empresa guarda sus reglas, política de aprobación, proveedores y acuerdos; los miembros suben facturas y las escaladas llegan a los aprobadores de esa empresa.

## 2. Modelo

- `companies`: `id` (texto), `name`, `name_key` (nombre normalizado, único), `base_currency`, `is_demo`, `created_by`, `created_at`.
- `company_members`: `company_id`, `user_id` (**único**: una empresa por usuario en el MVP), `email`, `role` (`admin` | `member`), `approver_groups` (lista JSON), `created_at`.
- **Aprobador** = miembro con al menos un grupo en `approver_groups`. Quien crea la empresa queda `admin` con grupos `finanzas` y `cfo`. Quien se une queda `member` sin grupos; un `admin` puede cambiar rol y grupos (`PATCH /companies/{id}/members/{user_id}`).
- `company_id` nuevo (nulo en filas viejas) en `rules_document`, `vendor_agreement_version`, `decision_record` y `chain_entries`.
- Migración de arranque idempotente: agrega las columnas si faltan, crea la empresa demo **«Acme Demo Inc.»** (`id = demo-acme`, USD, `is_demo`) y asigna a ella toda fila con `company_id` nulo. Dos arranques seguidos dejan lo mismo.
- Vista `users_with_company` (`auth.users` ⨝ `company_members` ⨝ `companies`: correo, empresa, rol, moneda base), solo si existe el esquema `auth` (Supabase).

## 3. Empresa nueva = configuración vacía, nunca PAGAR

- Una empresa sin `rules_document` propio está **sin configurar**. `GET /rules` devuelve un borrador con el nombre y la moneda de la empresa, beneficiarios, presupuestos, aprobadores y política vacíos, y límites/umbral/`on_fail`/JEV con los valores seguros actuales.
- Cada factura de una empresa sin configurar se decide con una configuración de resguardo donde **R01 falla con severidad ESCALAR** (no hay beneficiarios permitidos). El resultado es ESCALAR o más severo; por defensa, un PAGAR se sube a ESCALAR. El resumen empieza por «Configura tu empresa para que el agente pueda decidir pagos…».
- La empresa queda configurada cuando un `admin` guarda una configuración completa con `PUT /rules` (validación `RulesConfig` estricta).

## 4. Moneda base

`companies.base_currency` define `RulesConfig.company.base_currency` y la conversión FX: la tabla `data/fx.json` (USD por unidad) se recalcula a la moneda base de la empresa. Crear una empresa con una moneda que no está en `fx.json` → **422** `unsupported_currency`.

## 5. Identidad y permisos (límite conocido del hackathon)

- La identidad sigue siendo la del hackathon: el navegador guarda el id y el correo de Supabase al iniciar sesión y los envía como `X-User-Id` y `X-User-Email`; los proxies de Next los reenvían. **El API no verifica el JWT de Supabase**: quien conozca el id de otro usuario puede actuar como él. Queda anotado en `README.md` «Limitaciones».
- Todo endpoint con datos de empresa resuelve la empresa desde la membresía del usuario; sin membresía → **403** `no_company` (el frontend lleva a `/onboarding`).
- `PUT /rules` y escribir acuerdos: clave de admin (la inyecta el proxy) **y** rol `admin` en la empresa.
- Aprobar/rechazar: clave de admin, la decisión debe ser de la empresa del usuario (si no, 404) y `author` debe ser aprobador de esa empresa (R14: además estar en los grupos de la ruta). En la empresa demo también valen los aprobadores de `data/company.json`.
- `PUT /admin/members` (solo clave de admin) adjunta un usuario a una empresa; lo usa el script de semilla.

## 6. Endpoints nuevos

`GET /companies`, `POST /companies {name, base_currency, is_demo}`, `POST /companies/{id}/join`, `GET /me`, `GET /companies/{id}/members`, `PATCH /companies/{id}/members/{user_id}`, `PUT /admin/members`.

## 7. Frontend

`/entrar` guarda id y correo. `AuthGate` consulta `GET /me` y manda a `/onboarding` si no hay empresa. `/onboarding`: elegir empresa existente o crear una (nombre, moneda base, «empresa demo»). La barra lateral muestra empresa y rol; «Aprobaciones» solo aparece para aprobadores.

## 8. Semilla de la demo

```bash
ADMIN_API_KEY=... python backend/scripts/seed_demo.py --apply --with-rules \
  --member-user-id <uuid de Supabase> --member-email <correo> --role admin
```

Adjunta el usuario a «Acme Demo Inc.» con grupos `finanzas` y `cfo`, siembra la política 2 de N, el proveedor de iguala fija (caso PAGAR) y el de horas (caso aprobación). El tercer caso de la demo es «ya pagada → reenviada → FRENAR».

## 9. Fuera de alcance

Verificación del JWT en el servidor, invitaciones, varias empresas por usuario, cadena de huellas por empresa (`chain_entries` guarda `company_id` pero `verify-chain` sigue recorriendo la cadena global).

## 10. Criterios de aceptación

1. La empresa A no lee ni aprueba decisiones, reglas ni acuerdos de la empresa B.
2. Factura de empresa nueva → ESCALAR (nunca PAGAR) con «Configura tu empresa…».
3. Sin membresía → 403; `PUT /rules` de un `member` → 403; `author` que no es aprobador → 422.
4. Migración: filas sin `company_id` quedan en la empresa demo; idempotente.
5. Moneda base fuera de `fx.json` → 422.
6. `pytest -q`, `ruff`, motor dev 34/34, f7 16/16, fraude 79/79, `openapi.json` regenerado; frontend `lint`, `tsc`, `test`, `build`.
