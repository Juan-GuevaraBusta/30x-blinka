# 03 — Ingeniería inversa de jueces-agente en hackathons

> Objetivo: anticipar cómo un evaluador automatizado (o un humano apoyado por uno) inspeccionaría nuestro repo y diseñar el proyecto para que la evidencia sea fácil de encontrar y verificar.
> **Límite:** no conocemos la rúbrica interna de Blinka. Lo siguiente se infiere de casos públicos análogos. Tratar como hipótesis, no como hechos.

## Fuentes revisadas
1. **Devfolio, "The Discerning Machine"** (mayo 2026): auditor agéntico para el hackathon Push to Prod.
2. **HackerRank Orchestrate** (24 h, mayo 2026): repo inicial con `AGENTS.md`, entrevista con un juez-IA y evaluación por varias dimensiones.
3. **Verdict (lablab.ai, Milan AI Week 2026)**: agente que puntúa envíos contra una rúbrica en lenguaje natural con pesos.
4. **AI Judge (ETHGlobal)** y **Ax Bot (OpenClaw)**: evaluación multi-modelo con rúbricas personalizables y plantillas de prompts de juez.

## Hallazgos (en palabras propias) y su implicación

### Devfolio — el repo es la evidencia
- El agente recibe el texto del envío y **recorre el repositorio con herramientas de lectura/búsqueda**, verificando afirmación por afirmación. El hallazgo central son los desajustes entre lo que se dice y lo que el código hace, con citas a archivo y línea.
- Pipeline en dos fases: un modelo caro lee y redacta la auditoría; uno barato la convierte en JSON; **el puntaje agregado lo calcula el código**, no el modelo.
- Jerarquía de confianza: código → auditoría → JSON → agregado → decisión humana. Cuanto más lejos del código, menos se confía.
- Un README muy pulido solo aumenta la lista de afirmaciones a comprobar.
- Los fallos típicos son de búsqueda: el juez miró en el lugar equivocado o no exploró todo.
- La rúbrica ambigua deja al agente sustituir su propia noción de calidad; una rúbrica buena se parece a una especificación.

**Implicaciones para nosotros**
| Hallazgo | Decisión de diseño | Artefacto |
|---|---|---|
| Se contrastan afirmaciones con código | Cada afirmación del README apunta a un archivo, prueba o reporte | `JUDGE_GUIDE.md` (tabla afirmación → evidencia) |
| El agregado lo calcula código | Nuestra decisión es función pura; el LLM no decide | `rules/decide.py` + tests |
| Se premia la búsqueda fácil | Estructura de repo predecible y nombres literales (`rules/`, `verifier/`, `eval/`) | `AGENTS.md §8` |
| Fallos por mala exploración | Un único punto de entrada para jueces: qué ejecutar y qué leer | `JUDGE_GUIDE.md` |
| Claims inflados se penalizan | No prometer lo que no está (p. ej. "detección de fraude", "pagos reales") | revisión final de README |

### HackerRank Orchestrate — varias dimensiones y trazabilidad del uso de IA
- Se puntúa **diseño del agente**, **exactitud de salida**, **entrevista con un juez-IA** y **fluidez con IA** vista en la transcripción del trabajo. El repo inicial incluye un `AGENTS.md` y pide un README dentro de la carpeta del agente.
- La entrevista pregunta por enfoque, decisiones y uso de IA.

**Implicaciones**
- Mantener `docs/AI_USAGE_LOG.md` (una línea por decisión) y estar listos para justificar cada elección de diseño.
- README con instalación/ejecución en minutos; `AGENTS.md` presente y coherente con el código.
- Preparar respuestas a: ¿por qué el LLM no decide?, ¿qué pasa si JEV falla?, ¿cómo evitan una inyección en la factura?, ¿cómo midieron autonomía?

### Verdict y similares — rúbrica con pesos y veredicto por criterio
- Puntúan por criterio con pesos y generan una frase de veredicto; algunos muestran el razonamiento en vivo y dan enlace permanente por decisión.

**Implicaciones**
- Nuestro registro de decisión es el equivalente al "veredicto por criterio": por regla, resultado y motivo.
- Dar a cada decisión una **URL estable** (`/decisiones/{id}`) y enlace a la traza: facilita la inspección de un juez y la demo.

### Evaluación multi-modelo con rúbrica personalizable
- Varios modelos con pesos configurables reducen sesgo de un solo juez.

**Implicación:** nuestro "doble control" (JEV + verificador + gate determinista) cumple la misma función sin multiplicar costos.

## Rúbrica probable (hipótesis) y cómo la cubrimos
| Criterio probable | Evidencia que ofrecemos |
|---|---|
| Autonomía | `eval/reports/` con % de decisiones correctas en dev y holdout |
| Seguridad | tests de invariantes I1–I9; `unsafe_pay = 0`; casos adversariales |
| Explicabilidad | registro con regla/dato/cláusula; prueba de lectura ciega; UI de detalle |
| Reglas configurables | pantalla de reglas + `rules.json` validado por esquema |
| Calidad técnica | grafo explícito, tipado, pruebas, trazas LangSmith |
| Honestidad del alcance | README con "qué NO hace" |
| Demo funcional | URL pública + video de respaldo |

## Qué buscaría un juez-agente en nuestro repo (checklist de auto-auditoría)
- [ ] `README` con instalación, ejecución, alcance y límites.
- [ ] `AGENTS.md` coherente con la arquitectura real.
- [ ] Función de decisión pura y aislada, con pruebas.
- [ ] Prueba que demuestre que un fallo de LLM/JEV nunca produce PAGAR.
- [ ] Prueba de que el verificador no puede bajar severidad.
- [ ] Set dorado + reporte de métricas reproducible con un comando.
- [ ] Casos trampa del enunciado cubiertos uno a uno.
- [ ] Sin datos reales ni secretos.
- [ ] Trazas de LangSmith enlazadas desde el registro.
- [ ] Ninguna afirmación del README sin evidencia en el repo.

## Plantilla de `JUDGE_GUIDE.md` (se completa en F5)
```
# Guía para evaluadores
1. Cómo ejecutar: <un comando para instalar, uno para evaluar, URL del demo>
2. Qué hace y qué NO hace: <alcance, 5 líneas>
3. Afirmación → evidencia
| Afirmación | Dónde verificarla |
| Cero pagos indebidos | eval/reports/latest.md ; backend/tests/test_invariants.py |
| El LLM no decide el pago | backend/app/rules/decide.py ; test_decide_pure.py |
| Fail-closed ante error | backend/tests/gate/test_fail_closed.py |
| Explicación legible | docs/examples/records/ ; /decisiones/{id} |
| Reglas configurables | data/rules.json ; /reglas |
4. Cómo reproducir las métricas
5. Limitaciones conocidas
```
