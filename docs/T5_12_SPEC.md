# Spec T5.12 — Decodificar streams PDF con FlateDecode en ingest

Dueño: **Agent Graph**. Carril: B. Skill de dominio: NINGUNA (`docs/SKILLS_MAP.md`); proceso: `test-driven-development`, `python-testing-patterns` (PARCIAL).

Depende de: ninguna tarea previa bloquea esta. No bloquea ninguna tarea del backlog D055; es un hallazgo nuevo, posterior a T4.10.

Estado: contrato para la sesión que **implementa** T5.12. Este archivo no corre el comando ni cierra la tarea.

Decisión que fija este contrato: **D056** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio NINGUNA. Declarar `test-driven-development` y `python-testing-patterns` (PARCIAL) y leerlas antes de escribir los tests nuevos.

Lecturas:

- `backend/app/extraction/ingest.py` — `_ingest_pdf_text`, `_pdf_content_stream`, `_TJ_PATTERN`, `_unescape_pdf_literal`.
- `backend/tests/test_ingest.py` — convenciones de test existentes para `ingest_bytes`/`ingest_path`.
- `backend/tests/smoke/test_external_pdf_smoke.py` y `docs/PIPELINE_SMOKE_EXTERNAL_SPEC.md` — T4.10 mockea `run_invoice`, por lo que el humo **nunca** pasa un PDF real por la ingesta real; por eso el bug no se detectó ahí.
- `data/invoices/smoke-external/external-smoke-01.pdf` y `-02.pdf` — PDFs reales del generador externo MIT (T4.10, D041); ambos usan `/Filter [ /ASCII85Decode /FlateDecode ]` en su stream de contenido.
- `AGENTS.md` I7 (texto de factura = dato no confiable, nunca instrucciones) — el cambio no debe alterar esa semántica.

## 1. Qué es T5.12

`_pdf_content_stream` en `backend/app/extraction/ingest.py` solo busca bytes crudos sin comprimir entre `stream...endstream` y descarta cualquier chunk que no contenga literalmente la subcadena `"Tj"`. La mayoría de generadores de PDF reales comprimen el content stream con `FlateDecode` (a veces encadenado con `ASCII85Decode`), así que esos bytes nunca contienen `"Tj"` en claro: la función no encuentra ningún stream candidato, devuelve `""`, y `_ingest_pdf_text` lanza `IngestError("illegible")`. El resultado: **cualquier PDF real subido por un juez en la demo termina en ESCALAR**, no porque el documento sea ilegible sino porque el ingest solo sabe leer PDFs sin comprimir.

Esto no se detectó en T4.10 porque `backend/tests/smoke/test_external_pdf_smoke.py` mockea `app.api.production_processor.run_invoice`: el PDF real se lee de disco y se sube, pero el grafo (y por tanto la ingesta real) nunca se ejecuta sobre esos bytes.

Verificado con `zlib`/`base64` sobre los dos PDFs de `data/invoices/smoke-external/`: el content stream de ambos decodifica con `ASCII85Decode` seguido de `FlateDecode` a texto con operadores `Tj` en claro (p. ej. `(TOTAL) Tj`, `(R e c h n u n g) Tj`, números de factura y VIN sintéticos).

## 2. Alcance

- Reescribir el recorrido de streams en `backend/app/extraction/ingest.py` para que, por cada objeto `stream...endstream` del documento:
  1. Lea el diccionario `<< ... >>` que precede a `stream` y busque `/Filter` (forma simple `/FlateDecode` o arreglo `[ /ASCII85Decode /FlateDecode ]`, en cualquier orden de filtros soportados).
  2. Si no hay `/Filter`, use los bytes del stream tal cual (camino existente, sin cambios de comportamiento).
  3. Si hay `/FlateDecode` (sola o precedida por `/ASCII85Decode`), decodifique con `zlib` (stdlib, sin dependencia nueva) aplicando los filtros en el orden declarado.
  4. Si el filtro no se reconoce, o la decodificación falla (`zlib.error`, `ascii85` inválido), o el tamaño descomprimido excede un tope de **5 MB**, descarte ese stream (no intente interpretarlo como texto) en vez de abortar toda la ingesta — el fail-closed final sigue siendo "ningún stream produjo texto → `illegible`".
- Extraer operadores de texto (`Tj`, arreglos `TJ`, `'` y `"`) de cada stream ya decodificado, igual que hoy se hace para `Tj` con cadenas literales `(...)`. Soportar cadenas hex `<...>` solo en el caso simple (pares de 2 dígitos hex que decodifican a bytes ASCII imprimibles); si la cadena hex no es "simple" (p. ej. fuentes CID de 2 bytes por glifo con CMap propio), no emitir texto para esa cadena — queda fail-closed, no se inventa texto.
- Tope de descompresión (`5 MB`) implementado con `zlib.decompressobj` + `max_length` para no materializar la bomba completa en memoria antes de cortar.
- Mantener semántica I7: el texto extraído sigue siendo dato no confiable; no se ejecuta ni interpreta como instrucción en ningún punto de este cambio.
- Limitación a documentar (no a resolver aquí): fuentes con *encoding* personalizado o CID (glifo → código ajeno a ASCII, mapeado por `/ToUnicode` o CMap) pueden producir cadenas hex o literales que no son texto legible plano; esos casos quedan fail-closed (`illegible` si no hay ningún otro stream legible) en vez de inventar texto incorrecto. No se implementa `/ToUnicode` ni CMap en este cambio.

## 3. Fuera de alcance

- Cualquier dependencia nueva (`pypdf`, `pdfminer`, etc.) — solo stdlib `zlib` (+ `base64` si se usa para `ASCII85Decode`; también stdlib).
- OCR de imágenes (`channel="image"` sigue fail-closed, sin cambios).
- `/ToUnicode`, CMap, fuentes CID — quedan fail-closed, documentado como limitación conocida.
- Tocar `_unescape_pdf_literal`, `_ingest_email_raw`, `_ingest_chat`, `normalize_document_text`.
- `data/invoices/dev/`, `holdout/`, `golden/`, `catalog.json` — ningún PDF de esos corpora se toca ni se regenera.
- `data/invoices/smoke-external/*.pdf` — no se reemplazan ni regeneran; solo se leen.
- Reglas, grafo, JEV, verificador, motor de reglas.
- `docs/TASK_BOARD.md`, `docs/DECISIONS_LOG.md`, `docs/AI_USAGE_LOG.md` — los cierra el Orquestador.

## 4. Criterios de aceptación

1. TDD observado: tests nuevos en rojo contra el código viejo (muestran `IngestError("illegible")` sobre los PDFs externos y sobre un PDF sintético con `/Filter /FlateDecode`), luego en verde tras la implementación.
2. `ingest_path` sobre `data/invoices/smoke-external/external-smoke-01.pdf` y `-02.pdf` (ejecutados de verdad, sin mocks) devuelve `channel == "pdf_text"` y `result.text` contiene al menos un token reconocible de cada factura (verificado por inspección manual con `zlib`/`base64`, no inventado).
3. Test unitario con un PDF sintético mínimo construido en el propio test (`/Filter /FlateDecode` simple, y también la forma arreglo `[/FlateDecode]`) extrae el `Tj` esperado.
4. Stream `FlateDecode` corrupto (bytes no válidos tras el filtro) sigue produciendo `IngestError("illegible")` — fail-closed, no excepción no controlada.
5. Bomba de descompresión (stream que comprime unos pocos KB pero expande muy por encima de 5 MB) produce `IngestError("illegible")` sin agotar memoria ni tiempo de ejecución razonable.
6. Camino sin comprimir existente (`test_minimal_inline_pdf_extracts_single_tj`, `test_dev_001_pdf_golden_substrings`, `test_hold_001_pdf_english_lines`, etc. en `backend/tests/test_ingest.py`) sigue en verde sin cambios de comportamiento.
7. `python -m pytest -q` desde la raíz: 0 failed, con el mismo total de T5.9 (462) más los tests nuevos de este spec; ningún test existente se rompe.
8. `git status --porcelain data/` solo muestra el cambio de una línea en `data/invoices/smoke-external/README.md` (nota sobre si la ingesta real ahora lee esos PDFs); ningún otro archivo bajo `data/` cambia.
9. `python eval/run_motor.py` sigue con `unsafe_pay = 0`.
10. `python -m ruff check .` — ok.
11. Diff limpio: `backend/app/extraction/ingest.py`, el/los archivo(s) de test nuevos, `data/invoices/smoke-external/README.md` (una línea), `docs/T5_12_SPEC.md`, y los registros de seguimiento que cierra el Orquestador (`docs/TASK_BOARD.md`, `docs/DECISIONS_LOG.md`, `docs/AI_USAGE_LOG.md`) — estos tres últimos no los toca esta sesión.

## 5. Commit

```text
T5.12: decode FlateDecode PDF streams in ingest
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T5.12 según docs/T5_12_SPEC.md. Decisión D056.
_pdf_content_stream en backend/app/extraction/ingest.py solo lee streams PDF
sin comprimir y descarta cualquier chunk sin "Tj" literal. Los PDFs reales
(incluidos los dos de data/invoices/smoke-external/, T4.10/D041) comprimen
su content stream con FlateDecode (a veces encadenado con ASCII85Decode),
así que el ingest real siempre cae en IngestError("illegible") sobre un PDF
normal — ESCALAR garantizado en la demo. T4.10 no lo detectó porque mockea
run_invoice. TDD: primero tests en rojo contra la ingesta real de los dos
PDFs externos y un sintético con /Filter /FlateDecode (forma simple y
arreglo), más corrupción de stream y bomba de descompresión (tope 5 MB)
fail-closed. Implementa con zlib stdlib (sin dependencia nueva): detecta
/Filter por objeto stream, decodifica, extrae Tj/TJ/'/" y cadenas hex
simples; si el filtro no se reconoce o falla, descarta ese stream sin
abortar la ingesta completa. Mantén I7 (texto no confiable) y el camino sin
comprimir existente sin cambios de comportamiento. Fuentes CID/encoding
personalizado quedan fail-closed, documentado como limitación conocida, no
resuelto aquí. No toques data/invoices/dev, holdout, golden, catalog.json;
solo una línea en data/invoices/smoke-external/README.md. No toques
TASK_BOARD, DECISIONS_LOG ni AI_USAGE_LOG — los cierra el Orquestador.
Al terminar: python -m pytest -q (462 base + nuevos); git status --porcelain
data/ (solo la línea del README); python eval/run_motor.py (unsafe_pay=0);
ruff check .
```
