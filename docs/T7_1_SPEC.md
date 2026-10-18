# Spec T7.1 — Política de aprobación configurable por empresa

Dueño: **Rules Engine** (resolución pura de la ruta y regla R14 en `backend/app/rules/`). Carril: B. Colabora: **API** (registro de aprobaciones y estado «x de N»), **Spec & Data** (esquema en `backend/app/models/`, grupos en `data/company.json`). Skill de dominio: NINGUNA; proceso: `test-driven-development`, `python-testing-patterns` PARCIAL.

Prioridad: **P0**. Depende de: T7.6 (dataset f7 con los casos de política). En paralelo con T7.2.

Estado: contrato para la sesión que **implemente** T7.1. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D059** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Lecturas:

- `AGENTS.md` §2 (I1, I2, I4, I5) y `docs/04_RULES_AND_DECISION_SPEC.md` §1–§3.
- `backend/app/models/rules_config.py` (`RulesConfig`, `OnFail` con `extra=forbid`; validador T5.9 del umbral).
- `backend/app/models/domain.py` líneas 12–26 (`RuleCode` = R01–R13, congelado D013) y 108–142 (`HumanEvent`, `DecisionRecord`).
- `backend/app/rules/checks.py` (`check_r04`, `CHECKS`) y `backend/app/rules/decide.py`.
- `backend/app/api/app.py` (`approve`, `reject`, `_add_human_event`, `_require_known_approver`) y `backend/app/api/asgi.py` `load_approver_emails` (la lista de aprobadores sale de `data/company.json`, nunca de `rules.json`, por T5.9).
- `data/rules.json`, `data/company.json` y `backend/tests/test_rules_config.py::test_shared_fields_match_company_json` (la clave nueva `approver_groups` debe ser aditiva y no romper esa prueba).

## 1. Qué es T7.1

El usuario del producto es el equipo de finanzas de una empresa cliente de Blinka que paga a sus proveedores (D059). Cada empresa tiene su propia política de aprobación: «sobre USD 3.000 firman dos de finanzas», «todo Marketing pasa por el CFO», «este proveedor siempre requiere aprobación». T7.1 hace esa política configurable sin tocar las reglas R01–R13: una regla nueva **R14 «Política de aprobación»** puede exigir aprobaciones humanas adicionales, nunca quitarlas.

## 2. Esquema (opcional, con default seguro)

Sección nueva opcional en `RulesConfig`: `approval_policy: ApprovalPolicy | None = None`.

```json
"approval_policy": {
  "routes": [
    {"id": "marketing-cfo", "match": {"department": "Marketing"},
     "require": {"mode": "approvals", "min_approvals": 1, "from_groups": ["cfo"]}},
    {"id": "alto-monto", "match": {"amount_base_gte": 3000},
     "require": {"mode": "approvals", "min_approvals": 2, "from_groups": ["finanzas", "cfo"]}},
    {"id": "default", "match": {}, "require": {"mode": "auto"}}
  ]
}
```

- `match` admite, todos opcionales y combinados con Y: `amount_base_gte`, `amount_base_lt`, `beneficiary` (comparación tras `normalize_beneficiary`), `department`, `invoice_type` (categoría, valores de `InvoiceType`).
- Las rutas se evalúan **en orden; gana la primera que coincide**. Validador: la última ruta debe tener `match` vacío (catch-all) e `id` únicos.
- `require.mode`: `auto` (la ruta no añade aprobaciones) o `approvals` con `min_approvals ≥ 1` y `from_groups` no vacío.
- Grupos: clave opcional nueva `approver_groups` en `data/company.json` (`{"finanzas": ["finanzas@demo.test", ...], "cfo": ["cfo@demo.test"]}`). Viven en `company.json` y no en `rules.json` porque `PUT /rules` es mutable (mismo motivo que T5.9). Validador al cargar: cada `from_groups` existe y `min_approvals ≤` miembros distintos de la unión. La lista de autores permitida pasa a ser `approvers.values() ∪ miembros de approver_groups`.
- `OnFail` gana el campo opcional `R14: FailAction = "ESCALAR"`.
- `RuleCode` se amplía de forma **aditiva** con `"R14"` (cambio de esquema congelado autorizado por D059; `DecisionRecord` no cambia).

**Default:** sin `approval_policy`, R14 **no se emite** y la lista de chequeos es idéntica a la actual. `data/rules.json` sigue válido sin cambios y el motor da 34/34, `unsafe_pay=0` en dev.

## 3. Regla R14 y composición con R04

- `resolve_route(policy, extraction, amount_base) -> Route` es función pura. Si falta un dato que la ruta usa en su `match` (depto, monto base), R14 = `INDETERMINADO` → ESCALAR (I3).
- R14 = `OK` si la ruta es `auto`; `FALLA` con `on_fail=R14` si la ruta exige aprobaciones. `detail` en español con el id de la ruta y el requisito («Ruta "alto-monto": requiere 2 aprobaciones de finanzas o cfo.»). `evidence.clause` = id de ruta; `evidence.quote` = requisito canónico `min_approvals=2;groups=cfo,finanzas` (grupos ordenados). Así el registro explica qué ruta aplicó (I5) sin campos nuevos en `DecisionRecord`.
- **Composición:** R04 no cambia. Aprobaciones requeridas efectivas = `max(base, ruta)`, donde `base = 1` si la decisión es ESCALAR por cualquier motivo (comportamiento actual) y `ruta = min_approvals` de R14 (0 si `auto`). La política solo puede añadir requisitos: una ruta `auto` nunca anula a R04 ni a ningún otro chequeo, porque `decide()` toma la severidad máxima.
- Plantilla nueva en `backend/app/records/templates.py`: «Escalada: la política de la empresa (ruta {ruta}) exige {n} aprobaciones de {grupos} (regla R14).»

## 4. Aprobaciones «x de N» (API)

- `POST /decisions/{id}/approve` sigue agregando un `HumanEvent` (I2: nunca reescribe `decision`). Validaciones nuevas cuando el registro tiene R14 en FALLA: autor ∉ miembros de `from_groups` → 422 `approver_not_in_route`; autor que ya aprobó → 409 `already_approved`; requisito ya cumplido o ya rechazada → 409 `approval_closed`. El cuerpo de respuesta sigue siendo `DecisionRecord` (compatibilidad con el frontend).
- `reject` de un aprobador elegible cierra la decisión como rechazada.
- `GET /decisions/{id}/approval` (nuevo, solo lectura): `{route_id, required, collected, approvers: [email], satisfied, rejected, payment_ready, pending_checks: [rule]}`. `collected` = autores distintos elegibles con `aprobada_humano`.
- El requisito se lee de la evidencia de R14 **congelada en el registro**; si la política actual exige más para esa ruta, se usa el máximo. Evidencia ilegible → `satisfied=false` (fail-closed).
- Registro sin R14 (empresa sin política): `route_id=null`, `required=1`, el flujo de aprobación actual no cambia.
- `payment_ready = satisfied ∧ ¬rejected ∧ todo chequeo distinto de R04 y R14 está OK`. Si queda otro chequeo no-OK, la respuesta lo lista en `pending_checks` y `payment_ready=false`.

## 5. Fuera de alcance

- Cambiar R01–R13, `decide()`, `final_gate` o los campos de `DecisionRecord`.
- Notificaciones por correo/chat a los aprobadores; flujos con orden obligatorio entre grupos; delegación de firma.
- Editar `approver_groups` desde la UI (se editan en `company.json`).
- Tocar `data/invoices/dev|holdout`, `data/golden/dev.json|holdout.json` o `catalog.json`.

## 6. Criterios de aceptación

1. `backend/tests/rules/test_approval_policy.py`: primera ruta que coincide gana; catch-all obligatorio; validador rechaza grupo inexistente y `min_approvals` imposible.
2. Sin `approval_policy`, la lista de chequeos de los 34 casos dev es idéntica byte a byte a la actual; `python eval/run_motor.py` → 34/34, `unsafe_pay=0`.
3. **Property test** (Hypothesis o generador propio con semilla fija, ≥ 500 casos): para cualquier política válida y cualquier contexto, `SEVERITY[decide(checks_con_politica)] ≥ SEVERITY[decide(checks_sin_politica)]`; en particular, nunca un no-PAGAR pasa a PAGAR.
4. Dato faltante en el `match` → R14 `INDETERMINADO` → ESCALAR.
5. Tests de API: dos aprobaciones distintas cumplen una ruta de 2; mismo autor dos veces → 409; autor fuera del grupo → 422; `GET .../approval` reporta `1 de 2` y luego `2 de 2`; `payment_ready=false` si otro chequeo sigue en FALLA.
6. Casos f7 de política (T7.6): ruta por departamento y ruta de 2 aprobaciones coinciden con su etiqueta; `unsafe_pay=0` en f7.
7. `cd backend && python -m pytest -q` 0 failed; `python -m ruff check .` ok; `backend/openapi.json` incluye `GET /decisions/{id}/approval`.
8. `docs/TASK_BOARD.md` T7.1 → HECHA con evidencia; fila en `docs/AI_USAGE_LOG.md`; commit y push con el §7.

## 7. Commit

```text
T7.1: configurable approval policy with N-of-M routes (R14)
```

## 8. Mensaje para la sesión que implementa

```text
Implementa T7.1 según docs/T7_1_SPEC.md. Decisión D059.
Usuario: equipo de finanzas de un cliente de Blinka. Añade la sección
opcional approval_policy (rutas ordenadas, gana la primera, catch-all
obligatorio) y la regla R14, que solo puede añadir aprobaciones: nunca
convierte un no-PAGAR en PAGAR. Sin approval_policy, R14 no se emite y el
motor sigue 34/34, unsafe_pay=0 en dev. Grupos de aprobadores en
data/company.json (approver_groups), no en rules.json. RuleCode se amplía
de forma aditiva con R14; DecisionRecord no cambia: la ruta aplicada va en
detail y evidence de R14. approve registra aprobaciones; GET
/decisions/{id}/approval reporta x de N y payment_ready. Tests primero,
incluido el property test de severidad. Al terminar: pytest, ruff,
run_motor dev y f7, openapi.json, tablero y AI_USAGE_LOG. Commit y push:
T7.1: configurable approval policy with N-of-M routes (R14)
```
