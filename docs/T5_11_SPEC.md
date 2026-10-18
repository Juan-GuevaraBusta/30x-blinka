# Spec T5.11 — Dinero como `Decimal` en montos y comparaciones de límite

Dueño: **Rules Engine**. Carril: B. Colabora: **Spec & Data** (dueño de `backend/app/models/`; cualquier cambio de tipo en `domain.py` o `rules_config.py` necesita su revisión, aunque D055 ya autoriza el cambio). Skill de dominio: NINGUNA; proceso: `python-testing-patterns` PARCIAL, `test-driven-development`.

Depende de: ninguna. **P2, explícitamente recortable**: solo se hace si queda tiempo después de cerrar todo P0 (T5.7, T5.8, T5.9, T6.4) y P1 (T5.10, T6.5, T6.6). Si no hay tiempo, esta tarea se deja PENDIENTE sin penalizar el resto del tablero.

Estado: contrato para la sesión que **implemente** T5.11. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D055** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio NINGUNA. Declarar `python-testing-patterns` (PARCIAL) y leerla antes de los tests de borde.

Lecturas (todas confirmadas al escribir este spec, con el número de línea leído en esta sesión):

- `backend/app/models/domain.py` línea 41 (`LineItem.amount: float | None`), línea 46 (`FxQuote.rate: float = Field(gt=0)`), líneas 53–56 (`Extraction.amount`, `Extraction.amount_base`, ambos `float | None`)
- `backend/app/rules/context.py` línea 21 (`LedgerEntry.amount_base: float`) y línea 35–36 (`ContractTerms.fee_amount: float`)
- `backend/app/models/rules_config.py` líneas 31 y 37 (`PeriodLimit.amount`, `Limits.per_payment`, ambos `float = Field(gt=0)`) y línea 79 (`RulesConfig.human_approval_threshold: float`)
- `backend/app/rules/ledger_queries.py` líneas 27–33 (`period_paid_total`, suma con `total = 0.0`) y líneas 40–59 (`department_spent_for_budget`, misma forma)
- `backend/app/rules/checks.py` (comparaciones de R02/R03/R04/R07 contra los límites anteriores; leer antes de tocar nada, el spec no asume los nombres exactos de cada check)
- `backend/app/models/domain.py` `_Frozen` (`extra=forbid`): **estos modelos están congelados v1 (D013)**. Cambiar el tipo de un campo es un cambio de esquema. D055 es la autorización del Orquestador; aun así, anotar en `docs/AI_USAGE_LOG.md` que Spec & Data fue avisado (o que revisó el diff, si participa).

## 1. El problema

Los montos viven en `float` (IEEE 754 binario) en todo el motor: extracción, reglas, límites y sumas del ledger. `float` no representa exacto `0.1 + 0.2` ni acumula de forma estable sumas repetidas de centavos. Un límite de periodo comparado con una suma de muchos `float` puede fallar por un error de redondeo en el último dígito, justo en el borde del límite — el peor lugar para un error de este tipo en un agente que paga.

## 2. Alcance

- Los campos que representan dinero cambian de `float` a `Decimal`, cuantizado a 2 decimales con `ROUND_HALF_EVEN` en la frontera de entrada (al construir `Extraction`, al cargar `RulesConfig`, al construir `LedgerEntry`): `domain.py` (`LineItem.amount`, `Extraction.amount`, `Extraction.amount_base`), `rules_config.py` (`PeriodLimit.amount`, `Limits.per_payment`, `RulesConfig.human_approval_threshold`), `context.py` (`LedgerEntry.amount_base`, `ContractTerms.fee_amount`).
- `FxQuote.rate` **no** se cuantiza a 2 decimales (una tasa de cambio necesita más precisión); se mueve a `Decimal` sin la cuantización de dinero, o se documenta explícitamente por qué se queda en `float` si cambiarlo rompe la conversión existente de `backend/app/rules/fx.py`. Decidir y anotar, no asumir.
- Pydantic v2 serializa `Decimal` a JSON como string por defecto salvo configuración; revisar que `model_dump_json()` / `model_validate_json()` en `SqlStore` (persistencia, T4.2/T5.10) siga redondeando sin re-pasar por `float`. Si hace falta un `field_serializer`, añadirlo donde corresponda sin tocar la forma pública del JSON más de lo necesario (un juez o un test existente no debe ver un campo que antes era `800` y ahora es `"800.00"` sin que el spec lo explique).
- `ledger_queries.py`: `period_paid_total` y `department_spent_for_budget` acumulan con `Decimal("0")` en vez de `0.0`.
- Comparaciones de límite en `checks.py` (R02 por pago, R03/R07 por periodo/presupuesto) comparan `Decimal` contra `Decimal`, nunca `Decimal` contra `float`.
- Tests de borde: una factura con monto exactamente igual al límite (`PAGAR` sigue permitido, igual que hoy, porque el chequeo ya usaba `<=`/`<` según la regla — no cambiar esa semántica, solo el tipo); una factura en `límite + 0.01` (debe fallar igual que antes); una suma de periodo con varias líneas de `0.1`-style (`0.10 + 0.20 + 0.10 ...`) que en `float` podría arrastrar error y en `Decimal` no.

## 3. Fuera de alcance

- Cambiar `on_fail`, la precedencia de severidad, o cualquier regla de negocio. Solo el tipo numérico y la cuantización.
- Tocar `fx.json`, `rules.json` o el golden para que un número "se vea mejor" en `Decimal`.
- Añadir una librería nueva: `decimal` es stdlib.
- Migrar la UI (`frontend/`) a mostrar centavos distinto de como ya los muestra; si el JSON cambia de forma (`float` → string), coordinarlo con quien lea esos campos en `frontend/`, pero no es parte de esta tarea rehacer esas pantallas.
- Resolver T5.7–T5.10, T6.4–T6.6.

## 4. Criterios de aceptación

1. Tests de borde nuevos: monto == límite (comportamiento sin cambio respecto al `float` actual, documentado con el resultado real observado en esta sesión, no asumido); monto == límite + 0.01 (sigue fallando igual); suma de periodo con valores `0.1`-style que en `float` podría desviar el total y en `Decimal` da el total exacto esperado.
2. `cd backend && python -m pytest -q` — 0 failed, mismo comportamiento de negocio que antes del cambio de tipo (ningún test existente de reglas cambia su resultado esperado, solo gana precisión en los bordes).
3. `python -m ruff check .` — ok.
4. El JSON persistido (`SqlStore`) sigue siendo legible por `DecisionRecord.model_validate_json` después del cambio; si la forma del campo serializado cambia (número → string), un test cubre esa forma explícitamente y el spec lo documenta en el diff.
5. Diff no toca `data/`, `frontend/` ni reglas de negocio (`on_fail`, severidad).
6. `docs/TASK_BOARD.md`: T5.11 pasa a HECHA, o se deja explícitamente PENDIENTE con la nota «recortada por tiempo (P2)» si no se llega a implementar.
7. Fila en `docs/AI_USAGE_LOG.md`, incluyendo si Spec & Data revisó el diff de `models/`.
8. Commit y push con el mensaje del §5, solo si se implementó.

## 5. Commit

```text
T5.11: use Decimal for money and limit comparisons
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T5.11 según docs/T5_11_SPEC.md, solo si ya cerraste todo P0
(T5.7, T5.8, T5.9, T6.4) y P1 (T5.10, T6.5, T6.6). Decisión D055.
Cambia a Decimal, cuantizado a 2 decimales ROUND_HALF_EVEN en la frontera:
domain.py (LineItem.amount, Extraction.amount, Extraction.amount_base),
rules_config.py (PeriodLimit.amount, Limits.per_payment,
human_approval_threshold), context.py (LedgerEntry.amount_base,
ContractTerms.fee_amount). FxQuote.rate: decide si Decimal sin cuantizar a
centavos o se queda float, y anótalo. domain.py está congelado v1 (D013);
D055 autoriza el cambio, pero avisa a Spec & Data en AI_USAGE_LOG.
ledger_queries.py: acumula con Decimal("0"), no 0.0. Revisa cómo
SqlStore serializa Decimal a JSON y que el modelo lo vuelva a leer igual.
No cambies on_fail, severidad ni ninguna regla de negocio: solo el tipo y
la cuantización. Tests de borde: monto==límite, límite+0.01, suma de
0.1-style que en float desvía. Si no llegas a terminarla, deja T5.11
PENDIENTE con la nota «recortada por tiempo (P2)», sin romper nada ya hecho.
Al terminar (si se implementa): pytest, ruff, tablero y AI_USAGE_LOG.
Commit y push: T5.11: use Decimal for money and limit comparisons
```
