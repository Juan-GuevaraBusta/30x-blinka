# T5.4 — Lectura ciega de 5 registros

Contrato: `docs/T5_4_SPEC.md`. Decisión: **D045**.

Fecha de la sesión: PENDIENTE — completar por la persona lectora.

El lector es el mismo humano (D011, 2026-10-16 22:27). No hay un segundo lector. Las lecturas no son independientes.

## 1. Cómo correr la lectura (para la persona lectora)

1. Abre, de uno en uno, solo estos cinco archivos:
   - `eval/reports/blind_read_packet/dev-001.md`
   - `eval/reports/blind_read_packet/dev-013.md`
   - `eval/reports/blind_read_packet/dev-015.md`
   - `eval/reports/blind_read_packet/dev-018.md`
   - `eval/reports/blind_read_packet/dev-021.md`
2. No abras `backend/`, `data/golden/`, `data/invoices/catalog.json`, ningún holdout, `.env` ni `/tmp/g3_e2e_decisions.json`. Si ya conoces el corpus por T1.7, dilo en la sección 3 con la frase ya puesta ahí; no finjas olvido.
3. Para cada ficha, escribe en la sección "2. Hoja de respuestas" de este mismo archivo, debajo del id correspondiente:
   - Tu respuesta libre (una frase) a "¿Qué decidió?", "¿Por qué?" y "¿Qué haría después?".
   - Para cada una de esas tres preguntas, una marca aparte: `sí` o `no` a "¿se entiende?". No hay punto medio; si dudas, la marca es `no`.
4. No le pidas a ningún agente que te explique la ficha ni que te diga si tu marca es la "correcta". No hay una respuesta correcta aquí: la marca es tu propio juicio de si la ficha se entiende.
5. Cuando termines las cinco, dilo para que se transcriban las marcas sin cambiarlas y se cuente el resultado (sección 4).

## 2. Hoja de respuestas (la llena la persona lectora)

### dev-001

- ¿Qué decidió? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Por qué? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Qué haría después? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- entendida: PENDIENTE (sí solo si las tres marcas de arriba son sí)

### dev-013

- ¿Qué decidió? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Por qué? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Qué haría después? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- entendida: PENDIENTE (sí solo si las tres marcas de arriba son sí)

### dev-015

- ¿Qué decidió? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Por qué? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Qué haría después? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- entendida: PENDIENTE (sí solo si las tres marcas de arriba son sí)

### dev-018

- ¿Qué decidió? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Por qué? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Qué haría después? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- entendida: PENDIENTE (sí solo si las tres marcas de arriba son sí)

### dev-021

- ¿Qué decidió? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Por qué? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- ¿Qué haría después? — PENDIENTE
  - ¿Se entiende? — PENDIENTE (sí/no)
- entendida: PENDIENTE (sí solo si las tres marcas de arriba son sí)

## 3. Confirmación del humano

- ¿Ya conocías el corpus sintético por T1.7 antes de esta sesión? PENDIENTE (sí/no).
- Confirmo que el texto de arriba (las marcas y las tres frases por ficha) es el mío, sin que un agente lo completara en mi lugar: PENDIENTE (sí/no).

## 4. Resultado — PENDIENTE — completar por la persona lectora

Esta sección la llena quien redacta el reporte, después de la sesión, transcribiendo la sección 2 sin cambiarla. Mientras la sección 2 diga PENDIENTE, esta sección también es PENDIENTE: no hay un `N/5` todavía.

- Resultado: **PENDIENTE / 5**
- Detalle por id y pregunta que falló (solo si `N < 4`): PENDIENTE.
- Meta de `docs/06` (`blind_read` ≥ 4/5): esa meta habla de una persona ajena al código. Esta sesión no tiene ese lector (Q4, D045): el lector es el mismo humano del proyecto, lectura no independiente. Llegar a 4 o a 5 no convierte a este lector en alguien que no vio el código. Quedarse en 3 o menos es un fallo anotado, no un borrador para reescribir la plantilla ni el id.

## 5. Notas de armado (para quien redacta el reporte — no se muestran al humano mientras lee las fichas)

Esta sección no contiene `expected_decision`, `expected_rules`, `case` ni ningún dato del golden: docs/T5_4_SPEC.md §7 paso 5 prohíbe escribirlos, y la lectura de la sección 1 no se corrige contra el golden (§6). Lo de aquí es solo administrativo: cómo se armaron las fichas y cómo se cuenta el resultado, separado de la hoja de respuestas para no sesgar la lectura.

- Las frases de las cinco fichas (`resumen`, `detalle` de cada chequeo, `siguiente paso`) son la salida literal de `build_summary`, `enrich_check_details` y `build_next_step` en `backend/app/records/build.py`/`templates.py`, copiadas sin parafrasear y sin pasada de LLM (I5).
- Las cinco fichas se generaron con el motor de G2: extracción verdadera de `data/golden/dev.json` + `run_deterministic_checks`/`decide`, con las señales JEV ya inyectadas en el `RuleContext` (`app.motor.golden_runner.build_rule_context`, mismo recorrido que `run_golden_split`: `sort_key`, `ledger_view_for_invoice`, asentamientos del ledger solo cuando la decisión es PAGAR). No es el grafo e2e de G3: no es una corrida de `run_invoice`/LangGraph y no usa el JSON de `/tmp/g3_e2e_decisions.json` del cierre de G3.
- No se abrió `data/golden/holdout.json` ni `data/invoices/holdout/`. No se calibraron umbrales. No se corrió `eval/run_eval.py`.
- Comando exacto de exportación:

  ```
  python eval/build_blind_read_packet.py --split dev
  ```

- sha256 de cada ficha (`shasum -a 256 eval/reports/blind_read_packet/dev-*.md`):

  ```
  f44bcef6b409d570a0c2d188eece3f5c21540e611c22566d7a2e8a71952699bc  eval/reports/blind_read_packet/dev-001.md
  0dbe1b7da1248e6f5e161d831ecfcb944d90844361713ca9e6ab3bebc158c244  eval/reports/blind_read_packet/dev-013.md
  0316ede21781ee95c63abc5d048a8222238a51751f9fa40ca24e9598d55b2711  eval/reports/blind_read_packet/dev-015.md
  8971be02c0028f809afb34a25f0c5f36888890df3403db7f3cb6c0057306b557  eval/reports/blind_read_packet/dev-018.md
  eed47200ccef4296542caeeca99138fc530e6954dda0f0f96118ecd963ad6947  eval/reports/blind_read_packet/dev-021.md
  ```

  (`eval/build_blind_read_packet.py` también se deja listo para commitear junto con el paquete, así T5.6 no depende solo de este sha256.)
- Cómo se cuenta el resultado: una ficha es "entendida" solo si las tres marcas de la sección 2 son `sí`. El resultado `N/5` es cuántas de las cinco fichas quedaron "entendida: sí". No se corrige ninguna marca contra `expected_decision`; la marca es el juicio del humano, transcrita tal cual.
- G5 sigue abierto. T5.4 no lo cierra. El claim de explicabilidad de G5, cuando exista, lleva la salvedad de Q4 (no es una persona ajena al código).
