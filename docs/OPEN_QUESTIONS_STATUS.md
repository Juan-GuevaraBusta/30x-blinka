# Estado de preguntas abiertas

Dueño: Orquestador. Fuente: `docs/08_OPEN_QUESTIONS_AND_ASSUMPTIONS.md`, más las que salieron al armar el roster.

Fecha: 2026-10-16. Ninguna respuesta humana todavía.

## Preguntas

| ID | Pregunta | Bloqueante | Propuesta por defecto | Respuesta | Estado (ABIERTA\|RESUELTA\|ASUMIDA) | Responde |
|---|---|---|---|---|---|---|
| Q1 | ¿Cómo se accede a JEV: clave directa de TypeSafe, Vercel AI Gateway, Cloudflare Workers AI o AI/ML API? ¿Cuál es el formato exacto de la petición? | Sí, para T0.3 y F3 | Probar primero una vía sin lista de espera. Si no hay acceso, plan B: `DecisionClient` con LLM de salida estructurada. | POR COMPLETAR | ABIERTA | Humano |
| Q2 | ¿Qué modelos expone OpenCode, hablan el formato OpenAI, hay salida estructurada y visión, y qué presupuesto de llamadas hay? | Sí, para T0.3 y F3 | `get_llm(role)` con extractor barato y verificador fuerte, por variables de entorno. | POR COMPLETAR | ABIERTA | Humano |
| Q3 | ¿Los `on_fail` de `docs/04` son los que queremos? En particular, beneficiario nuevo = FRENAR, no ESCALAR. | Sí para etiquetar T1.7. No impide T0.1. | Dejar los defaults de `docs/PARAMETERS.md` y documentarlos en `rules.json`. | POR COMPLETAR | ABIERTA | Humano |
| Q4 | ¿Hay una segunda persona para la segunda lectura de etiquetas y para la lectura ciega de 5 registros? | No para codar. Sí para la calidad de G1 y T5.4. | La misma persona hace una segunda pasada en otro momento. No es independiente. Se anota esa limitación en el reporte. | POR COMPLETAR | ABIERTA | Humano |
| Q5 | ¿Hay facturas o reglas compartidas por otros equipos? | No | Generar las propias. Si llegan compartidas, sumarlas al holdout, no al set con el que se calibra. | — | ASUMIDA | Orquestador, default de `docs/08` |
| Q6 | ¿Dónde se despliega el backend y hay Postgres? | No, si se acepta el SUPUESTO | Render + Postgres gestionado. Frontend en Vercel. | — | ASUMIDA | Orquestador (D003). El humano puede revertirla. |
| Q7 | ¿Los pendientes de aprobación reservan saldo del periodo? | No | No en v1. | — | ASUMIDA | Orquestador, default de `docs/08` |
| Q8 | ¿Hay que mostrar trazas de LangSmith a evaluadores externos? | No | Capturas y enlace si el plan lo permite. La UI no depende de LangSmith para explicar la decisión. | — | ASUMIDA | Orquestador, default de `docs/08` |
| Q9 | ¿La evaluación revisará el uso de IA? | No | Mantener este archivo y `docs/AI_USAGE_LOG.md` desde el inicio. | — | ASUMIDA | Orquestador, default de `docs/08` |
| Q10 | ¿Se confirman los parámetros PROPUESTOS de `docs/PARAMETERS.md` (empresa, límites ambos en 3000, beneficiarios, FX, umbrales JEV)? | Sí para dar por cerrados los números. Se puede avanzar con ellos marcados PROPUESTO. | Usar la tabla tal cual. R02 y R04 quedan en el mismo monto. | POR COMPLETAR | ABIERTA | Humano |

Q10 agrupa la confirmación del paquete. No cambia invariantes.

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
