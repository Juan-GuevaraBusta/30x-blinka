# Parámetros de la empresa ficticia

Dueño: Spec & Data. Redactado por el Orquestador el 2026-10-16.

Todos los valores salen de `docs/04` §2 y §4, o están marcados como propuesta de este turno. Estado **PROPUESTO** hasta que el humano diga lo contrario. Nada aquí es un dato real.

Semántica que estos números no pueden cambiar: **FRENAR** = violación o inconsistencia concreta, con aviso al administrador. **ESCALAR** = incertidumbre o decisión que una persona debe tomar.

## Empresa y dinero

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| Nombre de empresa ficticia | Acme Demo Inc. | PROPUESTO | Humano |
| Moneda base | USD | PROPUESTO | Humano |
| Periodo del límite | `calendar_month` | PROPUESTO | Humano |
| Límite por pago (`limits.per_payment`) | 3000 USD | PROPUESTO | Humano |
| Límite por periodo | 20000 USD | PROPUESTO | Humano |
| Umbral de aprobación humana | 3000 USD | PROPUESTO | Humano |
| Relación límite por pago / umbral | Iguales (ambos 3000). Una factura por encima dispara R02 y R04 a la vez. Los tests unitarios los separan; el set dorado, no. | PROPUESTO | Humano |
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
| R01 beneficiario no listado | FRENAR | PROPUESTO | Humano (Q3) |
| R02 sobre límite por pago | ESCALAR | PROPUESTO | Humano |
| R03 sobre límite del periodo | ESCALAR | PROPUESTO | Humano |
| R04 monto ≥ umbral humano | ESCALAR | PROPUESTO | Humano |
| R05 duplicado exacto | FRENAR | PROPUESTO | Humano |
| R05 duplicado probable | ESCALAR | PROPUESTO | Humano |
| R06 no cuadra, o contrato ausente o sin confirmar | ESCALAR | PROPUESTO | Humano |
| R07 presupuesto de departamento insuficiente | FRENAR | PROPUESTO | Humano |
| R08 destinatario distinto | ESCALAR | PROPUESTO | Humano |
| R09 extracción no fiable o campo obligatorio ausente | ESCALAR | PROPUESTO | Humano |
| R10 moneda sin tasa | ESCALAR | PROPUESTO | Humano |
| R11 fecha de pago ausente o ilegible | ESCALAR | PROPUESTO | Humano |
| R12 beneficiario en `manual_blocks` | FRENAR | PROPUESTO | Humano |
| R13 instrucciones embebidas | ESCALAR | PROPUESTO | Humano |
| Verificador, hallazgo concreto con evidencia | FRENAR + `admin_notice` | PROPUESTO (fijado en `docs/02` y `docs/04`) | Humano |
| Verificador, solo incertidumbre, o hallazgo sin evidencia | ESCALAR | PROPUESTO | Humano |
| Error, timeout, baja confianza, dato faltante | ESCALAR | PROPUESTO (I3) | Humano |

## Umbrales JEV

Por debajo del umbral → ESCALAR. Se calibran solo con el set de desarrollo (T5.2). J5 no tiene umbral en `docs/04`.

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| J1 beneficiario = emisor | 0.90 | PROPUESTO | Humano, luego calibración en dev |
| J2 monto y moneda | 0.90 | PROPUESTO | Humano |
| J3 fecha límite de pago | 0.85 | PROPUESTO | Humano |
| J4 dirigido a la empresa | 0.85 | PROPUESTO | Humano |
| J5 tipo de factura | Sin umbral. Se registra. No decide el pago. | PROPUESTO | Humano |
| J6 la cláusula citada respalda el cobro | 0.85 | PROPUESTO | Humano |
| J7 instrucciones a un sistema | 0.50 | PROPUESTO | Humano |

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

## Host (no es una regla de pago)

| Parámetro | Valor | Estado | Quién confirma |
|---|---|---|---|
| Backend | Render | PROPUESTO / SUPUESTO (Q6) | Humano |
| Base de datos | Postgres gestionado | PROPUESTO / SUPUESTO | Humano |
| Frontend | Vercel | PROPUESTO (stack de `docs/02`) | Humano |
