# Spec T6.5 — Licencia, política de seguridad y guía de contribución

Dueño: **Docs & Judge**. Carril: B. Skill de dominio: NINGUNA. Proceso: ninguno adicional (no es un cambio de código).

Depende de: ninguna. Puede hacerse en paralelo con cualquier otra tarea de F5/F6.

Estado: contrato para la sesión que **implemente** T6.5. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D055** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio NINGUNA.

Lecturas:

- Confirmado en esta sesión: no existen `LICENSE`, `SECURITY.md` ni `CONTRIBUTING.md` en la raíz del repo.
- `AGENTS.md` completo (I1–I9, convenciones de idioma, commits, protocolo de skills) — `CONTRIBUTING.md` lo resume, no lo duplica palabra por palabra.
- `AGENTS.md` I6 (solo datos sintéticos) e I8 (cero dinero real) — base del alcance de `SECURITY.md`.
- `pyproject.toml` (comandos `ruff`, `pytest`) y `frontend/package.json` (comandos `lint`, `test`, `tsc`) — base de la sección de setup de `CONTRIBUTING.md`.
- `docs/DECISIONS_LOG.md` (formato de fila) y el patrón de `docs/T*_SPEC.md` ya existentes — base de la sección «flujo de spec por tarea» de `CONTRIBUTING.md`.
- Historial de mensajes de commit ya usados en el repo (`T2.3: implement R02 per-payment limit` como ejemplo en `AGENTS.md` §3; D040, D041 citan hashes cortos de commits reales) — confirma el estilo Conventional Commits + ID de tarea.

## 1. Qué es T6.5

Tres archivos nuevos en la raíz, en inglés (son artefactos técnicos genéricos de GitHub, no documentación de producto en español — igual que el resto de archivos de código y configuración del repo, por la convención de `AGENTS.md` §3).

| Archivo | Contenido |
|---|---|
| `LICENSE` | MIT, marcada como **SUPUESTO** hasta que el humano decida otra cosa |
| `SECURITY.md` | Cómo reportar una vulnerabilidad; alcance: solo datos sintéticos (I6), sin dinero real (I8) |
| `CONTRIBUTING.md` | Setup, comandos, estilo de commits (Conventional Commits + ID de tarea), flujo de spec por tarea |

## 2. `LICENSE`

Texto estándar de la licencia MIT, con el titular de copyright en blanco o con un marcador genérico (`[nombre del titular]`) si el repo no tiene ya un nombre de autor fijado en otro archivo — no inventar un nombre de persona ni de empresa real. Encabezar el archivo (como comentario fuera de las líneas de la licencia, o en el commit) con la nota de que MIT es un **SUPUESTO** de esta tarea: el humano puede reemplazarla por otra licencia antes de la entrega final sin que eso bloquee ninguna otra tarea del tablero.

## 3. `SECURITY.md`

En inglés, con esta estructura mínima:

- **Reporting a vulnerability**: cómo contactar (abrir un issue privado de seguridad de GitHub si el repo lo permite, o la vía que el humano prefiera — no inventar un correo o canal que no exista; si no hay vía confirmada, decir «abrir un issue en este repositorio» como vía por defecto).
- **Scope**: este es un proyecto de hackathon con datos **sintéticos únicamente** (I6, `AGENTS.md`). No hay datos reales de clientes, proveedores ni empresas en el repo. Una decisión `PAGAR` es un registro simulado; el sistema **no mueve dinero real** (I8). Un reporte de seguridad sobre "exposición de datos reales" no aplica porque no existen en el repo; un reporte sobre la falta de autenticación de los endpoints mutantes (antes de T5.9) o sobre la race de ledger (antes de T5.8) es información ya conocida y documentada en `docs/T5_8_SPEC.md` y `docs/T5_9_SPEC.md` — enlazar esos dos archivos en vez de repetir el detalle.
- **Out of scope**: ataques de denegación de servicio contra el deploy gratuito de Render/Vercel (ya es un servicio `free` que se duerme, documentado en `docs/T4_9_SPEC.md`); vulnerabilidades en dependencias de terceros reportadas por CodeQL o Dependabot, que se gestionan como issues normales, no como reporte de seguridad privado.

## 4. `CONTRIBUTING.md`

En inglés, con esta estructura mínima:

- **Setup**: `python -m venv .venv` (o equivalente), `pip install -e ".[dev]"`, `cd frontend && npm install`. Citar los comandos reales de `pyproject.toml` y `frontend/package.json`, no inventar otros.
- **Running checks**: `ruff check .`, `pytest -q` (desde la raíz o `cd backend && pytest`, según quede resuelto por T5.7), `cd frontend && npx tsc --noEmit && npm run lint && npm test`.
- **Commit style**: Conventional Commits con un ID de tarea del tablero al inicio del asunto, ejemplo real del repo: `T2.3: implement R02 per-payment limit` (`AGENTS.md` §3). Código y commits en inglés; documentación y UI en español (`AGENTS.md` §3). Sin `Co-Authored-By` ni atribución de IA en el commit (esta es una convención del autor humano del repo, documentarla tal cual sin inventar una regla distinta).
- **Spec-per-task workflow**: cada tarea no trivial del tablero tiene un contrato `docs/T<fase>_<n>_SPEC.md` antes de implementarse (patrón ya usado por T0.1 en adelante); el contrato define alcance, fuera de alcance y criterios de aceptación. Enlazar `docs/TASK_BOARD.md`, `docs/05_PHASES_AND_ROADMAP.md` y `AGENTS.md` como punto de entrada para quien quiera contribuir una tarea nueva.
- **Invariants**: una frase que remita a `AGENTS.md` §2 (I1–I9) como las reglas que ninguna contribución puede romper, sin copiar la tabla completa (un solo archivo fuente de verdad).

## 5. Fuera de alcance

- Elegir la licencia final si el humano prefiere otra distinta de MIT: se marca SUPUESTO y se sigue.
- Configurar GitHub Security Advisories, un programa de recompensas, o una dirección de correo de seguridad nueva.
- Un `CODE_OF_CONDUCT.md` o una plantilla de PR/issue: no los pidió esta tarea.
- Editar `README.md`, `AGENTS.md` o cualquier archivo de `docs/` más allá de `docs/TASK_BOARD.md` y `docs/AI_USAGE_LOG.md` al cerrar.
- Tocar código de producto, tests o `data/`.

## 6. Criterios de aceptación

1. `LICENSE` existe en la raíz, texto MIT completo, con la nota de SUPUESTO sobre la elección anotada en el commit o en `docs/TASK_BOARD.md` (no es necesario que la nota viva dentro del propio archivo de licencia, que sigue el formato estándar).
2. `SECURITY.md` existe, en inglés, con las tres secciones del §3, citando I6 e I8 de `AGENTS.md` y enlazando `docs/T5_8_SPEC.md` y `docs/T5_9_SPEC.md`.
3. `CONTRIBUTING.md` existe, en inglés, con las cinco secciones del §4, con comandos verificados contra `pyproject.toml` y `frontend/package.json` (no inventados).
4. Ninguno de los tres archivos contiene datos reales, claves, URLs con token o el nombre de una persona real.
5. Diff limpio: solo los tres archivos nuevos, más `docs/TASK_BOARD.md` y `docs/AI_USAGE_LOG.md` al cerrar.
6. `docs/TASK_BOARD.md`: T6.5 pasa a HECHA.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit y push con el mensaje del §7.

## 7. Commit

```text
T6.5: add license, security policy and contributing guide
```

## 8. Mensaje para la sesión que implementa

```text
Implementa T6.5 según docs/T6_5_SPEC.md. Decisión D055.
Crea LICENSE (MIT, SUPUESTO hasta que el humano decida otra cosa),
SECURITY.md y CONTRIBUTING.md en la raíz, en inglés (artefactos técnicos
genéricos, no documentación de producto). Ninguno de los tres existe hoy.
SECURITY.md: cómo reportar, alcance solo datos sintéticos (I6) y cero dinero
real (I8), enlaza docs/T5_8_SPEC.md y docs/T5_9_SPEC.md para lo ya conocido
(race del ledger, falta de auth), fuera de alcance DoS del free tier y
vulnerabilidades de dependencias (van por issue normal).
CONTRIBUTING.md: setup real (pyproject.toml, frontend/package.json),
comandos de chequeo reales, estilo Conventional Commits + ID de tarea
(ejemplo real: "T2.3: implement R02 per-payment limit", AGENTS.md §3),
inglés en código/commits y español en docs/UI, sin Co-Authored-By, flujo de
spec por tarea (docs/T*_SPEC.md) y enlaces a TASK_BOARD/05_ROADMAP/AGENTS.md.
No inventes datos, claves ni nombres de personas reales.
Al terminar: tablero y AI_USAGE_LOG. Commit y push:
T6.5: add license, security policy and contributing guide
```
