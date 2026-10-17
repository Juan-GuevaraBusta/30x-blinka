# Estado de preguntas abiertas

Dueño: Orquestador. Fuente: `docs/08_OPEN_QUESTIONS_AND_ASSUMPTIONS.md`, más las que salieron al armar el roster.

Fecha de las respuestas: 2026-10-16 22:21 (UTC-5).

## Preguntas

| ID | Pregunta | Bloqueante | Propuesta por defecto | Respuesta | Estado (ABIERTA\|RESUELTA\|ASUMIDA) | Responde |
|---|---|---|---|---|---|---|
| Q1 | ¿Cómo se accede a JEV? | La vía ya no. La clave sí, para T0.3. | API directa. Si la clave no llega, plan B. | API directa de TypeSafe. La clave todavía no está; la consigue el humano. El formato de la petición se comprueba en T0.3. | RESUELTA en la vía. La clave sigue PENDIENTE. | Humano, 2026-10-16 22:21 |
| Q2 | ¿Qué modelos, y con qué presupuesto? | No, si se respeta la política de costo. | Modelos baratos por variables de entorno. | El humano puede elegir el que sea. En la demo no se usan modelos caros. Extractor económico; verificador como mucho un peldaño mejor. IDs en T0.3. | RESUELTA | Humano, 2026-10-16 22:21 |
| Q3 | ¿Se confirman los `on_fail` de `docs/04`, con beneficiario nuevo = FRENAR? | No. Ya no bloquea T1.7. | Esos defaults. | Sí. | RESUELTA | Humano, 2026-10-16 22:21 |
| Q4 | ¿Hay una segunda persona para releer las etiquetas y para leer 5 explicaciones sin haber visto el código? | No para codar. | La misma persona hace una segunda pasada más tarde y se anota que no es independiente. | No entendió la pregunta. Sigue ABIERTA. Explicación en el chat del 2026-10-16 22:21. | ABIERTA | Humano |
| Q5 | ¿Hay facturas o reglas compartidas por otros equipos? | No | Generar las propias. Si llegan compartidas, sumarlas al holdout, no al set con el que se calibra. | — | ASUMIDA | Orquestador, default de `docs/08` |
| Q6 | ¿Dónde se despliega el backend y hay Postgres? | No, si se acepta el SUPUESTO | Render + Postgres gestionado. Frontend en Vercel. | — | ASUMIDA | Orquestador (D003). El humano puede revertirla. |
| Q7 | ¿Los pendientes de aprobación reservan saldo del periodo? | No | No en v1. | — | ASUMIDA | Orquestador, default de `docs/08` |
| Q8 | ¿Hay que mostrar trazas de LangSmith a evaluadores externos? | No | Capturas y enlace si el plan lo permite. La UI no depende de LangSmith para explicar la decisión. | — | ASUMIDA | Orquestador, default de `docs/08` |
| Q9 | ¿La evaluación revisará el uso de IA? | No | Mantener este archivo y `docs/AI_USAGE_LOG.md` desde el inicio. | — | ASUMIDA | Orquestador, default de `docs/08` |
| Q10 | ¿R02 y R04 pueden quedar en el mismo monto? | No. El resto del paquete (nombre, FX, beneficiarios, umbrales JEV) sigue PROPUESTO y no bloquea. | Montos distintos. | Deben ser distintos. Quedaron umbral humano 3000 USD y límite por pago 5000 USD. | RESUELTA | Humano, 2026-10-16 22:21 |

Q10 quedó resuelta solo en los dos montos. Nombre, FX, beneficiarios y umbrales JEV siguen PROPUESTOS en `docs/PARAMETERS.md`.

## Supuestos heredados de `docs/08`

Siguen vigentes. Estado: ASUMIDA.

| ID | Supuesto | Estado |
|---|---|---|
| A1 | 36 h, no 48 | ASUMIDA |
| A2 | Una persona + agentes de código | ASUMIDA |
| A3 | El verificador solo sube severidad | ASUMIDA |
| A4 | Contratos en texto, términos con cita y confirmación humana | ASUMIDA |
| A5 | Compromisos bancarios fuera de v1; los cubre R12 | ASUMIDA |
| A6 | JEV verifica señales; no decide el pago | ASUMIDA |
| A7 | `decide()` es función pura | ASUMIDA |
| A8 | Explicaciones por plantilla | ASUMIDA |
| A9 | Frontend en v1 | ASUMIDA |
| A10 | UI y explicaciones en español | ASUMIDA |
| A11 | Ledger ordenado por fecha de recepción | ASUMIDA |

## Qué sigue sin poder verificarse (igual que `docs/08`)

- Formato real de la petición JEV.
- Límites reales de OpenCode.
- Versiones actuales de LangGraph, LangChain y LangSmith: mirar la documentación oficial antes de fijar dependencias en F0.
- Rúbrica real de Blinka: `docs/03` es una hipótesis.
