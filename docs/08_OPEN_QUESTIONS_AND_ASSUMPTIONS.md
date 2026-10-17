# 08 — Supuestos y preguntas abiertas

Resolver los marcados **[BLOQUEANTE]** antes de iniciar F1. Los demás se asumen por defecto si no hay respuesta.

## Supuestos actuales
| ID | Supuesto | Fuente |
|---|---|---|
| A1 | Tiempo total: **36 h** (el análisis previo hablaba de 48 h; manda la cifra más reciente) | indicación del equipo |
| A2 | Equipo de **una persona** + agentes de código | conversación previa |
| A3 | El verificador valida que lo hecho concluye y concuerda con lo establecido, y **solo puede subir severidad** | conversación |
| A4 | Contratos de proveedores son **texto firmado**; se extraen a términos estructurados con cita y confirmación humana | conversación |
| A5 | Compromisos bancarios y pendientes de stakeholders **no entran** en v1; se cubren con `manual_blocks` (R12) | alcance del reto |
| A6 | JEV se usa como verificador de señales tipadas, no como decisor del pago | diseño |
| A7 | La decisión final es función pura de los chequeos; los LLM no autorizan | restricción de seguridad |
| A8 | Explicaciones por plantillas; LLM opcional solo para pulir | restricción de explicabilidad |
| A9 | Frontend requerido en v1 porque el entregable exige una pantalla; LangSmith alimenta una versión futura más rica | entregable |
| A10 | UI y explicaciones en español | contexto del equipo |
| A11 | Facturas ordenadas por fecha de recepción para el ledger | decisión de diseño |

## Preguntas abiertas
| ID | Pregunta | Impacto | Propuesta por defecto |
|---|---|---|---|
| Q1 **[BLOQUEANTE]** | ¿Cómo se accede a JEV: clave directa de TypeSafe (lista de espera), Vercel AI Gateway, Cloudflare Workers AI o AI/ML API? ¿Cuál es el formato exacto de petición? | F0, F3 | Probar la vía sin espera primero; plan B con LLM estructurado |
| Q2 **[BLOQUEANTE]** | ¿Qué modelos expone la API de OpenCode, ¿es compatible con el formato OpenAI?, ¿soporta salida estructurada y visión? ¿Presupuesto aproximado de llamadas? | F0, F3 | Abstraer con `get_llm(role)`; extractor barato + verificador fuerte |
| Q3 | ¿Los `on_fail` por defecto de `04` (p. ej. beneficiario nuevo → FRENAR) son los esperados por Blinka, o un beneficiario nuevo debería ser ESCALAR? | etiquetas del set dorado | Configurable; documentar la política elegida en `rules.json` |
| Q4 | ¿Se trabaja realmente solo? ¿Hay alguien para la lectura ciega y la segunda revisión de etiquetas? | calidad de eval | Pedir ayuda puntual a una persona externa |
| Q5 | ¿Hay facturas/reglas compartidas por otros equipos o por la organización? | tiempo en F1 | Generar las propias; sumar compartidas al holdout si llegan |
| Q6 | ¿Dónde se despliega el backend (Railway/Render/Fly) y hay Postgres gratuito disponible? | F4 | Postgres gestionado gratuito; backend en Render o Railway |
| Q7 | ¿Los pendientes de aprobación deben reservar saldo del periodo? | R03/R07 | No en v1 (documentado) |
| Q8 | ¿Se espera mostrar las trazas de LangSmith a evaluadores externos (acceso/permisos)? | demo | Capturas y enlace público si el plan lo permite |
| Q9 | ¿La entrevista o evaluación incluirá revisión del uso de IA (transcripciones)? | trazabilidad | Mantener `AI_USAGE_LOG.md` desde el inicio |

## Cosas que no verifiqué (la IA que lea esto debe comprobarlas)
- El formato exacto de la petición/respuesta de JEV; solo confirmé que existen preguntas tipadas (sí/no, elección, puntaje) y varias vías de acceso.
- Compatibilidad y límites de la API de OpenCode.
- Versiones actuales de LangGraph/LangChain/LangSmith y sus APIs (cambian rápido): consultar la documentación oficial antes de fijar dependencias.
- Rúbrica real de Blinka: lo de `03` es una inferencia.
