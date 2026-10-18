# 07 — Observabilidad y registro con LangSmith (puente al futuro frontend)

## Dos capas de registro (no confundir)
| Capa | Qué es | Fuente de verdad para | Quién la lee |
|---|---|---|---|
| **DecisionRecord** (nuestra BD) | Registro estructurado, inmutable, con explicación por plantillas | Decisión, motivo, auditoría | Frontend, evaluadores, finanzas |
| **Traza LangSmith** | Ejecución del grafo: nodos, prompts, llamadas a modelos, latencias, errores | Depuración, evaluación, costos | Desarrollador, juez técnico |

El registro guarda `langsmith_run_id` y una URL para saltar a la traza. La UI **no depende** de LangSmith para mostrar la decisión; LangSmith la enriquece.

## Configuración
Variables (documentar en `.env.example`, nunca valores reales en el repo):
- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY=...`
- `LANGSMITH_PROJECT=blinka-invoice-agent` (un proyecto por entorno: `-dev`, `-eval`, `-demo`)
- `LANGSMITH_ENDPOINT` solo si se usa un endpoint distinto.

## Qué se traza
- **Una traza por factura**, con cada nodo del grafo como sub-ejecución.
- **Metadatos y etiquetas** por traza: `invoice_id`, `decision`, `rules_version`, `model_extractor`, `model_verifier`, `jev_version`, `phase` (`dev|eval|demo`). En rutas HTTP (`POST /invoices`), también `owner_id` (mismo valor que el header `X-User-Id` de esa sesión, como tag adicional). En CLI/eval (`run_invoice_folder`) no se envía `owner_id`.
- Entradas/salidas de: `extract`, `jev_checks`, `verify`. Los nodos deterministas registran resultado y regla.
- Errores y desvíos fail-closed, con motivo (`error_tecnico`, `invariante_violado`, `baja_confianza`).
- Retroalimentación: tras la evaluación, adjuntar la etiqueta esperada y si acertó (`correct: true|false`) a la traza.

## Evaluación en LangSmith (opcional pero barato)
- Subir el set dorado como **dataset**; cada experimento = una corrida del agente.
- Evaluadores propios en código: `decision_matches_expected`, `unsafe_pay`, `reasons_match`.
- Sirve para comparar modelos, umbrales y prompts sin tocar el reporte oficial (`eval/reports/` sigue siendo la fuente de las cifras entregadas).

## Privacidad
- Solo datos sintéticos (I6). Aun así, evitar subir claves o datos de ejemplo que parezcan reales (nombres, cuentas, documentos de identidad); usar nombres y números inventados evidentes (`*.demo.test`, cuentas ficticias).
- Si el proyecto cambia a datos reales, enmascarar entradas/salidas antes de trazar. Está fuera de alcance de esta hackathon.

## Puente al frontend futuro
| Necesidad | Solución v1 | Evolución |
|---|---|---|
| Ver por qué se decidió | `/decisiones/{id}` desde `DecisionRecord` | igual |
| Ver cómo corrió el agente | enlace a la traza LangSmith | incrustar resumen de nodos vía API de LangSmith |
| Métricas de calidad | `/metricas` desde último reporte de eval | alimentar desde experimentos de LangSmith |
| Auditoría por periodo | filtros en `/decisiones` | exportación CSV |
| Retroalimentación humana | eventos de aprobación/rechazo | adjuntarlos como feedback a la traza para mejorar prompts y umbrales |

Contrato mínimo que el frontend debe poder asumir (no cambiar sin avisar):
`GET /decisions`, `GET /decisions/{id}` devuelve `DecisionRecord` completo con `trace.url`; todos los campos de texto en español; `id` estables.

## Bucles de retroalimentación (harness mínimo)
1. Decisión del agente → registro + traza.
2. Si es ESCALAR → humano aprueba/rechaza → **evento** guardado y adjuntado como feedback.
3. Discrepancias humano-agente (p. ej. humano aprueba algo que el agente frenó) → lista de revisión para ajustar reglas/umbrales.
4. Cambios de reglas generan nueva `rules_version`; nada se reescribe hacia atrás.
