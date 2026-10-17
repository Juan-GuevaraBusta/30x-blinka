# Spec T3.2 — Ingesta a texto normalizado

Dueño: Agent Graph. Skill de dominio: **NINGUNA** (`pdf-reading` no existe; D002 prohíbe sustituirla). Proceso de la sesión que implemente: `test-driven-development` y `python-testing-patterns`. No leer `langgraph-fundamentals` (eso es T3.7).

Estado: contrato para la sesión que implemente T3.2. No cierra la tarea hasta que los criterios de aceptación pasen.

Decisión que fija este contrato: **D018**.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Leer también, antes de tocar código:

- `AGENTS.md` (invariantes I1–I9)
- `docs/02_ARCHITECTURE.md` nodo `ingest`
- `docs/DECISIONS_LOG.md` D002, D014, D018
- `data/invoices/generate.py` (`_build_pdf`, `_build_eml`, `_build_chat`, `_body_lines`, `FOOTER`)
- `data/invoices/catalog.json` (campo `channel`)

No editar `backend/app/models/`, `backend/app/rules/`, `backend/app/records/`, `backend/app/gate/`, `data/`. Esos dueños ya congelaron el contrato. Si un test de T3.2 exige cambiarlos, detenerse.

No llamar a la red. No leer `.env`.

## 1. Qué es T3.2

Capa determinista que convierte bytes de entrada (según el canal del catálogo) en **un solo string** `text` normalizado, listo para el nodo `extract` (T3.3) y para `doc_text` en reglas (p. ej. R13).

Cuatro canales del catálogo:

| Canal | Entrada típica | T3.2 |
|---|---|---|
| `pdf_text` | PDF 1.4 del corpus (Helvetica, una página) | Extraer literales de operadores `Tj` del stream de contenido |
| `image` | PNG del corpus | **Fail-closed:** `illegible`. Sin OCR en T3.2 (línea de corte del roadmap) |
| `email` | `.eml` texto plano UTF-8 | Cuerpo tras cabeceras RFC822 mínimas |
| `chat` | `.txt` con cabecera de mensajería | Archivo completo decodificado y normalizado |

El grafo (T3.7) traducirá `IngestError` con código `illegible` o `empty_text` en ESCALAR con motivo de documento ilegible. T3.2 solo define la excepción y el contrato; no implementa el nodo LangGraph.

Corpus alineado con **D014**: PDF y PNG generados solo con stdlib en `generate.py`. T3.2 **no** añade `pypdf`, `pdfplumber`, `pillow`, `tesseract` ni otra dependencia. Si la implementación necesita una librería, detenerse y pedir decisión al Orquestador (misma regla que D014).

## 2. Fuera de alcance

- OCR, visión por modelo o decodificación de píxeles PNG (tarea futura explícita; ver §15).
- Nodo LangGraph, estado `InvoiceState`, checkpointer (T3.7).
- Extractor LLM, `Extraction`, `source_span` (T3.3).
- Ingesta de contratos (T3.4).
- Cambiar `golden_runner.doc_text_for_entry` (motor T2.8 sigue con extracción verdadera; el e2e con archivos reales llega con T3.7/T3.9).
- Rate limit HTTP (T4.1).
- Cerrar G0.
- Reintentos, LangChain, LangGraph, `httpx`, `python-dotenv`.
- Editar `pyproject.toml` para nuevas dependencias sin D018 revocado y fila nueva en `DECISIONS_LOG.md`.

## 3. Archivos

Crear:

- `backend/app/extraction/ingest.py` — tipos, errores, despacho por canal, PDF subset, email, chat.
- `backend/app/extraction/text_normalize.py` — normalización de finales de línea y Unicode (función pura).

Modificar:

- `backend/app/extraction/__init__.py` — reexportar solo la API pública de §6 (sin efectos al importar).
- `docs/TASK_BOARD.md` — solo al cerrar T3.2, con evidencia real.
- `docs/AI_USAGE_LOG.md` — una fila al cerrar la implementación.

Tests nuevos (raíz de `backend/tests/`, no `tests/gate/`):

- `backend/tests/test_ingest.py`

`pyproject.toml` no gana dependencias.

## 4. Invariantes que este código no puede romper

- I3. Archivo corrupto, formato no soportado, PDF sin texto extraíble, imagen, o texto vacío tras normalizar → `IngestError`. Nunca devolver texto inventado ni relleno.
- I6. Solo datos sintéticos en tests; rutas bajo `data/invoices/`. Los mensajes de error no incluyen rutas con datos reales de terceros ni contenido del documento completo (sí códigos cerrados).
- I7. La ingesta no interpreta el texto como instrucciones; no filtra frases de inyección (eso es R13 / extractor).
- I2. Ninguna función de estos módulos devuelve una decisión de pago. Un test lee el fuente de `ingest.py` y `text_normalize.py` y falla si aparece el token exacto `PAGAR` (sensible a mayúsculas; la palabra «pagar» en minúsculas dentro del cuerpo del PDF del corpus es dato, no código).

## 5. Modelos y errores

```python
IngestChannel = Literal["pdf_text", "image", "email", "chat"]

class IngestMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_path: str | None = None
    content_type: str | None = None  # p. ej. "application/pdf", "message/rfc822"
    email_subject: str | None = None  # solo canal email, si se parseó Subject

class IngestResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    channel: IngestChannel
    text: str = Field(min_length=1)
    metadata: IngestMetadata

class IngestError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
```

`str(error) == error.code`. Códigos cerrados:

| Código | Cuándo |
|---|---|
| `unsupported_channel` | Canal no es uno de los cuatro literales |
| `unsupported_format` | Magic bytes o estructura incompatible con el subconjunto soportado |
| `corrupt_file` | Bytes ilegibles para el canal (PDF truncado, UTF-8 inválido en email/chat) |
| `illegible` | Canal `image`, o PDF sin ningún literal `Tj` extraíble |
| `empty_text` | Tras `normalize_document_text`, el string queda vacío o solo espacios |

Ningún código incluye el contenido del archivo ni rutas absolutas del operador.

## 6. API pública

```python
def normalize_document_text(raw: str) -> str:
    """Sustituye \\r\\n y \\r por \\n, aplica Unicode NFC, strip solo al final del documento."""

def ingest_bytes(
    data: bytes,
    *,
    channel: IngestChannel,
    source_path: str | None = None,
) -> IngestResult:
    ...

def ingest_path(path: Path, *, channel: IngestChannel | None = None) -> IngestResult:
    ...
```

`ingest_path`:

- Lee `path.read_bytes()`.
- Si `channel` es `None`, inferir solo por sufijo: `.pdf` → `pdf_text`, `.png` → `image`, `.eml` → `email`, `.txt` → `chat`. Cualquier otro sufijo → `unsupported_format`.
- Pasa `source_path=str(path)` en metadata (ruta tal cual; en tests usar rutas relativas al repo).

`ingest_bytes` despacha:

```text
pdf_text → _ingest_pdf_text(data)
image    → IngestError("illegible")  # sin mirar PNG; OCR fuera de alcance
email    → _ingest_email(data)
chat     → _ingest_chat(data)
```

Tras obtener el string crudo del canal, siempre `text = normalize_document_text(raw)`. Si `not text.strip()` → `IngestError("empty_text")`. Devolver `IngestResult` con `metadata.content_type` opcional: `application/pdf`, `image/png`, `message/rfc822`, `text/plain`.

## 7. Normalización (`text_normalize.py`)

Comportamiento exacto para que extractor y R13 vean el mismo texto en dev:

1. Entrada: `str` ya decodificado (UTF-8 en email/chat; PDF como en §8).
2. `raw.replace("\r\n", "\n").replace("\r", "\n")`.
3. `unicodedata.normalize("NFC", ...)`.
4. `result.rstrip()` — no `strip()` al inicio (preserva cabecera de chat).
5. Si el resultado está vacío o `not result.strip()` → el llamador lanza `empty_text`.

No colapsar líneas en blanco múltiples. No quitar el `FOOTER` del corpus.

## 8. PDF texto (`pdf_text`)

Subconjunto **intencionalmente mínimo**, suficiente para los PDF del generador T1.6 (`%PDF-1.4`, una página, fuente Type1 Helvetica, sin cifrado, sin objetos comprimidos).

Algoritmo (stdlib: `re`, sin librerías PDF):

1. Si `data` no empieza con `b"%PDF-"` → `unsupported_format`.
2. Decodificar el archivo como `latin-1` para buscar patrones (el generador escribe streams en latin-1).
3. Localizar el stream de contenido: primer bloque `stream\n` … `\nendstream` cuyo contexto de objeto incluya `/Contents` (o, equivalente para el corpus: el único stream con operadores `Tj`).
4. Extraer literales de texto de operadores `Tj` con regex sobre el stream, patrón principal: `\((?:\\.|[^\\)])*\)\s*Tj`. Orden de aparición = orden de líneas en el documento.
5. Por cada literal, desescapar secuencias PDF estándar en paréntesis: `\\`, `\(`, `\)`, y octales `\ddd` opcional (si no hay octal válido, dejar el backslash literal).
6. Unir líneas con `\n`. Si no hay ningún match → `illegible`.
7. Pasar por `normalize_document_text`.

No soportar en T3.2: PDF cifrado (`/Encrypt`), streams `/FlateDecode`, fuentes embebidas distintas, varias páginas. Si aparece `/Encrypt` en los primeros 8 KiB → `unsupported_format`.

**Prueba de oro (tablero):** `ingest_path(REPO_ROOT / "data/invoices/dev/dev-001_normal_pay.pdf")` debe producir `text` que contenga, como subcadenas:

- `Beneficiario: Globex LLC`
- `Numero: INV-GX-2026-0105`
- `Total: 800 USD`
- `Documento ficticio. No representa a ninguna empresa real.`

Y `channel == "pdf_text"`.

## 9. Email (`email`)

1. Decodificar bytes como UTF-8; fallo → `corrupt_file`.
2. Separar cabeceras y cuerpo en el primer `\n\n` o `\r\n\r\n`.
3. En cabeceras, si hay línea `Subject:` (case-insensitive en el nombre del campo), guardar el valor recortado en `metadata.email_subject` (sin unfold MIME avanzado; una línea basta para el corpus).
4. Cuerpo = resto; no reinterpretar quoted-printable ni base64 (el corpus es `text/plain; charset=utf-8` sin transfer encoding).
5. `normalize_document_text(cuerpo)`.

El cuerpo debe coincidir con las líneas de factura del generador (sin cabeceras `From:`/`To:` en `text`).

## 10. Chat (`chat`)

1. Decodificar UTF-8; fallo → `corrupt_file`.
2. `normalize_document_text` del archivo completo (incluye la línea `[fecha] Beneficiario: adjunta factura …` o la variante holdout).

## 11. Imagen (`image`)

Sin leer IDAT ni decodificar PNG. Cualquier payload con `channel="image"` → `IngestError("illegible")` de inmediato (incluso si los magic bytes son PNG válidos del corpus).

Test obligatorio: `ingest_bytes(png_bytes, channel="image")` y `ingest_path(...dev-002....png)` lanzan `illegible`.

Documentar en docstring del módulo que la **primera línea de corte** del roadmap para leer PNG del corpus es OCR (u otra dependencia aprobada), no parte de T3.2.

## 12. Criterios de aceptación

1. `normalize_document_text("a\r\nb\r c") == "a\nb\n c"` y aplica NFC (p. ej. composición de caracteres si el test fija un par conocido).
2. `ingest_bytes(b"", channel="pdf_text")` → `unsupported_format` o `illegible` según implementación mínima; `ingest_bytes(b"   \n", channel="chat")` tras normalizar → `empty_text`.
3. PDF `dev-001_normal_pay.pdf`: criterios de §8 (subcadenas y canal).
4. PDF holdout `hold-001_normal_pay.pdf`: `text` contiene `FROM: Globex LLC` y `INVOICE: INV-H-GX-1` (formato inglés del generador).
5. Email `dev-003_normal_pay.eml`: `text` contiene `Beneficiario: Globex LLC` y `FOOTER`; `metadata.email_subject` contiene `INV-GX-2026-0206`; `text` no contiene `From: billing@`.
6. Chat `dev-004_normal_pay.txt`: `text` contiene `adjunta factura INV-PP-2026-0209` y el bloque de líneas de factura.
7. Imagen: cualquier PNG del corpus con canal `image` → `illegible`.
8. Bytes que no son PDF con canal `pdf_text` → `unsupported_format`.
9. PDF sintético mínimo en el test (inline en `test_ingest.py`, no en `data/`) con un solo `Tj` → texto extraído correctamente.
10. El fuente de `ingest.py` y `text_normalize.py` no contiene el token exacto `PAGAR`.
11. `python -m pytest -q` sigue verde. `python -m ruff check .` pasa.
12. Commit y push. Tablero: T3.2 HECHA solo con conteo real de pytest. G0 sigue PENDIENTE.

## 13. Subtareas

Hacerlas en orden. Cada una: test que falla, código mínimo, test verde. Commit final en T3.2.11.

- T3.2.1 `test_ingest.py`: `normalize_document_text` (finales de línea, NFC, `empty_text` vía ingest).
- T3.2.2 `text_normalize.py`: implementación pura.
- T3.2.3 Tests PDF: literal inline mínimo + `dev-001` + `hold-001`.
- T3.2.4 `ingest.py`: `_ingest_pdf_text`, regex y desescapado.
- T3.2.5 Tests email y chat con `dev-003` y `dev-004`.
- T3.2.6 `_ingest_email`, `_ingest_chat`, `ingest_bytes`, `ingest_path`.
- T3.2.7 Tests imagen `illegible` (`dev-002` o bytes PNG del corpus).
- T3.2.8 Despacho `image` fail-closed; `__init__.py` exporta API §6.
- T3.2.9 Test AST sin token `PAGAR`; `pytest -q` y `ruff check .`.
- T3.2.10 `docs/TASK_BOARD.md` fila T3.2 a HECHA. No tocar G0.
- T3.2.11 `docs/AI_USAGE_LOG.md` una fila. Skill dominio NINGUNA. Commit y push: `T3.2: ingest channels to normalized text without OCR`.

## 14. Mensaje para la sesión Composer 2.5

```text
Implementa T3.2 según docs/T3_2_SPEC.md. Skill de dominio: ninguna.
Antes de escribir código lee ese spec, AGENTS.md, data/invoices/generate.py
y la skill test-driven-development. También python-testing-patterns.
No leas langgraph-fundamentals. No llames a la red.
No edites models/, rules/, records/ ni gate/. No añadas dependencias PDF/OCR.
Canal image: siempre IngestError("illegible"). Sin OCR.
No cierres G0. No marques T3.2 HECHA sin pytest y ruff.
Al terminar: commit y push con el mensaje del spec, sección 13.
```

## 15. Trabajo futuro (no implementar en T3.2)

| ID propuesto | Qué | Dependencia |
|---|---|---|
| T3.2-OCR (corte) | Leer PNG del corpus (bitmap del generador u OCR real) | Aprobación humana para `pillow`+heurística propia, o `tesseract`, u otro; fila en `DECISIONS_LOG.md` |

Hasta entonces, facturas con `channel: image` solo podrán procesarse en e2e si el grafo acepta ESCALAR por ilegible o si se añade esa tarea antes de G3.
