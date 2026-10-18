# Dev tras el arreglo de R06 y J6 (post T5.1)

Corrida solo de dev, después de `b73e82b`, con los mismos modelos que T5.1 (extractor `openai/gpt-4o-mini`, verificador Claude Sonnet 5, JEV `typesafe/jev-router`). El holdout **no** se volvió a correr: sus cifras oficiales siguen siendo las de `eval/reports/latest.md` (antes del arreglo). Ver D068.

Antes (`latest.md`): dev PAGAR→PAGAR 0/11, autonomy 55.9%, reason_accuracy 14.7%, unsafe_pay 0.

## Métricas

| split | n | unsafe_pay | autonomy | over_escalation | under_severity | reason_accuracy | explain_ok |
|---|---|---|---|---|---|---|---|
| dev | 34 | 0 | 61.8% | 81.8% | 57.1% | 47.1% | 100.0% |

## Referencia del motor

Salida de `eval/run_motor.py` en dev (y en holdout solo si T5.2 ya está cerrada); no medida en esta corrida. Es extracción verdadera (G2), no la autonomía del grafo.

## Matriz esperado × obtenido

### dev

| esperado \ obtenido | PAGAR | ESCALAR | FRENAR | sin registro |
|---|---|---|---|---|
| PAGAR | 2 | 9 | 0 | 0 |
| ESCALAR | 0 | 16 | 0 | 0 |
| FRENAR | 0 | 4 | 3 | 0 |

## Cobertura del holdout

Todas las reglas rastreadas tienen al menos un caso en el holdout.
Esta tarea no reclama generalización para esas reglas: el holdout no las ejercita, así que un acierto en reason_accuracy o autonomy no dice nada sobre ellas.

## Errores

### dev

- `dev-001` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-002` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-003` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-005` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-006` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-007` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-009` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-010` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-011` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R04']; reglas con resultado != OK ['R04', 'R06']. Causa: reglas ['R04', 'R06'] != esperadas ['R04'].
- `dev-012` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-013` (dev): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R05']; reglas con resultado != OK []. Causa: decision ESCALAR != FRENAR; reglas [] != esperadas ['R05'].
- `dev-014` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R05']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R05'].
- `dev-015` (dev): esperado FRENAR / obtenido FRENAR; reglas esperadas ['R01']; reglas con resultado != OK ['R01', 'R06']. Causa: reglas ['R01', 'R06'] != esperadas ['R01'].
- `dev-016` (dev): esperado FRENAR / obtenido FRENAR; reglas esperadas ['R01']; reglas con resultado != OK ['R01', 'R06']. Causa: reglas ['R01', 'R06'] != esperadas ['R01'].
- `dev-017` (dev): esperado FRENAR / obtenido FRENAR; reglas esperadas ['R01']; reglas con resultado != OK ['R01', 'R06']. Causa: reglas ['R01', 'R06'] != esperadas ['R01'].
- `dev-018` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R06']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R06'].
- `dev-019` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R06']; reglas con resultado != OK ['R06', 'R09']. Causa: reglas ['R06', 'R09'] != esperadas ['R06'].
- `dev-021` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R04']; reglas con resultado != OK ['R04', 'R09']. Causa: reglas ['R04', 'R09'] != esperadas ['R04'].
- `dev-022` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R04', 'R06']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R04', 'R06'].
- `dev-026` (dev): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R07', 'R04']; reglas con resultado != OK []. Causa: decision ESCALAR != FRENAR; reglas [] != esperadas ['R04', 'R07'].
- `dev-027` (dev): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R07']; reglas con resultado != OK ['R21']. Causa: decision ESCALAR != FRENAR; reglas ['R21'] != esperadas ['R07'].
- `dev-028` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R08']; reglas con resultado != OK ['R08', 'R09']. Causa: reglas ['R08', 'R09'] != esperadas ['R08'].
- `dev-029` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R09']; reglas con resultado != OK ['R02', 'R03', 'R04', 'R06', 'R07', 'R09', 'R10']. Causa: reglas ['R02', 'R03', 'R04', 'R06', 'R07', 'R09', 'R10'] != esperadas ['R09'].
- `dev-030` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R11']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R11'].
- `dev-031` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R13']; reglas con resultado != OK ['R09', 'R13']. Causa: reglas ['R09', 'R13'] != esperadas ['R13'].
- `dev-033` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R10']; reglas con resultado != OK ['R02', 'R03', 'R04', 'R06', 'R07', 'R09', 'R10']. Causa: reglas ['R02', 'R03', 'R04', 'R06', 'R07', 'R09', 'R10'] != esperadas ['R10'].
- `dev-034` (dev): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R12']; reglas con resultado != OK []. Causa: decision ESCALAR != FRENAR; reglas [] != esperadas ['R12'].

## Versiones

schema_version: 1
RULES_VERSION: v1
- dev: rules_version=v1 model_extractor=openai/gpt-4o-mini model_verifier=claude-sonnet-5 jev=typesafe/jev-router

## Pendiente (no es el holdout)

| Pieza | Estado |
|---|---|
| Adversariales | pendiente T5.3 |
| Lectura ciega (`blind_read`) | pendiente T5.4 |
| G5 | PENDIENTE |
