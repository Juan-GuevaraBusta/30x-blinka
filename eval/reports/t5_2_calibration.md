# T5.2: calibración JEV con dev

**Fecha:** 2026-10-18 (UTC-5)
**Spec:** `docs/T5_2_SPEC.md` (D043). Skill: NINGUNA.
**Alcance:** solo `data/invoices/dev` (34 facturas) y `data/golden/dev.json`. El holdout no se usó.
**Resultado:** ningún candidato. Los seis umbrales quedan como estaban. Ninguna de las 20 facturas que no coinciden con el golden escala porque una probabilidad JEV quede bajo el umbral. Las causas son otras y no se arreglan con `jev_thresholds`.

## 1. Línea base de G3 (D039)

Autonomía **55.9 %** (19/34), `unsafe_pay = 0`. De las 15 facturas que no coincidían, 11 eran `PAGAR`→`ESCALAR` y 4 `FRENAR`→`ESCALAR`.

## 2. Entorno de las corridas

| Pieza | Valor |
|---|---|
| Comando | `python eval/run_invoices.py -o <tmp>/before.json`, carpeta por defecto `data/invoices/dev`, reglas leídas de `data/rules.json` |
| Variables forzadas | `DATABASE_URL=` (vacía: ninguna base remota), `VERIFIER_MODEL=anthropic/claude-sonnet-5`, `JEV_PLANB_MODEL=typesafe/jev-router`. Las claves salen de `.env` mediante un envoltorio que no imprime valores |
| Extractor | `openai/gpt-4o-mini` |
| Verificador | `anthropic/claude-sonnet-5` (OpenRouter) |
| JEV | cliente plan B por OpenRouter con `typesafe/jev-router` (`versions.jev = typesafe/jev-router` en los 34 registros) |
| Salidas | `/tmp`, fuera del repo, sin commitear |

**Causa raíz del `error_tecnico` generalizado en las primeras corridas.** `.env` fija `VERIFIER_MODEL=claude-sonnet-5`, un id que no existe en OpenRouter (el válido es `anthropic/claude-sonnet-5`). Con ese id el verificador falla en cada factura que llega a él, y el grafo escala por `error_tecnico`. La corrida 1, hecha con el `.env` sin tocar, dio exactamente 19/34 (55.9 %) y `unsafe_pay = 0`, con 22 registros en ESCALAR por `error_tecnico`, 9 por `documento ilegible` y 3 FRENAR por R01. Es la misma cifra que G3. Esta sesión no comprueba que G3 corriera con el mismo id. Solo se registra la coincidencia.

Con el id corregido, el verificador seguía dando `invalid_json`: `anthropic/claude-sonnet-5` envuelve el JSON en un bloque ```` ```json ````. Lo arregló el commit `71b182b` (`fix(llm): accept markdown-fenced JSON`), escrito fuera de esta tarea (T5.2 no edita `backend/app/`). La corrida 4 ya lo incluye.

**JEV.** Las señales vienen de `typesafe/jev-router`. Según su descripción oficial en OpenRouter es un router, así que las señales pueden variar de una corrida a otra. En lo observado aquí, las 20 facturas que tienen señales en las corridas 3 y 4 difieren como mucho en **0.01** de probabilidad, en cualquier señal.

## 3. Corridas

| # | Configuración | Tiempo | Autonomía | `unsafe_pay` | Validez |
|---|---|---|---|---|---|
| 1 | `.env` sin tocar (verificador `claude-sonnet-5`, id inválido) | 884 s | 19/34 (55.9 %) | 0 | Descartada: verificador inválido |
| 2 | Verificador corregido; JEV = modelo del extractor | 641 s | 19/34 (55.9 %) | 0 | Solo comprueba el cableado: JEV no es el de la demo y aún existía el fallo del bloque ```` ```json ```` |
| 3 | Verificador corregido + `typesafe/jev-router` | 947 s | 19/34 (55.9 %) | 0 | Descartada: arrancó antes de `71b182b` (fallo del bloque ```` ```json ````) y de T5.13 |
| **4** | **Verificador corregido + `typesafe/jev-router`, árbol con `71b182b` y T5.13 (`0fcc9ef`)** | **985 s** | **14/34 (41.2 %)** | **0** | **El antes válido de esta sesión** |

Antes de las corridas 2 a 4 hubo comprobaciones sobre una sola factura (dev-001), de unos 6 a 30 s cada una. Esta sesión no midió el coste de las llamadas al LLM.

El antes de esta sesión (corrida 4) da **41.2 % (14/34)** y `unsafe_pay = 0`. La línea base de G3 era 55.9 % (19/34) con `unsafe_pay = 0`. La caída no viene de los umbrales, que no cambiaron. Viene de que el verificador ahora sí responde. Ya no escala todo por fallo técnico, y en 7 casos marca una «violation» que sube la decisión a FRENAR (filas ESCALAR→FRENAR y dev-012 en la §4).

## 4. Facturas distintas al golden (corrida 4)

Umbrales vigentes: J1 0.9, J2 0.9, J3 0.85, J4 0.85, J6 0.85, J7 0.5. «Bajo umbral» sigue la comparación del código, `probability < umbral`.

| `invoice_id` | Esperada | Obtenida | Tipo | Causa | ¿JEV? |
|---|---|---|---|---|---|
| dev-001 | PAGAR | ESCALAR | sobre-escalado | R06 INDETERMINADO: el contrato es `confirmed: false` (D015). Además J6=0.01, con `answer` falso | no es JEV (R06) |
| dev-004 | PAGAR | ESCALAR | sobre-escalado | R06 INDETERMINADO; J6=0.02 | no es JEV (R06) |
| dev-005 | PAGAR | ESCALAR | sobre-escalado | R06 INDETERMINADO; J6=0.01 | no es JEV (R06) |
| dev-007 | PAGAR | ESCALAR | sobre-escalado | R06 INDETERMINADO; J6=0.01 | no es JEV (R06) |
| dev-008 | PAGAR | ESCALAR | sobre-escalado | R06 INDETERMINADO; J6=0.01 | no es JEV (R06) |
| dev-009 | PAGAR | ESCALAR | sobre-escalado | R06 INDETERMINADO; J6=0.01 | no es JEV (R06) |
| dev-002 | PAGAR | ESCALAR | sobre-escalado | `documento ilegible` (PNG sin texto en la ingesta) | no es JEV (ingesta) |
| dev-006 | PAGAR | ESCALAR | sobre-escalado | `documento ilegible` (PNG) | no es JEV (ingesta) |
| dev-010 | PAGAR | ESCALAR | sobre-escalado | `documento ilegible` (PNG) | no es JEV (ingesta) |
| dev-003 | PAGAR | ESCALAR | sobre-escalado | `error_tecnico` antes de los chequeos (Globex, `.eml`). Esta sesión vio la búsqueda de contrato fallar de forma intermitente con `schema_mismatch` para Globex | no es JEV (`error_tecnico`) |
| dev-012 | PAGAR | FRENAR | sobre-severidad | R06 INDETERMINADO; el verificador marca la «violation» `R06` y el piso lo sube a FRENAR | no es JEV (verificador) |
| dev-013 | FRENAR | ESCALAR | severidad insuficiente | R06 INDETERMINADO; R05 no detecta el duplicado porque dev-012 no se pagó y no queda en el ledger | no es JEV (R05/R06) |
| dev-026 | FRENAR | ESCALAR | severidad insuficiente | `documento ilegible` (PNG) | no es JEV (ingesta) |
| dev-034 | FRENAR | ESCALAR | severidad insuficiente | `documento ilegible` (PNG) | no es JEV (ingesta) |
| dev-021 | ESCALAR | FRENAR | sobre-severidad | «violation» del verificador (`R06_ONFAIL_NULL…`) | no es JEV (verificador) |
| dev-023 | ESCALAR | FRENAR | sobre-severidad | «violation» del verificador (`R06_ON_FAIL_MISMATCH`) | no es JEV (verificador) |
| dev-024 | ESCALAR | FRENAR | sobre-severidad | «violation» del verificador (`R06_ON_FAIL_FIELD_MISMATCH`) | no es JEV (verificador) |
| dev-025 | ESCALAR | FRENAR | sobre-severidad | «violation» del verificador (`R06_ON_FAIL_INCONSISTENT`) | no es JEV (verificador) |
| dev-031 | ESCALAR | FRENAR | sobre-severidad | «violation» del verificador `R13`. J7=0.02 bajo 0.5 detecta bien la inyección: la decisión esperada es ESCALAR | no es JEV (verificador) |
| dev-032 | ESCALAR | FRENAR | sobre-severidad | «violation» del verificador `R13`/`R06`. J7=0.02, detección correcta | no es JEV (verificador) |

Resumen: 11 PAGAR esperados no salen PAGAR (10 en ESCALAR y 1 en FRENAR), 3 son FRENAR→ESCALAR y 6 son ESCALAR→FRENAR. Ninguna sale PAGAR cuando lo esperado no es PAGAR, así que `unsafe_pay = 0`.

**Facturas con causa JEV candidata:** ninguna. En las 21 facturas con señales, J1–J4 están entre 0.99 y 1.00, siempre sobre el umbral. J7 solo queda bajo umbral en dev-031 y dev-032, las dos inyecciones, que deben escalar. J6 queda entre 0.00 y 0.02, con `answer` falso, en todas las facturas con señales. Ningún contrato está confirmado, así que no hay cláusula citada. R06 ya escala por lo mismo.

Nota: de las 14 coincidencias, 7 son ESCALAR esperados que salen ESCALAR por `documento ilegible` o `error_tecnico`. Coinciden en la etiqueta, no en el motivo.

## 5. Candidatos y recálculo sin red

El spec (§5 paso 4) solo admite un candidato si la fila es PAGAR→ESCALAR **y** la causa es una probabilidad JEV bajo el umbral. Ninguna fila cumple las dos condiciones.

Para comprobarlo, se repitió sin red el cálculo con los `jev_signals`, los `checks` y el `verifier` guardados en el JSON de la corrida 4. Se usan `decide()` y los predicados vivos del gate (`apply_verifier_severity_floor`, `checks_allow_pagar`, la lógica de `jev_allows_pagar`), y R09/R13 se recalculan con comparación estricta.

| Candidato | Autonomía predicha | `unsafe_pay` predicho | Facturas que cambian | Veredicto |
|---|---|---|---|---|
| Umbrales vigentes (control) | 14/34 (41.2 %) | 0 | 0. El recálculo reproduce las 34 decisiones observadas | — |
| J6 0.85 → 0.11 (mínimo admitido por §3: J6 > 0.1) | 14/34 (41.2 %) | 0 | 0 | Descartado: no cubre J6 = 0.00–0.02, `answer` sigue falso y R06 sigue INDETERMINADO |

No se probó ningún otro campo: la tabla de la §4 no señala ninguno. No hubo corrida de confirmación, porque §5 paso 7 la exige solo cuando el recálculo sin red predice una mejora.

## 6. Umbrales finales

| Campo | Antes | Después |
|---|---|---|
| J1 | 0.9 | 0.9 |
| J2 | 0.9 | 0.9 |
| J3 | 0.85 | 0.85 |
| J4 | 0.85 | 0.85 |
| J6 | 0.85 | 0.85 |
| J7 | 0.5 | 0.5 |

`data/rules.json` y `EXPECTED_JEV` no cambian. J5 sigue sin umbral.

## 7. Qué subiría la autonomía (fuera de T5.2)

Ninguna de estas causas se arregla con un umbral. Cada una pide decisión de su dueño:

- R06 en e2e: los `.txt` de `data/contracts/` están en `confirmed: false` a propósito (D015), y el golden lleva `contract_confirmed: true`. Ningún PAGAR es posible en e2e mientras siga así. Afecta a 6 de los 11 PAGAR esperados (Spec & Data / Rules Engine).
- Ingesta de PNG: 9 facturas dan `documento ilegible` (Agent Graph / ingesta).
- El verificador marca como «violation» un `on_fail` nulo o «mismatch» en R06 INDETERMINADO y sube 7 decisiones a FRENAR (Agent Graph / verificador).
- La búsqueda de contrato da `schema_mismatch` con `gpt-4o-mini`: siempre para Initech (`quotes.period_cap_amount` llega como número) y de forma intermitente para Globex (Agent Graph).

## 8. Exposición del holdout

Esta tarea no abrió `data/invoices/holdout/` ni `data/golden/holdout.json`. Otra sesión pasó el **motor** determinista (extracción del golden, sin LLM) sobre el holdout como chequeo de regresión. Quedó como D064: 9/10, con hold-010 (inyección por chat) en PAGAR, porque el motor no tiene texto del documento para R13/J7. Ningún umbral se ajustó con ese resultado ni con el holdout.

El holdout no se usó.
