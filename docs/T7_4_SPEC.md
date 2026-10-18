# Spec T7.4 — Alta de proveedor nuevo desde una factura frenada

Dueño: **API** (endpoint, persistencia y entrada nueva de la cadena). Carril: B. Colabora: **Rules Engine** (regla R20 y tipo de entrada en `backend/app/records/chain.py`), **Frontend** (acción en la ficha), **Spec & Data** (esquema). Skill de dominio: `api-engineer` PARCIAL (backend), `frontend-design` PARCIAL (botón); proceso: `test-driven-development`.

Prioridad: **P1**. Depende de: T5.9 (clave de admin, HECHA) y T5.10 (cadena solo-anexar, HECHA). Independiente de T7.1–T7.3.

Estado: contrato para la sesión que **implemente** T7.4. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D059** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Lecturas:

- `AGENTS.md` §2 (I1, I2, I4, I5) y `docs/04_RULES_AND_DECISION_SPEC.md` §1 (la aprobación humana es un evento nuevo; el registro es inmutable).
- `backend/app/rules/checks.py` `check_r01` y `data/rules.json` (`allowed_beneficiaries`, `on_fail.R01 = FRENAR`).
- `backend/app/api/app.py` (`put_rules`, `_check_admin_key`, `_require_known_approver`, `_add_human_event`).
- `backend/app/records/chain.py` (entradas `decision` y `human_event`, `verify_chain`) y `backend/app/persistence/tables.py` (`chain_entries.kind`).
- `docs/T5_10_SPEC.md` y la fila D058 de `docs/DECISIONS_LOG.md` (ningún hash guardado se reescribe).

## 1. Qué es T7.4

Cada empresa se entera de sus proveedores nuevos de forma distinta; en este producto, el primer aviso suele ser una factura frenada por R01 («no está en la lista»). Hoy el equipo de finanzas tiene que editar el JSON de reglas a mano. T7.4 añade una acción explícita y auditada, «Agregar a proveedores permitidos», que **nunca paga la factura que la disparó** ni la siguiente sin aprobación humana.

## 2. Alcance

- **Config opcional** en `RulesConfig`: `vendor_onboarding: {enabled: bool = false, first_invoice_requires_approval: bool = true}` y `vendor_additions: list[{beneficiary, added_at, added_by, reason, source_decision_id}] = []`. Sin la sección, el comportamiento es el actual (endpoint responde 403 `vendor_onboarding_disabled`).
- **Endpoint** `POST /decisions/{id}/add-beneficiary` (clave de admin vía `Depends(_check_admin_key)`, igual que T5.9). Cuerpo `{author, reason}`; `author` ∈ aprobadores de `data/company.json` (422 si no). Solo si el registro existe (404), tiene R01 en `FALLA` (409 `r01_not_failed`) y el beneficiario no está ya en la lista (409 `already_allowed`). Efecto, en una sola transacción: añade el beneficiario a `allowed_beneficiaries`, agrega una fila a `vendor_additions` y anexa una entrada de cadena nueva.
- **Cadena (T5.10):** tipo de entrada nuevo `allowlist_change`, `ref_id` = id de la decisión origen; payload inmutable `{beneficiary, author, reason, at, source_decision_id}`, hasheado completo como `human_event`. `verify_chain` lo recorre sin lógica especial. Ningún hash existente se reescribe.
- **Regla R20 «Primer pago de proveedor nuevo»** (Rules Engine): si el beneficiario está en `vendor_additions` y el ledger no tiene todavía un `aprobada_humano` suyo posterior a `added_at`, R20 = `FALLA` con `on_fail` ESCALAR. Se emite solo si `vendor_additions` no está vacío. `RuleCode` suma `R20` de forma aditiva; `OnFail.R20="ESCALAR"` opcional (D059).
- **La factura origen no cambia:** su registro sigue en FRENAR (inmutable, I2). Para pagarla, el equipo la vuelve a subir; la nueva evaluación queda, como mínimo, en ESCALAR por R20 (y por R06 si no hay contrato confirmado) y pasa por aprobación normal (T7.1 si hay política).
- **Frontend:** en `/decisiones/[id]`, si R01 está en FALLA y `vendor_onboarding.enabled`, botón «Agregar a proveedores permitidos» con motivo obligatorio y aviso: «Esta factura no se pagará. La próxima factura de este proveedor quedará pendiente de aprobación.»

## 3. Fuera de alcance

- Pagar, reabrir o reevaluar automáticamente la factura frenada.
- Verificar identidad o datos bancarios del proveedor (fuera del reto, `docs/01`).
- Quitar proveedores de la lista desde esta acción (se sigue usando `PUT /rules`).
- Que un LLM proponga o apruebe el alta.

## 4. Criterios de aceptación

1. Tests de API: sin clave → 401/503 antes de validar el cuerpo; autor desconocido → 422; R01 OK → 409; alta válida → beneficiario en la lista, fila en `vendor_additions`, entrada `allowlist_change` en la cadena.
2. `GET /decisions/verify-chain` → `ok=true` tras el alta; manipular el payload de la entrada `allowlist_change` en la base → `ok=false` con su `ref_id`.
3. El registro de la factura origen es idéntico antes y después del alta (misma `decision`, mismo hash de cadena).
4. Reevaluar la misma factura tras el alta → ESCALAR con R20 en FALLA; tras un `aprobada_humano` de ese proveedor, la siguiente factura ya no falla R20.
5. Property test: con cualquier `vendor_additions`, la severidad nunca baja respecto al motor sin la sección.
6. Sin la sección, motor dev 34/34, `unsafe_pay=0`; `pytest -q` 0 failed; `ruff check .` ok; si se toca el frontend, `npx tsc --noEmit && npm run lint && npm test` ok.
7. `backend/openapi.json` incluye el endpoint. Tablero T7.4 → HECHA; fila en `docs/AI_USAGE_LOG.md`; commit y push con el §5.

## 5. Commit

```text
T7.4: audited add-beneficiary action from R01 failures (R20)
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T7.4 según docs/T7_4_SPEC.md. Decisión D059.
Endpoint POST /decisions/{id}/add-beneficiary con clave de admin (T5.9) y
autor de company.json: solo si R01 falló. Añade el beneficiario a la lista,
una fila en vendor_additions y una entrada nueva allowlist_change en la
cadena solo-anexar de T5.10 (no reescribas ningún hash). La factura origen
sigue FRENAR (registro inmutable). Regla R20: el primer pago de un
proveedor recién agregado siempre ESCALAR hasta una aprobación humana. Sin
vendor_onboarding habilitado, el endpoint responde 403 y el motor no
cambia (dev 34/34, unsafe_pay=0). Botón en /decisiones/[id] con motivo
obligatorio. Al terminar: pytest, ruff, verify-chain, frontend checks,
openapi.json, tablero y AI_USAGE_LOG. Commit y push:
T7.4: audited add-beneficiary action from R01 failures (R20)
```
