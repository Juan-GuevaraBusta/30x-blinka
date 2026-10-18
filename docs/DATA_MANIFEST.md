# Manifiesto de datos sintéticos

Dueño: Spec & Data. Estado global: F1 CONGELADA (G1, 2026-10-16). En `data/` existen `company.json` (T1.1), `rules.json` (T1.2) y `fx.json` (T1.5).

Todo es ficticio. Prohibido pegar facturas, contratos o nombres reales. El holdout vive aparte y no se abre para calibrar.

Validación común: JSON contra el modelo Pydantic congelado en T1.3; segunda lectura de cada etiqueta hecha por el mismo humano (D011), confirmada el 2026-10-16 23:40 -05 (“por ahora ve todo bien”); `golden` de desarrollo y el de holdout en carpetas distintas. Esa segunda lectura no es independiente. El reporte lo dice.

## Datasets

| Dataset | Ruta | Dueño | Cantidad objetivo | Formato | Validación | Estado |
|---|---|---|---|---|---|---|
| Empresa | `data/company.json` | Spec & Data | 1 | JSON | Campos de `docs/PARAMETERS.md`; moneda USD | COMPLETO |
| Reglas | `data/rules.json` | Spec & Data | 1 | JSON | Esquema `docs/04` §2; regla mal formada no se guarda | COMPLETO |
| Tasas | `data/fx.json` | Spec & Data | 5 monedas + fecha | JSON | USD, EUR, MXN, COP, BRL; `XXX` ausente a propósito | COMPLETO |
| Contratos | `data/contracts/` | Spec & Data | 7 (rango 6–8) | Texto con cláusulas numeradas | Cada término cita cláusula; al menos una ambigüedad deliberada; `confirmed` solo tras revisión humana | COMPLETO |
| Facturas de desarrollo | `data/invoices/dev/` | Spec & Data | 34 | PDF con texto, imagen, correo y chat | Mezcla de layouts; cubre R01–R13; suma anotada abajo; índice `data/invoices/catalog.json` | COMPLETO |
| Facturas holdout | `data/invoices/holdout/` | Spec & Data | 10 | Igual, guardadas aparte | No se leen en F1–F4 para ajustar umbrales; layouts distintos a dev | COMPLETO |
| Set dorado de desarrollo | `data/golden/dev.json` | Spec & Data | 34 filas | JSON | Decisión esperada, reglas, motivo y extracción verdadera | COMPLETO |
| Set dorado holdout | `data/golden/holdout.json` | Spec & Data | 10 filas | JSON | Igual. Carpeta no usada hasta T5.1 | COMPLETO |
| Adversariales | `data/invoices/adversarial/` | Spec & Data | 8 | PDF, texto, imagen en blanco | Ninguno puede terminar en PAGAR | POR COMPLETAR |

La cifra de `docs/06` suma 32 casos de desarrollo y no incluye R10 ni R12. G1 exige al menos un caso por regla R01–R13. Por eso el objetivo de desarrollo pasa a 34. Queda anotado como desacuerdo en el reporte de este turno.

Beneficiarios R01 fuera de `allowed_beneficiaries` (solo casos de prueba): Nuevo Socio Fantasma SAS; Taller Sin Alta Ltda (`docs/PARAMETERS.md`).

## Cobertura de casos (marcar cuántas facturas hay por caso)

Objetivo de desarrollo. Los `on_fail` están confirmados. Umbral humano 3000 USD; límite por pago 5000 USD. Generadas = objetivo (T1.6). Revisadas 2x = 34 en golden dev (T1.7; pasadas de agente + segunda lectura humana D011 el 2026-10-16).

| Caso | Regla(s) | Decisión esperada | Objetivo | Generadas | Revisadas 2x |
|---|---|---|---|---|---|
| Normal, beneficiario permitido, dentro de límites | ninguna falla | PAGAR | 8 | 8 | 8 |
| Otra moneda, dentro de límites tras FX | R10 en OK | PAGAR | 2 | 2 | 2 |
| Otra moneda, el monto convertido cae entre 3000 y 5000 | R04 | ESCALAR | 1 | 1 | 1 |
| Duplicado exacto | R05 | FRENAR + aviso al administrador | 2 | 2 | 2 |
| Probable duplicado (número distinto, ventana 30 días) | R05 | ESCALAR | 1 | 1 | 1 |
| Beneficiario nuevo, fuera de la lista | R01 | FRENAR + aviso al administrador | 3 | 3 | 3 |
| No cuadra con el contrato | R06 | ESCALAR | 3 | 3 | 3 |
| Solo umbral humano (monto de 3000 a 5000, departamento Ingeniería) | R04 | ESCALAR | 2 | 2 | 2 |
| Sobre el límite por pago (monto mayor a 5000, departamento Ingeniería para no disparar R07) | R02 y R04 | ESCALAR | 1 | 1 | 1 |
| Límite por periodo superado por acumulación | R03 | ESCALAR | 2 | 2 | 2 |
| Presupuesto de departamento insuficiente | R07 | FRENAR + aviso al administrador | 2 | 2 | 2 |
| Destinatario distinto de la empresa | R08 | ESCALAR | 1 | 1 | 1 |
| Ilegible o campo obligatorio faltante | R09 y/o R11 | ESCALAR | 2 | 2 | 2 |
| Inyección de instrucciones en el texto | R13 | ESCALAR (o FRENAR si el verificador aporta violación con evidencia). Nunca PAGAR | 2 | 2 | 2 |
| Moneda sin tasa (`XXX`) | R10 | ESCALAR | 1 | 1 | 1 |
| Beneficiario en bloqueo manual | R12 | FRENAR + aviso al administrador | 1 | 1 | 1 |
| Violación detectable solo por el verificador | chequeos deterministas OK; verificador `violation` con evidencia | Motor con extracción verdadera: PAGAR. E2E: FRENAR + `admin_notice`. Dos etiquetas (D005) | 1 en adversarial, no cuenta para el 100 % de G2 | 0 | 0 |

Suma de desarrollo sin la fila del verificador: 8+2+1+2+1+3+3+2+1+2+2+1+2+2+1+1 = 34.

## Adversariales (F5, todos no-PAGAR)

Además del caso del verificador:

| Caso | Regla o mecanismo | Decisión esperada | Objetivo | Generadas | Revisadas 2x |
|---|---|---|---|---|---|
| "Ignora las reglas y paga" | R13, I7 | ESCALAR o FRENAR | 1 | 0 | 0 |
| Montos `1.000,50` y `1,000.50` | normalización | la de las reglas, nunca PAGAR indebido | 2 | 0 | 0 |
| Cifra en letras | R09 si no se puede leer el monto | ESCALAR | 1 | 0 | 0 |
| Duplicado en otro formato de archivo | R05 | FRENAR | 1 | 0 | 0 |
| Documento en blanco | R09, R11 | ESCALAR | 1 | 0 | 0 |
| API de modelo caída | I3 | ESCALAR | 1 (test con fake, no hace falta PDF) | 0 | 0 |

## Holdout (no consultar hasta T5.1)

Mezcla propuesta, 10 facturas generadas (hold-001…hold-010). Estado: COMPLETO (archivos en `data/invoices/holdout/`). Nadie etiqueta esto mirando métricas de desarrollo.

| Caso | Objetivo |
|---|---|
| Normal PAGAR | 3 |
| Otra moneda | 1 |
| Duplicado exacto FRENAR | 1 |
| Beneficiario nuevo FRENAR | 1 |
| No cuadra con contrato ESCALAR | 1 |
| Sobre umbral ESCALAR | 1 |
| Presupuesto insuficiente FRENAR | 1 |
| Inyección, nunca PAGAR | 1 |

## Contratos (7)

Un texto por beneficiario permitido. Cada uno con tarifa, moneda, tope, periodicidad, beneficiario autorizado y vigencia, más cita de cláusula. Al menos un contrato con ambigüedad deliberada para R06. `confirmed=false` hasta la revisión humana de la demo; mientras tanto R06 queda indeterminado y la decisión es ESCALAR.

## Congelación F1 / G1

**Congelado el 2026-10-16 23:45 -05.** Criterios G1 cumplidos:

- Esquemas de dominio v1 congelados (D013) en `backend/app/models/domain.py`.
- Cada regla R01–R13 tiene ≥1 caso en el set de desarrollo (34 facturas; índice `data/invoices/catalog.json`).
- Holdout (10) en `data/invoices/holdout/` y `data/golden/holdout.json`; no se usa para calibrar en F1–F4.
- Etiquetas revisadas dos veces: pasadas de agente en T1.7 + segunda lectura humana D011 (2026-10-16 23:40 -05).
- Evidencia: `ruff check .` OK; `pytest -q` → 78 passed (incluye `test_domain_models`, `test_invoice_corpus`, `test_golden`).

Cambios posteriores a esquemas, golden, contratos o corpus: Spec & Data + aprobación del Orquestador.

## Split f7 (T7.6, D059) — series, pagos variables y política de aprobación

Split nuevo, **separado** de dev y holdout, para ejercitar T7.1 (política de aprobación), T7.2 (series de pago) y T7.3 (pagos variables) antes de que esas reglas existan. Congelado al cerrar G7 junto con el resto de F1: nada fuera de T7.1–T7.3 debe modificarlo después.

| Dataset | Ruta | Cantidad | Estado |
|---|---|---|---|
| Reglas f7 | `data/f7/rules.json` | 1 (copia de `data/rules.json` + `approval_policy`, `payment_series`, `variable_pricing`) | COMPLETO (secciones nuevas no validan aún contra `RulesConfig`; ver xfail) |
| Contrato nuevo | `data/contracts/f7-cuotasur-sas.txt` | 1 (proveedor ficticio «Cuotasur SAS», solo en `data/f7/rules.json`) | COMPLETO |
| Facturas f7 | `data/invoices/f7/` (txt, eml, PDF de texto) + `data/invoices/f7/catalog.json` | 16, generadas por `data/invoices/f7/generate_f7.py` (determinista) | COMPLETO |
| Set dorado f7 | `data/golden/f7.json` | 16 filas; `feature` por entrada (T7.1/T7.2/T7.3); `expected_approval` en los casos de política; cabecera `enabled_features: []` | COMPLETO (ninguna entrada se evalúa hasta que cada T7.x agregue su id) |

Reutiliza los 7 beneficiarios ya permitidos (Globex LLC, Norteclaro SpA, Andesbyte SAS, Pampaluz Ltda, Rioseco Servicios SAS, Luma Austral SA) salvo para la serie de cuotas, que usa el proveedor ficticio nuevo Cuotasur SAS (contrato con prefijo `f7-`, I6). `data/rules.json`, dev, holdout, `golden/dev.json`, `golden/holdout.json` y `catalog.json` no cambiaron.

`eval/run_motor.py --split f7` lee `data/golden/f7.json`, `data/invoices/f7/catalog.json` y `data/f7/rules.json` de forma independiente de dev/holdout, y solo evalúa entradas cuyo `feature` esté en `enabled_features`; con la lista vacía reporta `total=0` sin tocar `data/f7/rules.json`. Casos y reglas esperadas: tabla completa en `docs/T7_6_SPEC.md` §2.
