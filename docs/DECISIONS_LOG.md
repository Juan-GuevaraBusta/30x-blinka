# Registro de decisiones de diseño

Dueño: Orquestador. Distinto de `docs/AI_USAGE_LOG.md`: aquí va la decisión; allí, que intervino una IA.

Estado de cada fila: VIGENTE hasta que se revierta.

| Fecha/hora | ID | Decisión | Alternativas | Motivo | Impacto (archivos/tareas) | Revierte a |
|---|---|---|---|---|---|---|
| 2026-10-16 20:11 -05 | D001 | Ejecutar los 8 roles como sombreros secuenciales. No crear `.cursor/agents/` todavía. | Ocho subagentes en paralelo | Una persona, ruta crítica secuencial, menos conflictos de archivos | `docs/AGENT_ROSTER.md`, `AGENTS.md` §5 | Crear los dos subagentes propuestos si el humano lo pide |
| 2026-10-16 20:11 -05 | D002 | Donde `pdf`, `pdf-reading`, `testing`, `diagrams` o `xlsx` no existen, la tarea queda en NINGUNA. No se sustituyen en silencio. | Usar `datasets`, `drawio-skill` o `python-testing-patterns` como si fueran esas skills | El encargo prohíbe inventar o cambiar una skill parecida sin decirlo | `docs/SKILLS_MAP.md`, T1.6, T3.2, T1.7 | — |
| 2026-10-16 20:11 -05 | D003 | Host de backend PROPUESTO: Render + Postgres gestionado. Sigue en SUPUESTO hasta confirmación. | Railway, Fly | El IDE tiene skills y MCP de Render. El stack deja los tres abiertos. | T4.9, Q6 en `docs/OPEN_QUESTIONS_STATUS.md` | Elegir Railway o Fly y no cargar las skills de Render |
| 2026-10-16 20:11 -05 | D004 | No usar `langchain-rag` ni `langfuse`. | RAG vectorial; migrar trazas a Langfuse | Contradicen `docs/02` (sin vector DB) y el stack LangSmith | F3, T3.4, T3.8 | Solo si el Orquestador aprueba un cambio de stack |
| 2026-10-16 20:11 -05 | D005 | El caso "violación solo detectable por el verificador" lleva dos etiquetas: motor con extracción verdadera, y e2e. | Una sola decisión esperada | G2 exige 100 % con extracción perfecta. Ese caso puede ser PAGAR en el motor y FRENAR en el e2e. | `docs/DATA_MANIFEST.md`, T1.7, T2.8, T3.6 | — |
| 2026-10-16 20:11 -05 | D006 | No se fusiona ningún rol. Invariantes, fail-closed y verificador conservan dueño. | Fundir QA con Rules Engine por compartir skill de tests | La regla de calidad de este encargo lo prohíbe. Pueden ir en paralelo sin compartir archivos. | T2.7, T3.6, T3.10 | — |
| 2026-10-16 20:11 -05 | D007 | `backend/app/config.py` es de Agent Graph. API no lo edita. | Archivo compartido | Un archivo, un dueño | T3.1, T4.2 | Mover la URL de base a otro módulo si estorba, con nota en este log |
| 2026-10-16 20:11 -05 | D008 | Tests partidos por dueño: `backend/tests/rules/`, `backend/tests/api/`, `backend/tests/gate/`, `backend/tests/adversarial/`. `final_gate` en `backend/app/gate/` (QA). | Una sola carpeta `backend/tests/` para todos | `docs/05` asigna T2.7 a QA y los tests de reglas a Rules Engine. Una carpeta común tendría dos dueños | `AGENTS.md` §5, T2.x, T3.10, T4.1, T5.3 | — |
