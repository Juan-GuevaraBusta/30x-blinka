# Spec T5.4 — Lectura ciega de 5 registros

Dueño: **QA & Eval**. Skill: **NINGUNA** (`docs/SKILLS_MAP.md`, fila T5.4). No hay skill de lectura humana en el IDE; no se sustituye por `test-driven-development`, `python-testing-patterns` ni `verification-before-completion`. Depende de T2.6, ya HECHO: las plantillas viven en `backend/app/records/`.

Estado: contrato para la sesión que **ejecute** la lectura con el humano. Este archivo no hace esa lectura, no rellena sí/no y no cierra la tarea. No trae un resultado `4/5` ni ningún otro numerador.

Decisión que fija este contrato: **D045**.

D045. La lectura la hace el mismo humano del proyecto (D011, fila del 2026-10-16 22:27, la de la lectura; no la fila homónima de commit y push). Q4 está RESUELTA: no hay segundo lector, y el reporte dice que las lecturas no son independientes. La meta de `docs/06` (≥ 4/5, persona ajena) se publica con esa salvedad. Un resultado por debajo de 4 se anota; no se reescribe el registro para llegar a la meta. El paquete de fichas vive en `eval/reports/blind_read_packet/`, no en `docs/examples/records/` (eso es T5.5). T5.4 no bloquea el motor. Sí bloquea el claim de explicabilidad en G5. G5 no se cierra aquí.

## 0. Para la sesión que ejecuta

Pegar este archivo entero en el primer mensaje. Leer también, antes de armar fichas:

- `AGENTS.md` (I2 el LLM no decide ni reescribe la explicación; I5 la explicación sale de plantillas; I6 solo datos sintéticos; I8 cero dinero)
- `docs/OPEN_QUESTIONS_STATUS.md` fila Q4
- `docs/06_EVAL_AND_TEST_PLAN.md` fila `blind_read`
- `docs/AGENT_ROSTER.md` fila de paralelismo T5.4
- `docs/04_RULES_AND_DECISION_SPEC.md` §5 y §6
- `backend/app/records/templates.py` y `backend/app/records/build.py` (`build_summary`, `enrich_check_details`, `build_next_step`, `RecordContext.from_rule_context`)
- `backend/app/motor/golden_runner.py` (orden del ledger y `build_rule_context`; el split de esta tarea es `dev`)
- `docs/TASK_BOARD.md` fila T5.4

Declarar en una línea: skill NINGUNA. No leer otra skill para esta tarea.

El humano responde las tres preguntas. Un agente no las contesta en su lugar, no sugiere el sí o el no y no «completa» una ficha que el humano dejó en blanco. Si el humano no está en la sesión, T5.4 sigue PENDIENTE y no se crea `eval/reports/blind_read.md` con respuestas inventadas.

No abrir `data/golden/holdout.json`, `data/invoices/holdout/` ni `.env`. No hay red.

## 1. Qué es T5.4

Una persona lee cinco fichas y marca si entiende qué decidió el sistema, por qué y qué haría después. Una ficha cuenta como entendida solo cuando las tres marcas son sí. El número es cuántas de las cinco cumplen eso.

La evidencia futura es `eval/reports/blind_read.md`: los cinco ids, el resultado y la frase de que el lector es el mismo humano (D011).

`docs/AGENT_ROSTER.md`: T5.4 puede hacerse en cuanto haya cinco registros. No bloquea el motor. Sí bloquea el claim de explicabilidad en G5. El claim, cuando exista, lleva la salvedad de Q4: las lecturas no son de una persona ajena al código.

Las frases de las fichas salen de las plantillas de T2.6. El grafo ya estampa `DecisionRecord.id` con el `invoice_id` (`backend/app/graph/build.py`). En el repo no hay un volcado de cinco `DecisionRecord` distintos: el doble de `backend/tests/api/support.py` (`dec_0042` y las variantes `dec_pay`, `dec_esc`, `dec_stop`) repite el mismo `summary`, y el e2e de G3 escribió `/tmp/g3_e2e_decisions.json`, fuera del repo. Esas dos fuentes no son el paquete. El ejemplo de `docs/04` §5 (`dec_0042`) tampoco: es una ilustración, no cinco casos.

## 2. Fuera de alcance

- Hacer la lectura dentro de este contrato, o publicar un `N/5` antes de que el humano marque.
- Cerrar G5, G6, T5.1, T5.2, T5.3, T5.5 o T5.6.
- Crear `docs/examples/records/` o escribir `README.md` / `JUDGE_GUIDE.md`.
- Editar `backend/app/records/`, `decide()`, el grafo, los modelos o `data/`. Si una ficha sale ilegible (placeholder sin rellenar, traza de excepción, texto vacío), se para y se escala a Rules Engine. No se parchea la plantilla en esta tarea para aprobar la lectura.
- Abrir el holdout, calibrar umbrales o correr `eval/run_eval.py`.
- Llamar a un LLM para pulir `summary`, `detail` o `next_step`. I5: la explicación de la prueba es la plantilla, copiada tal cual.
- Usar el JSON de `/tmp` del cierre G3, ni el `summary` fijo de `make_record`.
- Mover dinero. Una ficha que hable de pago es un registro simulado (I8).

## 3. Archivos

Los crea la sesión de la lectura, no este contrato:

- `eval/reports/blind_read_packet/dev-001.md`
- `eval/reports/blind_read_packet/dev-013.md`
- `eval/reports/blind_read_packet/dev-015.md`
- `eval/reports/blind_read_packet/dev-018.md`
- `eval/reports/blind_read_packet/dev-021.md`
- `eval/reports/blind_read.md`

Al cerrar la lectura, también: `docs/TASK_BOARD.md` (fila T5.4) y una fila en `docs/AI_USAGE_LOG.md`. `docs/DECISIONS_LOG.md` es del Orquestador. D045 es este contrato; la sesión de la lectura no reabre esa decisión para cambiar la meta ni el lector.

No crear `docs/examples/records/`. El script que arma las fichas (p. ej. `eval/build_blind_read_packet.py`) se commitea junto con el paquete; si no se commitea, el comando exacto y el sha256 de cada ficha quedan anotados en `eval/reports/blind_read.md` (§7) para que T5.6 pueda verificar. Entran al diff el paquete, el reporte, el script (si se commitea) y las notas de tablero y de uso de IA.

## 4. Invariantes

- I2. Ni el armado ni la lectura llaman a un modelo para decidir o para reescribir. `decide()` solo elige el valor que las plantillas ya saben convertir en frase. Ese valor no se imprime como línea propia en la ficha.
- I5. `summary`, el `detail` de cada chequeo no OK y `next_step` son la salida de `build_summary`, `enrich_check_details` y `build_next_step`. Se copian. No se parafrasean en la ficha ni en el reporte.
- I6. Los cinco ids son del corpus sintético de desarrollo (Acme Demo Inc. y el catálogo ya del repo). Sin datos reales, sin claves, sin `.env`.
- I8. El reporte puede recordar, en una frase, que no hay pago. La lectura no ejecuta un pago.

## 5. Qué ve el lector

Cada ficha es un markdown en español, con el id en el título y tres bloques: resumen, chequeos, siguiente paso. Nada más.

| Bloque | Origen | Qué se copia |
|---|---|---|
| Resumen | `build_summary` | el string entero |
| Chequeos | `enrich_check_details` | por cada chequeo: `rule`, `name`, `result`, `detail` |
| Siguiente paso | `build_next_step` | el string entero |

No hay un campo `detail` en la raíz del `DecisionRecord`. El único `detail` es el de cada chequeo. No se añade una línea `decision:`. No se añade `expected_decision`, `expected_rules`, `case`, `reason` (el campo `reason` del golden, distinto del `summary`/`detail` de las plantillas), `severity`, extracción en bruto, señales JEV, `verifier`, `trace`, `versions`, `admin_notice` ni rutas de código. No se pega el registro JSON entero: con los chequeos R01–R13 la ficha ya es larga, y el spec no la reproduce.

El lector no tiene el código al lado, ni el catálogo, ni el golden, ni este apartado de selección, ni el informe de G3.

## 6. Preguntas fijas

Sobre cada ficha, en este orden, en español:

1. ¿Qué decidió?
2. ¿Por qué?
3. ¿Qué haría después?

Cada pregunta lleva una marca aparte: ¿se entiende? **sí** o **no**. No hay punto medio. Una ficha cuenta como entendida solo si las tres marcas son sí. Dos sí y un no es no entendida.

La respuesta libre (una frase del humano) se transcribe para ver que leyó la ficha. No se corrige contra el golden. No se usa `expected_decision` para cambiar un no en sí. El agente no puntúa la calidad literaria: anota las marcas del humano.

## 7. Los cinco ids y la exportación

Ids, todos `split: dev` en `data/invoices/catalog.json`. El `id` de la ficha es ese `invoice_id`, el mismo que el grafo escribe en `DecisionRecord.id`.

| Id | `case` del catálogo (solo para quien arma el paquete) |
|---|---|
| `dev-001` | `normal_pay` |
| `dev-013` | `dup_exact` |
| `dev-015` | `r01` |
| `dev-018` | `r06` |
| `dev-021` | `r04_only` |

Esa columna no se copia a las fichas ni a `blind_read.md`. Sirve para no elegir cinco textos iguales. `dev-012` es el anterior del par de duplicado exacto y no es una de las cinco fichas; el recorrido del ledger sí tiene que procesarlo antes de `dev-013`, igual que el motor.

Exportación, en la sesión. Quien arma el paquete commitea el script de exportación (p. ej. `eval/build_blind_read_packet.py`) junto con el paquete, o — si no lo commitea — anota en `eval/reports/blind_read.md` el comando exacto usado y el sha256 de cada una de las cinco fichas (`shasum -a 256 eval/reports/blind_read_packet/dev-*.md`), para que T5.6 pueda verificar sin tener que reconstruir el script de memoria. Las fichas se generan así:

1. Split fijo `dev`. Si la invocación pide `holdout`, se aborta.
2. Mismo orden y el mismo contexto que `run_golden_split`: entradas de `data/golden/dev.json`, `sort_key`, `build_rule_context`, `ledger_view_for_invoice`, `run_deterministic_checks`, `decide`. Los asentamientos del ledger siguen la regla del motor (solo cuando la decisión es PAGAR).
3. Para los otros id del split no se escribe ficha. Sí se recorren, porque el ledger de `dev-013` depende de lo anterior.
4. En cada id de la tabla: `RecordContext.from_rule_context`, luego `build_summary`, `enrich_check_details` y `build_next_step`. Esos tres strings, más `rule` / `name` / `result` / `detail` de cada chequeo, son la ficha.
5. `expected_decision`, `expected_rules` y `case` se leen solo dentro del proceso, si el runner ya los carga, y no se escriben.
6. Si dos fichas quedan con el mismo `summary`, se sustituye el id posterior por otro `dev-*` del mismo split cuyo resumen sea distinto, se anota el cambio en el reporte y no se entra al holdout para buscar variedad.
7. Si una ficha trae llaves sin rellenar, excepción o texto vacío, no se improvisa una frase. Se escala a Rules Engine y T5.4 sigue PENDIENTE.

El spec no pega ninguna ficha. El paquete es el archivo que lee el humano.

## 8. Protocolo de la sesión con el humano

1. Quien arma el paquete termina las cinco fichas y las deja en `eval/reports/blind_read_packet/`. En ese momento el humano no está eligiendo palabras ni viendo el golden.
2. El humano abre solo esos cinco markdown, de uno en uno. No abre `backend/`, `data/golden/`, `data/invoices/catalog.json`, el holdout, `.env`, `/tmp/g3_e2e_decisions.json` ni el código de las plantillas. Si ya conoce el corpus por T1.7, el reporte lo dice con la frase de abajo; no se finge olvido.
3. Para cada id responde por escrito las tres preguntas del §6 y marca sí o no en cada una. No pide al agente que le explique la ficha. Si duda, la marca es no.
4. Quien redacta `eval/reports/blind_read.md` transcribe las marcas sin cambiarlas. Cuenta cuántas fichas tienen las tres en sí. Ese entero es el resultado, entre 0 y 5.
5. Si el entero es menor que 4, el reporte dice que la meta no se alcanzó e indica qué pregunta falló en qué id. No se vuelve a generar la ficha, no se edita la plantilla y no se cambia el id para repetir hasta aprobar.
6. El humano confirma que el texto del reporte es el suyo (las marcas y las tres frases por ficha).

`eval/reports/blind_read.md` lleva, en este orden:

- La fecha de la sesión.
- Esta frase, literal, antes del número:

```text
El lector es el mismo humano (D011, 2026-10-16 22:27). No hay un segundo lector. Las lecturas no son independientes.
```

- Los cinco ids, en el orden del §7 (o el id sustituido, si el paso 6 de la exportación cambió uno).
- Por cada id: la respuesta breve a las tres preguntas y el sí/no de «se entiende» en cada una. Una línea `entendida: sí` solo si las tres son sí; si no, `entendida: no`.
- El resultado `N/5`.
- La meta de `docs/06` (≥ 4/5) y una frase de que esa meta habla de una persona ajena y esta sesión no tiene ese lector (Q4, D045).
- Que las frases de las fichas son las plantillas de `backend/app/records/`, sin pasada de LLM.
- Que las cinco fichas se generaron con el motor de G2 (extracción verdadera del golden + `run_deterministic_checks`/`decide`, con las señales JEV ya inyectadas en el `RuleContext`), no con el grafo e2e de G3: no son una corrida de `run_invoice`/LangGraph ni usan el JSON de `/tmp` del cierre G3.
- El comando exacto de exportación y el sha256 de cada una de las cinco fichas (§7), salvo que el script de exportación se haya commiteado junto con el paquete.
- Que no se abrió el holdout.
- Que G5 sigue abierto.

Sin la frase literal, el reporte no cuenta como evidencia de T5.4.

## 9. Meta, con la salvedad

`docs/06` define `blind_read` como cuántos de cinco registros entiende una persona ajena, meta ≥ 4/5. D045 no baja la meta y no inventa al ajeno. El reporte publica `N/5` junto a la frase del §8. Llegar a 4 o a 5 no convierte al lector en alguien que no vio el código. Quedarse en 3 o menos es un fallo anotado, no un borrador para reescribir.

Este contrato no afirma que el humano vaya a llegar a 4. No deja el numerador en blanco disfrazado de éxito.

## 10. Qué no afirmar, y cuándo la tarea está hecha

No afirmar:

- Que un lector ajeno al código hizo la lectura, o que las dos lecturas de Q4 son independientes.
- Un `4/5` o un `5/5` que el humano no haya marcado.
- Que un fallo se corrigió reescribiendo la ficha o la plantilla.
- Que G5 está cerrado, o que el claim de explicabilidad de G5 ya puede decir «persona ajena» sin la frase D011.
- Que el paquete es `docs/examples/records/` o el ejemplo `dec_0042`.
- Que el e2e de G3 (autonomía 55,9 %, JSON en `/tmp`) es esta prueba.
- Que se abrió el holdout o que un modelo redactó las explicaciones de la prueba.
- Que leer una ficha mueve dinero.

Hecho, solo después de la sesión con el humano:

1. Las cinco fichas en `eval/reports/blind_read_packet/`, sin `expected_decision`, sin `case` y sin código al lado. El texto de resumen, detalle y siguiente paso coincide con las tres funciones de `backend/app/records/build.py`, no con una paráfrasis.
2. `eval/reports/blind_read.md` con los cinco ids, las marcas, `N/5` y la frase literal del §8. Si `N` es menor que 4, el fallo está escrito y las plantillas siguen como estaban.
3. El humano no fue sustituido por el agente en las tres preguntas.
4. Diff de `data/golden/holdout.json`, de `data/invoices/holdout/` y de `backend/app/records/` vacío. Sin `.env`. Sin `docs/examples/records/`.
5. Tablero: T5.4 HECHA con la ruta del reporte, o PENDIENTE si el humano no estuvo. G5 sigue PENDIENTE. El motor no se reabre por esta tarea.
6. Fila en `docs/AI_USAGE_LOG.md`.
7. Commit: `T5.4: record blind read of five explanations`. Push a la rama de seguimiento.

```text
Ejecuta T5.4 según docs/T5_4_SPEC.md.
Skill: NINGUNA. No leas otra.
No hagas la lectura tú. No inventes un 4/5. No abras el holdout ni .env.
Arma cinco fichas en eval/reports/blind_read_packet/ con las plantillas
de backend/app/records/ (dev-001, dev-013, dev-015, dev-018, dev-021).
Sin expected_decision, sin case y sin el código al lado.
El humano responde qué decidió, por qué y qué haría después.
Cada pregunta es sí o no. Una ficha cuenta solo si las tres son sí.
El reporte eval/reports/blind_read.md lleva la frase literal de D011
(mismo humano, sin segundo lector, lecturas no independientes).
Si no llega a 4/5, anota el fallo. No reescribas plantillas.
No cierres G5. No crees docs/examples/records/.
Al terminar: commit T5.4: record blind read of five explanations, y push.
```
