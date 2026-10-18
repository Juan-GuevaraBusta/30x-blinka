# Parámetros de la empresa ficticia

Dueño: Spec & Data. Redactado por el Orquestador el 2026-10-16.

Los `on_fail` y la separación de montos los confirmó el humano el 2026-10-16 22:21. El resto sigue **PROPUESTO**. Nada aquí es un dato real.

Semántica que estos números no pueden cambiar: **FRENAR** = violación o inconsistencia concreta, con aviso al administrador. **ESCALAR** = incertidumbre o decisión que una persona debe tomar.

## Empresa y dinero

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| Nombre de empresa ficticia | Acme Demo Inc. | PROPUESTO | Humano |
| Moneda base | USD | PROPUESTO | Humano |
| Periodo del límite | `calendar_month` | PROPUESTO | Humano |
| Límite por pago (`limits.per_payment`) | 5000 USD. Falla si el monto es mayor. | CONFIRMADO | Humano (pidió montos distintos; la cifra la fijó el orquestador) |
| Límite por periodo | 20000 USD | PROPUESTO | Humano |
| Umbral de aprobación humana | 3000 USD. Falla si el monto es mayor o igual. | CONFIRMADO | Humano (pidió montos distintos; la cifra la fijó el orquestador) |
| Relación límite por pago / umbral | Distintos. De 3000 a 5000 solo salta R04 (aprobación humana). Por encima de 5000 saltan R04 y R02. No hay factura que dispare solo R02, porque todo lo que pasa de 5000 también pasa de 3000. El caso solo-R02 vive en un test unitario. | CONFIRMADO | Humano |
| Pendientes reservan saldo | No en v1 | PROPUESTO (default de Q7) | Humano |
| Orden del ledger | Fecha de recepción, desempate por ID | PROPUESTO | Humano |
| Ventana de duplicado probable | 30 días; mismo beneficiario + mismo monto y moneda + número distinto | PROPUESTO | Humano |
| Duplicado exacto | Mismo beneficiario normalizado + mismo número de factura | PROPUESTO | Humano |

## Departamentos, presupuestos y aprobadores

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| Presupuesto Ingeniería | 8000 USD | PROPUESTO | Humano |
| Presupuesto Marketing | 5000 USD | PROPUESTO | Humano |
| Aprobador Ingeniería | `finanzas@demo.test` | PROPUESTO | Humano |
| Aprobador por defecto | `cfo@demo.test` | PROPUESTO | Humano |
| Aviso al administrador en FRENAR | Mismo buzón `cfo@demo.test`, texto de plantilla `admin_notice` | PROPUESTO | Humano |

## Beneficiarios

Nombres inventados y evidentes. Los permitidos entran en `allowed_beneficiaries`. Los otros existen para el caso R01.

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| Permitidos | Globex LLC; Initech SAS; Norteclaro SpA; Andesbyte SAS; Pampaluz Ltda; Rioseco Servicios SAS; Luma Austral SA | PROPUESTO | Humano |
| Fuera de lista (casos R01) | Nuevo Socio Fantasma SAS; Taller Sin Alta Ltda | PROPUESTO | Humano |
| Bloqueo manual (R12) | Lista vacía al inicio. Un caso de prueba bloquea `Pampaluz Ltda` solo en esa factura, vía `manual_blocks` | PROPUESTO | Humano |

## on_fail por regla

Configurable. Estos son los defaults de `docs/04` §2–§3. R09–R13 no están en el bloque `on_fail` del ejemplo JSON; la columna Default de §3 manda.

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| R01 beneficiario no listado | FRENAR | CONFIRMADO | Humano, 2026-10-16 |
| R02 sobre límite por pago | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R03 sobre límite del periodo | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R04 monto ≥ umbral humano | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R05 duplicado exacto | FRENAR | CONFIRMADO | Humano, 2026-10-16 |
| R05 duplicado probable | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R06 no cuadra, o contrato ausente o sin confirmar | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R07 presupuesto de departamento insuficiente | FRENAR | CONFIRMADO | Humano, 2026-10-16 |
| R08 destinatario distinto | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R09 extracción no fiable o campo obligatorio ausente | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R10 moneda sin tasa | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R11 fecha de pago ausente o ilegible | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| R12 beneficiario en `manual_blocks` | FRENAR | CONFIRMADO | Humano, 2026-10-16 |
| R13 instrucciones embebidas | ESCALAR | CONFIRMADO | Humano, 2026-10-16 |
| Verificador, hallazgo concreto con evidencia | FRENAR + `admin_notice` | PROPUESTO (fijado en `docs/02` y `docs/04`) | Humano |
| Verificador, solo incertidumbre, o hallazgo sin evidencia | ESCALAR | PROPUESTO | Humano |
| Error, timeout, baja confianza, dato faltante | ESCALAR | PROPUESTO (I3) | Humano |

## Umbrales JEV

Por debajo del umbral → ESCALAR. Se calibran solo con el set de desarrollo (T5.2). J5 no tiene umbral en `docs/04`.

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| J1 beneficiario = emisor | 0.90 | CALIBRADO EN DEV (T5.2) | Humano, luego calibración en dev |
| J2 monto y moneda | 0.90 | CALIBRADO EN DEV (T5.2) | Humano |
| J3 fecha límite de pago | 0.85 | CALIBRADO EN DEV (T5.2) | Humano |
| J4 dirigido a la empresa | 0.85 | CALIBRADO EN DEV (T5.2) | Humano |
| J5 tipo de factura | Sin umbral. Se registra. No decide el pago. | PROPUESTO | Humano |
| J6 la cláusula citada respalda el cobro | 0.85 | CALIBRADO EN DEV (T5.2) | Humano |
| J7 instrucciones a un sistema | 0.50 | CALIBRADO EN DEV (T5.2) | Humano |

## Tasas FX

Tabla fija. Fecha de tasa: 2026-03-01. Moneda desconocida de prueba: `XXX` (no está en la tabla) para R10.

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| USD | 1.0 | PROPUESTO | Humano |
| EUR | 1.08 USD por 1 EUR | PROPUESTO | Humano |
| MXN | 0.058 USD por 1 MXN | PROPUESTO | Humano |
| COP | 0.00025 USD por 1 COP | PROPUESTO | Humano |
| BRL | 0.18 USD por 1 BRL | PROPUESTO | Humano |
| Fecha de la tabla | 2026-03-01 | PROPUESTO | Humano |

## Modelos de la demo

El humano puede elegir el modelo, con una condición: en la demo no se usan modelos caros. Los identificadores exactos se eligen en T0.3, cuando se vea el catálogo de la clave. Van por variables de entorno.

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| Política de costo | Extractor y verificador económicos. El verificador puede ser un peldaño mejor que el extractor, sin llegar a un modelo de frontera. | CONFIRMADO | Humano, 2026-10-16 |
| Acceso a JEV | API directa de TypeSafe | CONFIRMADO | Humano, 2026-10-16 |
| Clave de JEV | No configurada en smoke G0; plan B activo (D010, D027). | ASUMIDA (plan B) | Smoke G0 2026-10-17 |
| Identificador del extractor | `openai/gpt-4o-mini` (OpenRouter; smoke G0 §6.2) | CONFIRMADO | Smoke G0 2026-10-17 |
| Identificador del verificador | Sin smoke en G0; elegir en `.env` con la misma política de costo | PENDIENTE | Humano / T4+ |

## Host (no es una regla de pago)

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| Backend | Render | PROPUESTO / SUPUESTO (Q6) | Humano |
| Base de datos | Postgres gestionado | PROPUESTO / SUPUESTO | Humano |
| Frontend | Vercel | PROPUESTO (stack de `docs/02`) | Humano |
