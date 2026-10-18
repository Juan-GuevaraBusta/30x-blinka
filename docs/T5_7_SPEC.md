# Spec T5.7 — Unificar el import del backend para que la CLI de eval corra

Dueño: **Agent Graph**. Carril: B. Skill de dominio: NINGUNA (`docs/SKILLS_MAP.md`); proceso: `python-testing-patterns` PARCIAL, `test-driven-development`.

Depende de: ninguna tarea previa bloquea esta. T5.7 es el único arreglo del import de `backend`; **T5.1** y **T5.2** dependen de T5.7 HECHA (ver nota de coordinación abajo) y T5.7 desbloquea **T6.4** (el workflow de CI corre `eval/run_motor.py` y, de forma indirecta, el mismo paquete `app.extraction`).

Estado: contrato para la sesión que **implemente** T5.7. Este archivo no corre el comando ni cierra la tarea.

Decisión que fija este contrato: **D055** (`docs/DECISIONS_LOG.md`).

**Coordinación con T5.1 (D042, `docs/T5_1_SPEC.md`) y T5.2 (D043, `docs/T5_2_SPEC.md`).** La sesión de T5.1 documentó el mismo síntoma (`eval/reports/g3_closure_2026-10-17.md` línea 14). T5.7 es el **único** arreglo del import de `backend`: corrige la causa en el paquete (`backend/app/extraction/__init__.py`). No queda ninguna opción de arreglarlo vía `sys.path` dentro de los scripts de `eval/`; T5.1 y T5.2 no traen, ni plantean, un arreglo propio para esto. Ambas tareas declaran T5.7 (D055) como dependencia dura: si no está HECHA, se bloquean y no describen un comando distinto. T5.7 no inventa ni asume la forma de `eval/run_eval.py` si T5.1 todavía no lo ha creado: solo corrige el import del paquete y las pruebas de este spec.

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio NINGUNA: no hay skill que cubra una reescritura de imports. Declarar en una línea `python-testing-patterns` (PARCIAL) y leerla antes de tocar el test nuevo.

Lecturas:

- `backend/app/extraction/__init__.py` (líneas 3, 8 y 16 usan `backend.app.extraction.X`; línea 18 usa `.contracts` relativo)
- `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["backend/tests"]`, `pythonpath = ["backend"]`) y `[tool.setuptools.packages.find]` (`where = ["backend"]`)
- `eval/run_invoices.py` (importa `from app.config import load_settings`, `from app.graph import ...`: espera `app` como paquete top-level, no `backend.app`)
- `eval/reports/g3_closure_2026-10-17.md` línea 14 (`ModuleNotFoundError: No module named 'backend'` al correr la CLI)
- `docs/TASK_BOARD.md` fila G3 (nota: «`eval/run_invoices.py` exit 1 (import `backend`); follow-up T5.2») y filas T5.1/T5.2
- `docs/T5_1_SPEC.md` §0 y §5, y la fila D042 de `docs/DECISIONS_LOG.md` (T5.1 depende de T5.7 HECHA; no trae un arreglo propio del import)
- Cualquier otro módulo bajo `backend/app/` que importe con el prefijo `backend.app.` (buscar con grep antes de tocar nada; no asumir que solo `extraction/__init__.py` lo hace)

## 1. Qué es T5.7

Todo el resto del código importa `app.X` (resuelto porque `pythonpath = ["backend"]` en pytest, y porque la CLI se ejecuta con `backend/` como raíz de paquete). `backend/app/extraction/__init__.py` es la excepción: importa `backend.app.extraction.extract`, `backend.app.extraction.ingest` y `backend.app.extraction.text_normalize`. Esa forma solo resuelve si `backend` existe como paquete importable desde el directorio de trabajo, lo que no pasa cuando `eval/run_invoices.py` se ejecuta desde la raíz del repo — de ahí el `ModuleNotFoundError: No module named 'backend'`.

El arreglo es reescribir esas tres líneas a la forma relativa o `app.X`, igual que ya hace la línea 18 del mismo archivo con `.contracts`.

## 2. Alcance

- Cambiar `backend/app/extraction/__init__.py` líneas 3, 8 y 16: `backend.app.extraction.extract` → `.extract` (o `app.extraction.extract`), igual para `.ingest` y `.text_normalize`. Mantener el `__all__` igual.
- Buscar con `grep -rn "^from backend\.\|^import backend\." backend/app/` y corregir cualquier otra ocurrencia con el mismo patrón, si existe.
- Añadir una prueba de regresión que falle si alguien reintroduce el import roto: puede vivir en `backend/tests/test_extraction_imports.py` o añadirse a un archivo existente de `extraction`. Debe importar el módulo `app.extraction` y comprobar que no lanza `ModuleNotFoundError`.
- Añadir una prueba de regresión que ejecute el punto de entrada de la CLI como subproceso (`python eval/run_invoices.py --help` o equivalente de bajo costo, sin red ni facturas reales) desde la raíz del repo, y compruebe `returncode == 0`. Si `--help` no es viable por cómo está armado `argparse`, usar la invocación más barata que evite procesar las 34 facturas (por ejemplo, una carpeta vacía con `--data-root` y `--catalog` explícitos) — documentar cuál se usó.

## 3. Fuera de alcance

- Cambiar la lógica de `run_invoice_folder`, el grafo, el extractor o cualquier regla.
- Tocar `data/`, `eval/reports/`, `render.yaml` o el deploy.
- Resolver la calibración de JEV (T5.2) o correr el eval completo (T5.1).
- Cambiar `pyproject.toml` salvo que el grep del §2 revele que `pythonpath`/`testpaths` necesitan ajuste — si eso pasa, anotarlo y pedir confirmación antes de tocarlo, no asumir.

## 4. Criterios de aceptación

1. `cd backend && python -m pytest -q` sale 0 failed, con el mismo total de tests pasados que la última evidencia en `docs/TASK_BOARD.md` (419 en T4.10) más los tests nuevos de este spec; ningún test existente se rompe.
2. `python eval/run_invoices.py` (desde la raíz del repo) sale con código 0 en la invocación barata descrita en §2 (sin `ModuleNotFoundError`). Si `eval/run_eval.py` ya existe en el repo (T5.1, D042), repetir la misma comprobación barata sobre ese script también: mismo criterio, código 0, sin `ModuleNotFoundError: No module named 'backend'`. Si `eval/run_eval.py` todavía no existe, anotarlo y no inventar el archivo.
3. La prueba `backend/tests/test_invoice_corpus.py::test_regenerating_does_not_change_catalog_or_file_hashes` sigue en verde y, tras correr toda la suite, `git status --short` no muestra cambios en `data/invoices/` (el efecto secundario de esa prueba no deja el árbol sucio).
4. `python -m ruff check .` — ok.
5. Diff limpio: solo `backend/app/extraction/__init__.py` (y cualquier otro import corregido por el mismo patrón), el archivo de test nuevo o ampliado, y los registros de seguimiento (`docs/TASK_BOARD.md`, `docs/AI_USAGE_LOG.md`). Sin cambios en `data/` ni `eval/reports/`.
6. `docs/TASK_BOARD.md`: fila T5.7 pasa a HECHA con la evidencia de los comandos anteriores. T5.1, T5.2 y T6.4 siguen con su propio estado (no se marcan hechas desde aquí).
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit y push con el mensaje del §5.

## 5. Commit

```text
T5.7: unify backend import path so eval CLI runs
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T5.7 según docs/T5_7_SPEC.md. Decisión D055.
backend/app/extraction/__init__.py líneas 3, 8, 16 importan con el prefijo
backend.app.*; el resto del repo usa app.* (pythonpath=["backend"] en
pyproject.toml). Eso rompe `python eval/run_invoices.py` desde la raíz
(ModuleNotFoundError: No module named 'backend', ver
eval/reports/g3_closure_2026-10-17.md línea 14). Reescribe esos imports a la
forma relativa o app.*, igual que ya hace la línea 18 del mismo archivo.
Busca otras ocurrencias del mismo patrón con grep antes de dar por cerrado
el alcance. Añade una prueba que falle si el import se rompe de nuevo, y una
que corra la CLI como subproceso y exija exit 0 (sin procesar las 34
facturas si se puede evitar). Repite la comprobación sobre eval/run_eval.py
si T5.1 (D042) ya lo creó; no inventes ese archivo si todavía no existe.
T5.7 es el único arreglo de este import; T5.1 y T5.2 no traen uno propio
y dependen de que T5.7 esté HECHA. No toques reglas, grafo, data/ ni
eval/reports/.
Al terminar: cd backend && python -m pytest -q; python eval/run_invoices.py
desde la raíz; ruff check .; git status limpio en data/. Tablero y
AI_USAGE_LOG. Commit y push: T5.7: unify backend import path so eval CLI runs
```
