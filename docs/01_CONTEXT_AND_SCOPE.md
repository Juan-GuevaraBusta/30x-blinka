# 01 — Contexto y alcance del reto

## Ficha
- **Empresa/cliente:** Blinka. **Área:** Producto. **Tipo:** crear algo nuevo. **Entregable:** agente funcionando.
- **Reto en una frase:** construir un agente que revise las cuentas de una empresa y decida cuáles pagar por ella dentro de las reglas que la empresa define, y que pida permiso a una persona cuando algo se sale de esas reglas.
- **Tiempo:** 36 h. **Equipo:** una persona (a confirmar, ver `08`).

## Cómo funciona hoy (el problema)
1. Llega una factura o cuenta de cobro por correo, PDF o chat.
2. Alguien de finanzas la revisa, la compara con lo acordado y busca datos de quien cobra.
3. Pide aprobación por chat o correo.
4. Crea el pago a mano en la plataforma, a menudo en otra moneda y hacia otro país.
5. Concilia en una hoja de cálculo qué se pagó y por qué.

Todo es manual, mensual y depende de que una persona esté disponible.

## A quién afecta
Empresas constituidas en EE. UU. que operan en varios países, con equipo, proveedores y contratistas en Latinoamérica y otras regiones. Hacen decenas de pagos al mes.

**Usuario del producto (D059):** el equipo de finanzas de una empresa cliente de Blinka que paga a sus propios proveedores a través de Blinka. Blinka no tiene este problema; lo tienen sus clientes. Cada empresa define su política de aprobación, y la complejidad crece con pagos variables (tarifa × cantidad, tramos, comisiones, topes), pagos en serie (retainers, cuotas, hitos) y proveedores nuevos (fuente: mensaje de Blinka, Sebastián Linares).

## Por qué importa
Más empresas arman agentes propios y quieren que también paguen. Lo que falta es **confianza**: que pague solo lo que debe, explique cada decisión y nunca se pase de los límites.

## Hasta dónde llega el flujo
Termina cuando el agente decide qué hacer con cada factura: **pagarla, frenarla o escalarla**. No se mueve dinero ni se conecta a una plataforma de pagos. Basta con decidir, registrar y explicar por qué.

## Qué entra
- Leer una factura y extraer **a quién, cuánto, en qué moneda y para cuándo**.
- Decidir según **reglas configurables**: límites por pago y por periodo, beneficiarios permitidos, aprobación humana por encima de cierto monto.
- **Registro de cada decisión** (pagó, frenó o escaló) y por qué.

## Qué no entra
Ejecutar pagos reales · abrir cuentas · verificar identidad de empresas · decisiones de cumplimiento o fraude · diseño de la app de Blinka.

> Consecuencia de diseño: los duplicados se tratan como **regla de negocio** (ya pagada / posible duplicado), no como detección de fraude. "Verificar que la factura es de la empresa" se reduce a comparar el destinatario con el nombre configurado, sin validación externa.

## Datos de trabajo
No hay API ni facturas de ejemplo. Cada equipo arma su set: facturas simuladas (PDF, imagen, correo o chat) y reglas de una empresa ficticia. Se pueden compartir entre equipos. Deben incluir **casos normales y casos trampa**:
- cobro duplicado
- beneficiario nuevo fuera de la lista permitida
- factura que no cuadra con lo acordado
- monto sobre el límite que requiere aprobación humana
- saldo o presupuesto insuficiente para el periodo

(Añadimos por nuestra cuenta: moneda extranjera, documento ilegible, datos faltantes e inyección de instrucciones en el texto. Ver `06`.)

## Entregable esperado
Agente funcionando sobre su set + **pantalla simple** donde la empresa:
1. define sus reglas,
2. ve qué decidió pagar, qué frenó, qué dejó pendiente de aprobación y **por qué**.

## Restricciones
- Ningún dato real de clientes ni empresas.
- El agente nunca aprueba un pago fuera de las reglas sin aprobación humana.
- Cada decisión se puede explicar después.
- Libertad total de modelo, lenguaje y framework.

## Cómo se ve el éxito
| Eje | Definición | Nota |
|---|---|---|
| **Autonomía** | % del set que el agente decide correctamente sin intervención humana | "Correcta" = coincide con la decisión esperada, incluidos frenos/escalamientos legítimos |
| **Seguridad** | Cero pagos aprobados fuera de las reglas | **Aprobar un pago indebido descalifica** |
| **Explicabilidad** | Cualquier persona entiende por qué pagó/frenó/escaló leyendo el registro, sin abrir el código | Se prueba con lectura ciega |

## Glosario
- **PAGAR:** el agente autoriza (simulado) el pago sin intervención humana. Solo si todo pasa.
- **FRENAR:** el pago no procede por una regla dura; se informa y queda registrado.
- **ESCALAR:** pendiente de aprobación humana (monto alto, ambigüedad, desajuste, baja confianza, error).
- **JEV:** modelo de decisión de TypeSafe AI. No chatea: responde preguntas tipadas (sí/no, elección, puntaje) con probabilidad calibrada, rápido y barato. Lo usamos como **verificador de señales** sobre la extracción, no como decisor de pago.
- **Verificador:** LLM fuerte que audita el registro completo (¿lo hecho concuerda con lo establecido?). Solo puede subir severidad.
- **Harness:** contexto, memoria, validaciones, evaluaciones, registros y feedback loops que rodean al modelo.
- **Registro (de decisión):** objeto estructurado con datos leídos, chequeos, decisión, explicación y enlace a la traza.
- **Set dorado / holdout:** facturas con decisión esperada; el holdout se mantiene ciego para no sobreajustar.
