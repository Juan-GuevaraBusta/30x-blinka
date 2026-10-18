# 05 — Fases y roadmap (36 h)

Cada tarea tiene ID, dueño (ver `AGENTS.md §5`) y dependencias. Casilla `[ ]` = pendiente. **Una fase no se cierra sin su gate.** Los tiempos son objetivos, no promesas.

## Vista general
| Fase | Horas | Resultado | Gate |
|---|---|---|---|
| F0 Arranque | 0–2 | Repo, skills, APIs probadas | G0 |
| F1 Especificación y datos | 2–8 | Contratos congelados, set sintético, set dorado | G1 |
| F2 Núcleo determinista | 8–16 | Motor de reglas, registro, invariantes | G2 |
| F3 Agente | 16–24 | Grafo e2e con JEV, verificador, LangSmith | G3 |
| F4 API + Frontend | 24–31 | Reglas, decisiones, aprobaciones, desplegado | G4 |
| F5 Evaluación y blindaje | 31–35 | Métricas, adversariales, guía de jueces | G5 |
| F6 Demo y entrega | 35–36 | Guion, respaldo, congelar | G6 |

Ruta crítica: **F1 (datos y contratos) → F2 (motor) → F3 (grafo) → F4 (UI) → F5**. El motor determinista bloquea todo lo demás; la UI puede avanzar en paralelo desde el esquema OpenAPI.

---
## F0 — Arranque (h0–2)
- [x] **T0.1** Crear repo con estructura de `AGENTS.md §8`, `.env.example`, `ruff`, `pytest` mínimo. *(Orquestador)*
- [x] **T0.2** Descubrir skills del IDE y escribir `docs/SKILLS_MAP.md`. *(Orquestador)*
- [x] **T0.3** Smoke test de 3 accesos con una llamada cada uno: modelo extractor/verificador (OpenCode), JEV (vía elegida), LangSmith (una traza). *(Agent Graph)*
- [x] **T0.4** Resolver supuestos bloqueantes de `08` con el humano. *(Orquestador)*
- [x] **T0.5** Crear `docs/AI_USAGE_LOG.md` y primera entrada.

**G0:** las tres APIs responden; si JEV no está accesible, se activa el plan B (`DecisionClient` con LLM estructurado) y se anota.

## F1 — Especificación y datos (h2–8)
- [x] **T1.1** Empresa ficticia: `company.json` (departamentos, presupuestos, moneda base). *(Spec & Data)*
- [x] **T1.2** `rules.json` + esquema de reglas según `04 §2`. *(Spec & Data)*
- [x] **T1.3** Modelos Pydantic: `Extraction`, `Rules`, `CheckResult`, `JevSignal`, `VerifierReport`, `DecisionRecord`, `HumanEvent`. **Congelar v1.** *(Spec & Data)*
- [x] **T1.4** 6–8 contratos de proveedores en texto, con cláusulas numeradas y alguna ambigüedad deliberada. *(Spec & Data)*
- [x] **T1.5** `fx.json` con tasas fijas y fecha. *(Spec & Data)*
- [x] **T1.6** Generador reproducible de facturas sintéticas: ~30 de desarrollo + ~10 holdout, en PDF, imagen, correo y chat; layouts distintos. *(Spec & Data; skills `pdf`)*
- [x] **T1.7** `golden.json`: por factura, decisión esperada, regla(s) esperadas, motivo y **extracción verdadera** (para probar el motor aislado). Segunda revisión del etiquetado. *(Spec & Data)*

**G1:** esquemas congelados; cada regla R01–R13 tiene ≥1 caso en el set; holdout guardado aparte y no consultado; etiquetas revisadas dos veces. **Cerrado 2026-10-16 (D015).**

## F2 — Núcleo determinista (h8–16)
- [x] **T2.1** Normalización (beneficiario, moneda, fechas, montos con formatos regionales). *(Rules Engine)*
- [x] **T2.2** Conversión FX con registro de tasa. *(Rules Engine)*
- [x] **T2.3** Reglas R01–R13 como funciones puras con tests por regla (casos OK, falla, indeterminado). *(Rules Engine)*
- [x] **T2.4** Ledger (periodo, presupuesto, duplicados) con orden determinista. *(Rules Engine)*
- [x] **T2.5** `decide()` pura: precedencia + indeterminado→ESCALAR. *(Rules Engine)*
- [x] **T2.6** Registro y plantillas de explicación (`04 §5–6`). *(Rules Engine)*
- [x] **T2.7** `final_gate` / invariant checker + property tests (hypothesis) para I1–I4. *(QA & Eval)*
- [x] **T2.8** Runner que alimenta la **extracción verdadera** del set dorado al motor y compara con lo esperado. *(QA & Eval)*

**G2:** con extracción perfecta, 100 % de decisiones correctas en dev; `unsafe_pay = 0`; todos los invariantes con prueba verde. **Cerrado 2026-10-17 (D028).**

## F3 — Agente (h16–24)
- [x] **T3.1** `get_llm(role)` por variables de entorno y `DecisionClient` (JEV + plan B). *(Agent Graph)*
- [x] **T3.2** Ingesta: texto PDF → OCR → email/chat → texto normalizado. *(Agent Graph; skills `pdf-reading`)*
- [x] **T3.3** Extractor con salida estructurada y `source_span` por campo; prompt que trata el documento como dato. *(Agent Graph)*
- [x] **T3.4** Ingesta de contratos → términos + cita de cláusula + flag `confirmed`. *(Agent Graph)*
- [x] **T3.5** Nodo JEV con preguntas J1–J7 y umbrales de configuración. *(Agent Graph)*
- [x] **T3.6** Verificador (esquema de salida fijo; solo sube severidad). *(Agent Graph)*
- [x] **T3.7** Grafo LangGraph de `02` con ramas fail-closed y checkpointer. *(Agent Graph)*
- [x] **T3.8** LangSmith: trazas por factura con metadatos y `run_id` guardado en el registro (`07`). *(Agent Graph)*
- [x] **T3.9** CLI: procesa una carpeta de facturas y escribe `decisions.json`. *(Agent Graph)*
- [x] **T3.10** Tests con fakes: LLM que falla, JEV que expira, JSON inválido → siempre ESCALAR. *(QA & Eval)*

**G3:** e2e sobre el set de desarrollo con `unsafe_pay = 0`; línea base de autonomía medida y reportada; trazas visibles en LangSmith.

## F4 — API + Frontend (h24–31)
- [x] **T4.1** Endpoints: `POST /invoices`, `GET /decisions`, `GET /decisions/{id}`, `GET|PUT /rules`, `POST /decisions/{id}/approve|reject`, `GET /metrics`. OpenAPI publicado. *(API)*
- [x] **T4.2** Persistencia SQLAlchemy (SQLite dev / Postgres prod) y *seed* reproducible. *(API)*
- [x] **T4.3** UI `/reglas`: edición con validación y versionado. *(Frontend; skill `frontend-design`)*
- [x] **T4.4** UI `/decisiones`: tabla filtrable (Pagadas / Frenadas / Pendientes) con motivo en una línea. *(Frontend)*
- [x] **T4.5** UI `/decisiones/[id]`: datos leídos, chequeos OK/FALLA con regla y cláusula, explicación, enlace a la traza. *(Frontend)*
- [x] **T4.6** UI `/aprobaciones`: cola con aprobar/rechazar y motivo obligatorio. *(Frontend)*
- [x] **T4.7** UI `/metricas`: autonomía y pagos indebidos (cero) del último eval. *(Frontend)*
- [x] **T4.8** Subir factura desde la UI para demo en vivo. *(Frontend + API)*
- [x] **T4.9** Despliegue: Vercel (front) + backend + Postgres; CORS y variables. *(API/Frontend)*

**G4:** desde una URL pública se puede editar una regla, procesar una factura y ver la decisión explicada. Contrato: `docs/G4_SPEC.md` (D040).

## F5 — Evaluación y blindaje (h31–35)
- [ ] **T5.1** Eval completa dev + holdout; reporte en `eval/reports/latest.md`. *(QA & Eval)*
- [ ] **T5.2** Calibrar umbrales de JEV solo con dev; reportar holdout sin ajustar. *(QA & Eval)*
- [ ] **T5.3** Casos adversariales: inyección de instrucciones, montos con formato extraño, moneda desconocida, documento ilegible, duplicado con PDF distinto, API caída. Todos deben terminar en no-PAGAR. *(QA & Eval)*
- [ ] **T5.4** Prueba de explicabilidad: lectura ciega de 5 registros por alguien ajeno al código. *(QA & Eval)*
- [ ] **T5.5** `README.md`, `JUDGE_GUIDE.md` (afirmación → evidencia), ejemplos en `docs/examples/records/`. *(Docs & Judge)*
- [ ] **T5.6** Revisión final de afirmaciones: borrar lo que no tenga evidencia. *(Docs & Judge)*
- [x] **T5.7** Unificar el import del backend para que `cd backend && pytest` y la CLI de eval corran. *(Agent Graph)*
- [x] **T5.8** Serializar la decisión dependiente del ledger para cumplir el límite por periodo bajo concurrencia. *(API)*
- [x] **T5.9** Exigir clave de administrador en los endpoints que mutan y validar el aprobador. *(API)*
- [ ] **T5.10** Encadenar los registros de decisión con hash y exponer su verificación. *(Rules Engine)*
- [ ] **T5.11** Dinero como `Decimal` en montos y comparaciones de límite. *(Rules Engine)*

**G5:** `unsafe_pay = 0` en dev, holdout y adversariales; reporte commiteado; README verificable; T5.8 (sin pagos fuera de reglas por concurrencia) y T5.9 (endpoints mutantes con acceso mínimo) cerradas.

## F6 — Demo y entrega (h35–36)
- [ ] **T6.1** Guion de 3 min: factura normal pagada → duplicado frenado → monto alto escalado → aprobación humana → registro y traza → métricas.
- [ ] **T6.2** Video de respaldo y *seed* para reiniciar la demo.
- [ ] **T6.3** Etiqueta de versión, congelar rama, lista de entrega.
- [x] **T6.4** CI con gate de eval (`unsafe_pay`) y CodeQL. *(Orquestador)*
- [ ] **T6.5** Licencia, política de seguridad y guía de contribución. *(Docs & Judge)*
- [ ] **T6.6** Página de estado única y sincronizar el roadmap con el tablero. *(Orquestador)*

**G6:** demo ensayada una vez completa; repo congelado.

---
## Líneas de corte (si vamos tarde)
Sacrificar **en este orden**; todo lo anterior a "nunca cortar" se puede recortar:
1. OCR de imágenes (mantener PDF con texto, email y chat).
2. `/metricas` en la UI (queda el reporte en `eval/`).
3. Subir factura desde la UI (T4.8): el demo usa facturas precargadas.
4. Pulido de explicaciones por LLM (nunca estuvo en el camino crítico).
5. Verificador LLM → queda el `final_gate` determinista.
6. JEV → plan B detrás de `DecisionClient`.

**Nunca cortar:** motor determinista, invariantes y sus tests, registro explicable, pantalla de reglas mínima, `unsafe_pay = 0` como gate.

## Puntos de control de ritmo
| Hora | Debe existir |
|---|---|
| 8 | G1 cerrado: datos y esquemas congelados |
| 16 | G2 cerrado: el motor acierta 100 % con extracción perfecta |
| 24 | G3 cerrado: e2e con trazas y línea base |
| 31 | G4 cerrado: demo en URL pública |
| 35 | G5 cerrado: métricas y guía de jueces |
Si en un punto de control falta algo, aplicar la línea de corte **en ese momento**, no al final.

## Riesgos de tiempo (los 3 mayores)
1. **Calidad del set dorado:** etiquetas ambiguas distorsionan autonomía. Mitigación: dos lecturas y reglas por defecto escritas en `04`.
2. **Acceso a JEV:** puede tardar o diferir del formato esperado. Mitigación: G0 y plan B.
3. **Despliegue tardío:** dejar el deploy para el final es el riesgo clásico. Mitigación: desplegar un "hola mundo" conectado en F0/F1 y redeplegar en cada gate.
