# Spec T5.13 — Cerrar los huecos de fraude y duplicados que terminan en PAGAR

Dueño: **Rules Engine + API**. Carril: B. Prioridad: **P0** (un solo PAGAR indebido descalifica al equipo).

Depende de: batería `backend/tests/fraud/test_fraud_scenarios.py` (commit `4aa1746`), que deja 30 casos `xfail(strict=True)` donde el motor hoy paga una factura duplicada o fraudulenta.

Decisión que fija este contrato: **D063** (`docs/DECISIONS_LOG.md`).

Coordinación: T9.1 (acuerdos) edita `rules_config.py`, `store.py`, `tables.py`, `chain.py`, `app.py`; aquí solo se agregan entradas nuevas en `RuleCode`/`OnFail`/`RulesConfig` (aditivas, con valor por defecto). T5.2 puede tocar `data/rules.json` (`jev_thresholds`); aquí no se edita `data/rules.json`.

## 1. Huecos y arreglo elegido

| # | Hueco (verificado) | Arreglo |
|---|---|---|
| 1 | `extract.py` deja `amount_base=None` y nadie lo llena; `production_processor` asienta `float(None or 0.0)` = 0.0. R03, R07 y R05 probable nunca acumulan en producción. | El grafo calcula `amount_base`/`fx` con la tabla FX (`rules/fx.py`) una vez, justo después de extraer, y lo guarda en la extracción del registro. Al asentar (API, carpeta, motor) el monto base se recalcula desde `amount`+`currency`; si no se puede convertir, la línea del ledger guarda `amount_base=None` (nunca 0.0) y R03/R07/R17/R21 quedan INDETERMINADO (ESCALAR) mientras esa línea cuente. |
| 2 | R05 compara el número de factura literal. | Número normalizado: NFKC, casefold, se separa en tramos de letras y de dígitos, se quitan ceros a la izquierda en cada tramo numérico y se descarta todo separador (`INV-001` = `inv 001` = `INV-0001` = `INV.001` = `INV001`). Mismo beneficiario normalizado + mismo número normalizado = duplicado exacto → FRENAR. Un número que queda vacío tras normalizar cuenta como ausente. |
| 3 | No hay regla de fraccionamiento (pagos partidos bajo el umbral). | Regla nueva **R21 «Fraccionamiento»** (`on_fail` por defecto ESCALAR). Si la factura está bajo `human_approval_threshold` y la suma de `amount_base` de las líneas contadas del mismo beneficiario en una ventana de `splitting_window_days` (30 por defecto) más la factura actual alcanza el umbral → FALLA. Solo sube severidad. Se emite solo cuando hay al menos una línea contada del mismo beneficiario en la ventana (sin líneas previas la regla no puede fallar). Aplica aunque `data/rules.json` no traiga ninguna sección nueva. |
| 4 | `normalize_party_name` borra cualquier sufijo legal: «Globex Inc.»/«Corp»/«S.A.»/«Co» = «Globex LLC» (R01) y «Acme Demo LLC» = «Acme Demo Inc.» (R08). | R01 y R08 comparan **identidad de parte**: nombre base + forma legal canónica. Se igualan solo grafías equivalentes de la misma forma (mayúsculas, acentos, espacios, puntuación final: `Ltda`/`Ltda.`, `Inc`/`Inc.`, `GLOBEX, LLC.`; `Limited`→`ltd`, `Corporation`→`corp`, `Incorporated`→`inc`). Formas distintas, o una con forma y otra sin ella, no coinciden. Los acrónimos con puntos (`S.A.S`, `L.L.C.`, `S.A.`) **no** se igualan a la forma sin puntos: el test existente `test_s06_pipeline_lookalike_rejected[Initech S.A.S]` exige FRENAR y se prefirió ese falso negativo seguro (la persona agrega la grafía a la lista si es legítima). Antes de comparar: NFKC; si el nombre mezcla letras no ASCII (tras quitar acentos) con letras ASCII, o trae caracteres de formato invisibles (ancho cero), no coincide con nada (fail closed). `normalize_beneficiary` (clave de búsqueda de contratos, acuerdos T9.1 y R05) no cambia. |
| 5 | La API confía en `received_at` del cliente y el ledger de producción solo muestra líneas anteriores a esa fecha: un reenvío con fecha anterior no ve el pago original. | Cambio mínimo seguro: en producción la vista del ledger incluye **todas** las decisiones ya guardadas, sin filtrar por fecha (todo lo guardado ya se procesó antes, en tiempo real). R05 ve todo el historial. El motor dorado y la carpeta conservan su orden por fecha (reproducen una secuencia). Registrar la hora del servidor como `received_at` y guardar la del cliente como metadato **queda fuera** de T5.13: exige cambiar `app.py`/`schemas.py`, que T9.1 está editando; se deja como seguimiento. Riesgo residual documentado: con fecha falsa un cliente puede mover la factura de mes (R03/R07) o sacar el duplicado probable de la ventana de 30 días; el duplicado exacto ya no se puede esquivar. |
| 6 | R11 solo exige que exista la fecha de vencimiento. | R11 FALLA si el vencimiento está más de 365 días antes o después de la recepción, con explicación en español. Severidad: `on_fail.R11` (ESCALAR en `data/rules.json`). |
| 7 | `rules.manual_blocks` nunca se lee (`graph/build.py` pasa `manual_block=False`). | R12 FALLA (FRENAR) si el beneficiario normalizado está en `manual_blocks`, además de la marca `manual_block` del contexto. |
| 8 | R13 es una lista literal de 4 frases en español. | Texto normalizado (NFKC, casefold, sin acentos, sin caracteres de ancho cero, espacios colapsados) y tres vistas deterministas: texto normalizado, variante con dígitos «leet» (`0→o`, `1→i`, `3→e`, `4→a`, `5→s`, `7→t`, `@→a`) y variante sin separadores (solo frases de 12 letras o más). Frases nuevas en inglés: «ignore previous instructions», «ignore all previous instructions», «approve this payment», «you are now», «set decision», «pay immediately», «override rules», más patrones `system\s*:` y `decision\s*[:=]?\s*pagar`. Tramos base64 (≥16 caracteres) se decodifican y se revisan con las mismas frases. |
| 9 | Caso en vivo `amount-zero` respondió HTTP 502. | Se verifica localmente que monto 0 no rompe el grafo (termina no-PAGAR). Además R02 FALLA si `amount_base <= 0` (monto no positivo no es pagable). Prueba de API con dependencias falsas: monto 0 devuelve 2xx y no-PAGAR, nunca 500. |

## 2. Fuera de alcance

- Cambiar `data/rules.json`, los goldens o `data/invoices/`.
- Hora del servidor en la API (ver hueco 5).
- Detección de nombres parecidos por distancia de edición.

## 3. Criterios de aceptación

1. `backend/tests/fraud/test_fraud_scenarios.py`: los 30 `xfail` pasan a verde y se les quita la marca; ningún test se debilita. Los dos tests que fijaban el comportamiento inseguro (`amount_base == 0.0` y «R05 ciego a la variante») se cambian para exigir el comportamiento seguro.
2. Pruebas unitarias nuevas para normalización de número, identidad de parte, R11, R12, R13, R21 y monto base del ledger.
3. `python eval/run_motor.py`: dev 34/34, `unsafe_pay=0`. `python eval/run_motor.py --split f7`: 16/16. Si un caso dorado cambia, se detiene y se reporta; no se editan goldens.
4. Suite completa de pytest en verde; `ruff check .` limpio.
5. Fila D063 en `docs/DECISIONS_LOG.md` y una línea en `docs/AI_USAGE_LOG.md`.
