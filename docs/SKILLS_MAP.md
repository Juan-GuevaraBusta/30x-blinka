# Mapa de skills

Fecha: 2026-10-16. Dueño: Orquestador. Estado: HECHA como borrador de arranque. No abre la Fase 0.

Método: se listaron los `SKILL.md` de las raíces de abajo y se leyó el frontmatter (nombre y descripción) de cada uno. De las skills candidatas al núcleo se leyó el cuerpo. Una skill entra en una tarea solo si su descripción cubre esa tarea. Si no existe, la celda dice NINGUNA.

## Dónde se buscó

| Raíz | Estado | Notas |
|---|---|---|
| `~/.agents/skills/` | Existe | 35 skills. Ruta canónica de las que también aparecen como enlace. |
| `~/.claude/skills/` | Existe | 9 entradas. 8 son enlaces simbólicos a `~/.agents/skills/`. `graphify` es directorio real. |
| `~/.cursor/skills/` | Existe | `python-testing-patterns`, `aws-solution-architect`. |
| `~/.cursor/skills-cursor/` | Existe | Skills del producto Cursor (repo, hooks, subagentes, canvas). |
| `~/.cursor/plugins/cache/cursor-public/superpowers/` | Existe | TDD, verificación, planes, depuración, agentes paralelos. |
| `~/.cursor/plugins/cache/cursor-public/render/` | Existe | Deploy y Postgres en Render. |
| `~/.cursor/plugins/cache/cursor-public/postman/` | Existe | API, colecciones, mocks, datasets. |
| `~/.cursor/plugins/cache/cursor-public/langfuse/` | Existe | Observabilidad Langfuse. No es LangSmith. |
| `~/.cursor/plugins/cache/cursor-public/supabase/` | Existe | Supabase. El stack no lo usa. |
| `~/.claude/plugins/cache/marketingskills/` | Existe | Marketing. No aplican al núcleo. |
| Repo `30x-blinka/.cursor/skills/` y `.claude/skills/` | No existen | Cero skills de proyecto. |

Inventario: 163 nombres únicos. Ninguna skill inventada en este mapa.

## Skills que el mapa tentativo pedía y no existen

| Nombre buscado | Resultado |
|---|---|
| `pdf` | No existe |
| `pdf-reading` | No existe |
| `testing` | No existe |
| `diagrams` | No existe |
| `xlsx` | No existe |
| `financial-analyst` | No existe |
| `startup-financial-auditor` | No existe |

## Skills encontradas (candidatas al núcleo)

| Skill | Ruta | Se activa cuando | Produce | Límites / notas |
|---|---|---|---|---|
| `frontend-design` | `~/.agents/skills/frontend-design/SKILL.md` | UI nueva o rediseño: dirección visual, tipo, layout | Plan visual y UI con criterio propio | No cubre datos, API ni tests. Enlace gemelo en `~/.claude/skills/frontend-design`. |
| `ui-ux-pro-max` | `~/.agents/skills/ui-ux-pro-max/SKILL.md` | Diseñar, construir o revisar interfaces | Guía de UI, sistema visual, accesibilidad | Se solapa con `frontend-design`. No se asigna para no dar dos criterios visuales. |
| `web-design-guidelines` | `~/.agents/skills/web-design-guidelines/SKILL.md` | Revisión de UI, accesibilidad o UX | Informe de cumplimiento | No hay tarea de auditoría visual en el roadmap. No asignada. |
| `vercel-react-best-practices` | `~/.agents/skills/vercel-react-best-practices/SKILL.md` | Escribir o revisar React/Next por rendimiento | Patrones de rendimiento | No diseña la pantalla. PARCIAL junto a `frontend-design`. |
| `typescript-advanced-types` | `~/.agents/skills/typescript-advanced-types/SKILL.md` | Genéricos, condicionales, mapped types | Tipos TypeScript avanzados | Las pantallas no piden ese sistema de tipos. No asignada. |
| `langgraph-fundamentals` | `~/.agents/skills/langgraph-fundamentals/SKILL.md` | Cualquier código LangGraph: StateGraph, nodos, aristas, Command, errores | Grafo compilado | No cubre extracción, JEV, verificador ni LangSmith. |
| `python-testing-patterns` | `~/.cursor/skills/python-testing-patterns/SKILL.md` | Tests pytest, fixtures, mocks, TDD, property tests | Suite pytest | No es la skill `testing` de e2e web. No genera el reporte de eval. |
| `test-driven-development` | `~/.cursor/plugins/cache/cursor-public/superpowers/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/test-driven-development/SKILL.md` | Cualquier feature o bugfix, antes del código | Test que falla primero | Proceso. No define las reglas de negocio. |
| `verification-before-completion` | `~/.cursor/plugins/cache/cursor-public/superpowers/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/verification-before-completion/SKILL.md` | Antes de declarar algo hecho o un gate en verde | Evidencia de comandos, no una afirmación | No implementa el producto. |
| `verify-and-stop` | `~/.agents/skills/verify-and-stop/SKILL.md` | Validar sin ampliar alcance | Prueba mínima y parada | Se solapa con la anterior. Se usa la de superpowers en los gates. |
| `api-engineer` | `~/.cursor/plugins/cache/cursor-public/postman/0128d24704cfa71170d9df3b9fdc81959238be12/skills/api-engineer/SKILL.md` | Diseñar, implementar, documentar o probar una API | Contrato antes que código | Empuja colecciones Postman. No se crea workspace Postman sin aprobación del Orquestador. |
| `api-documentation` | misma raíz `postman/.../skills/api-documentation/SKILL.md` | Publicar documentación de API | Docs de API en ficheros | La usa `api-engineer` si hace falta. No es una segunda skill dueña. |
| `api-testing` | `postman/.../skills/api-testing/SKILL.md` | Correr tests de una colección | Resultados `pm.test` | No asignada: los tests de API van en pytest salvo que el Orquestador apruebe Postman. |
| `api-mocking` | `postman/.../skills/api-mocking/SKILL.md` | Backend falso desde OpenAPI | Mock local o en URL | El frontend puede mockear a mano desde OpenAPI. No asignada. |
| `datasets` | `postman/.../skills/datasets/SKILL.md` | Consultar CSV, JSON o SQL | Consultas sobre ficheros | No genera facturas ni hojas. No sustituye a `xlsx`. |
| `render-deploy` | `~/.cursor/plugins/cache/cursor-public/render/888d8627d41bebbe534e82d92cabfd2099e08e1f/skills/render-deploy/SKILL.md` | Desplegar en Render | `render.yaml` y enlace al dashboard | Solo si el host sigue siendo Render (SUPUESTO). |
| `render-web-services` | `render/.../skills/render-web-services/SKILL.md` | Servicio web: puerto, health check, TLS | Config de web service | Mismo SUPUESTO. Puerto `0.0.0.0:$PORT`. |
| `render-postgres` | `render/.../skills/render-postgres/SKILL.md` | Postgres gestionado en Render | Base y cadena de conexión | Mismo SUPUESTO. |
| `render-env-vars` | `render/.../skills/render-env-vars/SKILL.md` | Variables y secretos en Render | Env groups, sin secretos en el repo | Mismo SUPUESTO. |
| `drawio-skill` | `~/.agents/skills/drawio-skill/SKILL.md` | Diagrama draw.io, o convertir desde código | Fichero `.drawio` | Prefiere Mermaid si basta. `docs/02` ya tiene Mermaid. PARCIAL. |
| `sales-enablement` | `~/.claude/plugins/cache/marketingskills/marketing-skills/2.3.0/skills/sales-enablement/SKILL.md` | Collateral de ventas, incluido un guion de demo | Deck, one-pager o guion | Es marketing. Solo PARCIAL en el guion de 3 min. No entra al núcleo. |
| `create-subagent` | `~/.cursor/skills-cursor/create-subagent/SKILL.md` | Crear un subagente en `.cursor/agents/` o `~/.cursor/agents/` | Markdown con `name` y `description` | El IDE sí puede definir subagentes. Este turno no los crea. |
| `dispatching-parallel-agents` | `superpowers/.../skills/dispatching-parallel-agents/SKILL.md` | Dos o más tareas independientes | Reparto sin estado compartido | Solo la ventana de F4, y T2.7 contra T2.3 si el contrato ya está congelado. |
| `finishing-a-development-branch` | `superpowers/.../skills/finishing-a-development-branch/SKILL.md` | Implementación completa: merge, PR o limpieza | Opciones de cierre | PARCIAL en T6.3. No abre un PR sola. |
| `lean-build` | `~/.agents/skills/lean-build/SKILL.md` | Feature con riesgo de sobreconstruir | Corte explícito al cumplir la aceptación | Proceso. No es dueña de una tarea. |
| `systematic-debugging` | `superpowers/.../skills/systematic-debugging/SKILL.md` | Bug, test rojo o comportamiento raro | Causa antes del parche | Bajo demanda. No hay tarea preventiva. |
| `investigate-first` | `~/.agents/skills/investigate-first/SKILL.md` | Fallo ambiguo | Hipótesis ordenadas por evidencia | Bajo demanda. |
| `surgical-patch` | `~/.agents/skills/surgical-patch/SKILL.md` | Bugfix estrecho | Parche mínimo con test | Bajo demanda. |
| `writing-plans` | `superpowers/.../skills/writing-plans/SKILL.md` | Spec de varios pasos, antes de codar | Plan escrito | El roadmap ya está en `docs/05`. No se reescribe. |
| `brainstorming` | `superpowers/.../skills/brainstorming/SKILL.md` | Antes de trabajo creativo | Diseño acordado | `frontend-design` ya trae su pase de diseño. No se apila. |

## Mapa tarea → skill

| Tarea | Skill(s) | Cobertura (TOTAL/PARCIAL/NINGUNA) | Por qué |
|---|---|---|---|
| T0.1 | NINGUNA | NINGUNA | Ninguna skill crea el esqueleto Python/pytest/ruff del repo. |
| T0.2 | NINGUNA | NINGUNA | El protocolo está en `AGENTS.md` §4. `find-skills` sirve para instalar skills nuevas, no para este inventario. |
| T0.3 | NINGUNA | NINGUNA | No hay skill de smoke test para OpenCode, JEV o LangSmith. |
| T0.4 | NINGUNA | NINGUNA | Es una decisión del humano. |
| T0.5 | NINGUNA | NINGUNA | Es un registro. Este turno ya dejó la primera fila. |
| T1.1 | NINGUNA | NINGUNA | JSON de empresa ficticia. Ninguna skill lo especifica. |
| T1.2 | NINGUNA | NINGUNA | `rules.json` sale de `docs/04`, no de una skill. |
| T1.3 | NINGUNA | NINGUNA | Pydantic v2 no tiene skill propia. |
| T1.4 | NINGUNA | NINGUNA | Contratos en texto. No hay skill de redacción de contratos sintéticos. |
| T1.5 | NINGUNA | NINGUNA | Tabla FX fija. `xlsx` no existe. |
| T1.6 | NINGUNA | NINGUNA | `pdf` y `pdf-reading` no existen. No se sustituyen. |
| T1.7 | NINGUNA | NINGUNA | `xlsx` no existe. `datasets` consulta JSON; no etiqueta el set dorado. |
| T2.1 | `test-driven-development`; `python-testing-patterns` | TOTAL | Feature con tests primero y pytest. |
| T2.2 | `test-driven-development`; `python-testing-patterns` | TOTAL | Igual. |
| T2.3 | `test-driven-development`; `python-testing-patterns` | TOTAL | La skill de pytest pide casos y mocks; TDD pide el test antes. |
| T2.4 | `test-driven-development`; `python-testing-patterns` | TOTAL | Igual. |
| T2.5 | `test-driven-development`; `python-testing-patterns` | TOTAL | `decide()` es código puro con tests. |
| T2.6 | `test-driven-development`; `python-testing-patterns` | TOTAL | Plantillas y esquema se fijan con tests. |
| T2.7 | `test-driven-development`; `python-testing-patterns` | TOTAL | La skill cita property-based testing. Hypothesis entra por ahí. |
| T2.8 | `python-testing-patterns` | PARCIAL | Cubre un test de integración. No describe un runner de set dorado. |
| T3.1 | NINGUNA | NINGUNA | `get_llm(role)` y el plan B no están en la skill de LangGraph. |
| T3.2 | NINGUNA | NINGUNA | `pdf-reading` no existe. |
| T3.3 | NINGUNA | NINGUNA | No hay skill de extracción estructurada. |
| T3.4 | NINGUNA | NINGUNA | No hay skill de extracción de cláusulas. |
| T3.5 | NINGUNA | NINGUNA | JEV no aparece en ninguna skill. |
| T3.6 | NINGUNA | NINGUNA | El verificador es un contrato de `docs/02`, no LangGraph. |
| T3.7 | `langgraph-fundamentals` | TOTAL | StateGraph, nodos, aristas, checkpointer y errores. |
| T3.8 | NINGUNA | NINGUNA | LangSmith no tiene skill. `langfuse` es otro producto: no se usa. |
| T3.9 | NINGUNA | NINGUNA | Una CLI no está cubierta por las skills encontradas. |
| T3.10 | `python-testing-patterns` | TOTAL | Mock de dependencias y fallo de servicios. |
| T4.1 | `api-engineer` | PARCIAL | Cubre diseñar e implementar la API y el contrato. El flujo Postman queda fuera salvo aprobación. |
| T4.2 | NINGUNA | NINGUNA | SQLAlchemy no tiene skill. `supabase` sería otro proveedor. |
| T4.3 | `frontend-design`; `vercel-react-best-practices` | TOTAL; PARCIAL | Diseño de la pantalla; la segunda solo rendimiento. |
| T4.4 | `frontend-design`; `vercel-react-best-practices` | TOTAL; PARCIAL | Igual. |
| T4.5 | `frontend-design`; `vercel-react-best-practices` | TOTAL; PARCIAL | Igual. |
| T4.6 | `frontend-design`; `vercel-react-best-practices` | TOTAL; PARCIAL | Igual. |
| T4.7 | `frontend-design`; `vercel-react-best-practices` | TOTAL; PARCIAL | Igual. |
| T4.8 | `frontend-design` | PARCIAL | Solo la pantalla de subida. El endpoint ya es T4.1. |
| T4.9 | `render-deploy`; `render-web-services`; `render-postgres`; `render-env-vars` | PARCIAL | Cubren el backend si el host es Render. No hay skill de deploy en Vercel. |
| T5.1 | NINGUNA | NINGUNA | El reporte de métricas no es una suite pytest. |
| T5.2 | NINGUNA | NINGUNA | Calibrar umbrales es una regla de `docs/06`, no una skill. |
| T5.3 | `python-testing-patterns` | PARCIAL | Los casos pueden ser tests. La skill no habla de adversariales de prompt. |
| T5.4 | NINGUNA | NINGUNA | Lectura ciega por una persona. |
| T5.5 | `drawio-skill` | PARCIAL | Solo si el README necesita un `.drawio`. La tabla afirmación→evidencia no tiene skill. |
| T5.6 | `verification-before-completion` | TOTAL | Probar cada afirmación antes de darla por cierta. |
| T6.1 | `sales-enablement` | PARCIAL | Menciona guiones de demo, en clave de ventas. |
| T6.2 | NINGUNA | NINGUNA | `video` genera vídeo de marketing con herramientas de IA, no una grabación de la demo. |
| T6.3 | `finishing-a-development-branch` | PARCIAL | Ayuda a cerrar la rama. El etiquetado lo decide el humano. |
| G0 | `verification-before-completion` | TOTAL | El gate se cierra con salida de las tres llamadas, no con un relato. |
| G1 | `verification-before-completion` | TOTAL | Igual, contra el checklist de `docs/05`. |
| G2 | `verification-before-completion` | TOTAL | Igual. |
| G3 | `verification-before-completion` | TOTAL | Igual. |
| G4 | `verification-before-completion` | TOTAL | Igual. |
| G5 | `verification-before-completion` | TOTAL | Igual. |
| G6 | `verification-before-completion` | TOTAL | Igual. |

## Skills de proceso (no dueñas de tarea)

Se leen cuando el caso aparece. No sustituyen a la skill de la fila.

| Skill | Cuándo |
|---|---|
| `lean-build` | Al implementar T3.7 o la UI, para cortar alcance. |
| `dispatching-parallel-agents` | Solo en las ventanas de `docs/AGENT_ROSTER.md`. |
| `systematic-debugging`, `investigate-first`, `surgical-patch` | Cuando un test falle. |
| `create-subagent` | Si el humano pide crear los subagentes propuestos. |

## Skills descartadas

| Skill o familia | Motivo |
|---|---|
| `pdf`, `pdf-reading`, `testing`, `diagrams`, `xlsx` | No están en el IDE. |
| `financial-analyst`, `startup-financial-auditor` | No están. Aunque estuvieran, `AGENTS.md` las saca del núcleo. |
| `langchain-rag` | Construye RAG con embeddings y vector store. `docs/02` lo prohíbe en v1. |
| `langfuse`, `migrate-to-langfuse` | Otro producto. Migrar sacaría LangSmith, que es el stack. |
| `deep-agents-core`, `deep-agents-memory`, `lca-deepagents` | Harness Deep Agents. El grafo es LangGraph lineal. |
| `graphify` | Preguntas al grafo del repo. No hay tarea que lo exija. |
| `supabase`, `supabase-postgres-best-practices` | El Postgres previsto no es Supabase. |
| `aws-solution-architect`, `aws-architecture-diagram` | No hay AWS en el stack. |
| Resto de Render (`render-cron-jobs`, workers, Redis, discos, Docker, dominios, escala, workflows, Heroku, MCP, CLI, debug, monitor, networking, private, static, blueprints) | No hay cron, colas, Redis ni Docker en v1. `render-blueprints` solo si `render-deploy` lo pide. |
| Resto de Postman (bootstrap, monitoring, flows, performance, ci, variables, simulation, discovery, collection-schema, ai-readiness, postman-mcp, marketplace, release) | No se adopta Postman sin aprobación. |
| Marketing (unas 40 skills bajo `marketingskills/`, salvo el uso PARCIAL de `sales-enablement` en T6.1) | SEO, ads, email, pricing, churn. Fuera del producto. |
| `video`, `image`, `copywriting` | Producen contenido de marketing, no la demo ni la UI de facturas. |
| Caveman y Cavecrew (`caveman`, `ultracave`, `megacave`, `caveman-*`, `cavecrew`) | Voz o delegación del IDE. No construyen el agente pagador. |
| Skills de producto Cursor (`automate`, `canvas`, `create-hook`, `create-rule`, `create-skill`, `sdk`, `loop`, `shell`, `review`, `review-bugbot`, `review-security`, `split-to-prs`, `autopilot`, `onboard`, `new-repo`, `share`, `origin`, `goal`, `statusline`, `rename-chat`, `update-cursor-settings`, `update-cli-config`, `migrate-to-skills`, `writing-skills`, `skill-creator`, `find-skills`) | Operan el IDE, no el dominio. |
| `using-superpowers`, `executing-plans`, `writing-plans`, `brainstorming`, `requesting-code-review`, `receiving-code-review`, `using-git-worktrees`, `subagent-driven-development`, `safe-refactor`, `migration` | Proceso genérico. El plan ya existe. No hay migración. |
| `ui-ux-pro-max`, `web-design-guidelines`, `typescript-advanced-types`, `api-mocking`, `api-testing`, `datasets`, `verify-and-stop` | Existen y se evaluaron. No se asignan: solapan a una skill ya elegida o no cubren una tarea. |
