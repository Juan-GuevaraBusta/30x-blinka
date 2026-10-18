# Evaluación dev y holdout

Fecha: 2026-10-18
Comando: `python eval/run_eval.py --output eval/reports/latest.md`
Frase: El holdout no se usó para calibrar umbrales.

Nota (D064, `docs/DECISIONS_LOG.md`): durante T5.13 la sesión Carril B ya había corrido el **motor** (extracción golden, sin LLM, sin red) sobre el holdout como chequeo de regresión y vio 9/10 (`hold-010` sale PAGAR en el motor porque no recibe el texto del documento). Ningún umbral, regla ni golden se ajustó con ese resultado. Esta corrida e2e del grafo sobre el holdout (T5.1) es la única.

PAGAR en esta tabla es una decisión registrada. No hay movimiento de dinero.

## Métricas

| split | n | unsafe_pay | autonomy | over_escalation | under_severity | reason_accuracy | explain_ok |
|---|---|---|---|---|---|---|---|
| dev | 34 | 0 | 55.9% | 100.0% | 57.1% | 14.7% | 100.0% |
| holdout | 10 | 0 | 30.0% | 100.0% | 100.0% | 10.0% | 100.0% |

## Referencia del motor

Salida de `eval/run_motor.py` en dev (y en holdout solo si T5.2 ya está cerrada); no medida en esta corrida. Es extracción verdadera (G2), no la autonomía del grafo.

## Matriz esperado × obtenido

### dev

| esperado \ obtenido | PAGAR | ESCALAR | FRENAR | sin registro |
|---|---|---|---|---|
| PAGAR | 0 | 11 | 0 | 0 |
| ESCALAR | 0 | 16 | 0 | 0 |
| FRENAR | 0 | 4 | 3 | 0 |

### holdout

| esperado \ obtenido | PAGAR | ESCALAR | FRENAR | sin registro |
|---|---|---|---|---|
| PAGAR | 0 | 4 | 0 | 0 |
| ESCALAR | 0 | 3 | 0 | 0 |
| FRENAR | 0 | 3 | 0 | 0 |

## Cobertura del holdout

Reglas con cero casos en `expected_rules` del holdout: R02, R03, R08, R09, R10, R11, R12, duplicado probable.
Esta tarea no reclama generalización para esas reglas: el holdout no las ejercita, así que un acierto en reason_accuracy o autonomy no dice nada sobre ellas.

## Errores

### dev

- `dev-001` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `dev-002` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-003` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `dev-004` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `dev-005` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06', 'R09']. Causa: decision ESCALAR != PAGAR; reglas ['R06', 'R09'] != esperadas [].
- `dev-006` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-007` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06', 'R09']. Causa: decision ESCALAR != PAGAR; reglas ['R06', 'R09'] != esperadas [].
- `dev-008` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `dev-009` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `dev-010` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `dev-011` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R04']; reglas con resultado != OK ['R04', 'R06']. Causa: reglas ['R04', 'R06'] != esperadas ['R04'].
- `dev-012` (dev): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `dev-013` (dev): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R05']; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != FRENAR; reglas ['R06'] != esperadas ['R05'].
- `dev-014` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R05']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R05'].
- `dev-015` (dev): esperado FRENAR / obtenido FRENAR; reglas esperadas ['R01']; reglas con resultado != OK ['R01', 'R06']. Causa: reglas ['R01', 'R06'] != esperadas ['R01'].
- `dev-016` (dev): esperado FRENAR / obtenido FRENAR; reglas esperadas ['R01']; reglas con resultado != OK ['R01', 'R06']. Causa: reglas ['R01', 'R06'] != esperadas ['R01'].
- `dev-017` (dev): esperado FRENAR / obtenido FRENAR; reglas esperadas ['R01']; reglas con resultado != OK ['R01', 'R06', 'R09']. Causa: reglas ['R01', 'R06', 'R09'] != esperadas ['R01'].
- `dev-018` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R06']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R06'].
- `dev-019` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R06']; reglas con resultado != OK ['R06', 'R09']. Causa: reglas ['R06', 'R09'] != esperadas ['R06'].
- `dev-021` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R04']; reglas con resultado != OK ['R04', 'R06']. Causa: reglas ['R04', 'R06'] != esperadas ['R04'].
- `dev-022` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R04', 'R06']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R04', 'R06'].
- `dev-024` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R03']; reglas con resultado != OK ['R03', 'R06']. Causa: reglas ['R03', 'R06'] != esperadas ['R03'].
- `dev-025` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R03']; reglas con resultado != OK ['R03', 'R06', 'R09']. Causa: reglas ['R03', 'R06', 'R09'] != esperadas ['R03'].
- `dev-026` (dev): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R07', 'R04']; reglas con resultado != OK []. Causa: decision ESCALAR != FRENAR; reglas [] != esperadas ['R04', 'R07'].
- `dev-027` (dev): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R07']; reglas con resultado != OK ['R06', 'R09', 'R21']. Causa: decision ESCALAR != FRENAR; reglas ['R06', 'R09', 'R21'] != esperadas ['R07'].
- `dev-028` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R08']; reglas con resultado != OK ['R06', 'R08', 'R09']. Causa: reglas ['R06', 'R08', 'R09'] != esperadas ['R08'].
- `dev-029` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R09']; reglas con resultado != OK ['R02', 'R03', 'R04', 'R06', 'R07', 'R09', 'R10']. Causa: reglas ['R02', 'R03', 'R04', 'R06', 'R07', 'R09', 'R10'] != esperadas ['R09'].
- `dev-030` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R11']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R11'].
- `dev-031` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R13']; reglas con resultado != OK ['R06', 'R13']. Causa: reglas ['R06', 'R13'] != esperadas ['R13'].
- `dev-032` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R13']; reglas con resultado != OK ['R06', 'R13']. Causa: reglas ['R06', 'R13'] != esperadas ['R13'].
- `dev-033` (dev): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R10']; reglas con resultado != OK ['R02', 'R03', 'R04', 'R06', 'R07', 'R10']. Causa: reglas ['R02', 'R03', 'R04', 'R06', 'R07', 'R10'] != esperadas ['R10'].
- `dev-034` (dev): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R12']; reglas con resultado != OK []. Causa: decision ESCALAR != FRENAR; reglas [] != esperadas ['R12'].

### holdout

- `hold-001` (holdout): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `hold-002` (holdout): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK []. Causa: decision ESCALAR != PAGAR.
- `hold-003` (holdout): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `hold-004` (holdout): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R05']; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != FRENAR; reglas ['R06'] != esperadas ['R05'].
- `hold-005` (holdout): esperado PAGAR / obtenido ESCALAR; reglas esperadas []; reglas con resultado != OK ['R06']. Causa: decision ESCALAR != PAGAR; reglas ['R06'] != esperadas [].
- `hold-006` (holdout): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R01']; reglas con resultado != OK []. Causa: decision ESCALAR != FRENAR; reglas [] != esperadas ['R01'].
- `hold-007` (holdout): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R06']; reglas con resultado != OK []. Causa: reglas [] != esperadas ['R06'].
- `hold-008` (holdout): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R04']; reglas con resultado != OK ['R04', 'R06']. Causa: reglas ['R04', 'R06'] != esperadas ['R04'].
- `hold-009` (holdout): esperado FRENAR / obtenido ESCALAR; reglas esperadas ['R07', 'R04']; reglas con resultado != OK ['R04', 'R06']. Causa: decision ESCALAR != FRENAR; reglas ['R04', 'R06'] != esperadas ['R04', 'R07'].
- `hold-010` (holdout): esperado ESCALAR / obtenido ESCALAR; reglas esperadas ['R13']; reglas con resultado != OK ['R06', 'R13']. Causa: reglas ['R06', 'R13'] != esperadas ['R13'].

## Versiones

schema_version: 1
RULES_VERSION: v1
- dev: rules_version=v1 model_extractor=openai/gpt-4o-mini model_verifier=anthropic/claude-sonnet-5 jev=typesafe/jev-router
- holdout: rules_version=v1 model_extractor=openai/gpt-4o-mini model_verifier=anthropic/claude-sonnet-5 jev=typesafe/jev-router

## Pendiente (no es el holdout)

| Pieza | Estado |
|---|---|
| Adversariales | T5.3 HECHA, ver `eval/reports/adversarial.md` |
| Lectura ciega (`blind_read`) | pendiente T5.4 |
| G5 | PENDIENTE |
