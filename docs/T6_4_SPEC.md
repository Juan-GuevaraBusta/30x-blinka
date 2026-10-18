# Spec T6.4 — CI con gate de eval (`unsafe_pay`) y CodeQL

Dueño: **Orquestador**. Carril: B. Skill de dominio: NINGUNA (no hay skill de CI/CodeQL en el mapa). Proceso: ninguno adicional.

Depende de: **T5.7** (el workflow corre `pytest` y `eval/run_motor.py`; si el import roto de D039/T5.7 sigue sin arreglar, la CI falla por una razón ajena al código que se quiere proteger).

Estado: contrato para la sesión que **implemente** T6.4. Este archivo no corre el workflow ni cierra la tarea.

Decisión que fija este contrato: **D055** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill de dominio NINGUNA: no inventar una.

Lecturas:

- `runtime.txt` (`python-3.11.11`, confirmado en esta sesión)
- `pyproject.toml` (`[project.optional-dependencies] dev`, `[tool.ruff]`, `[tool.pytest.ini_options]`)
- `eval/run_motor.py` (el gate I9 ya existente: motor contra `data/golden/dev.json`, imprime `unsafe_pay=N` y, si el script no sale con código de error en `unsafe_pay > 0`, revisar y ajustar el propio script en esta tarea para que sí lo haga — leer su código antes de asumir el código de salida)
- `docs/T5_7_SPEC.md` y `docs/T5_1_SPEC.md` (qué arregla cada uno del import `backend.app.*`; esta tarea no reescribe ninguno de los dos)
- `AGENTS.md` I9 (`unsafe_pay > 0` bloquea el despliegue; el gate se verifica en `eval/`)
- `frontend/package.json` (scripts `lint`, `test`, y si existe `build`; `tsc --noEmit` ya se usa en los specs de T4.x)
- Confirmado en esta sesión: no existe `.github/` en el repo. Esta tarea lo crea.

No tocar `backend/app/`, `frontend/app/`, `data/` ni `eval/reports/`. Si `eval/run_motor.py` no retorna un código de salida distinto de 0 cuando `unsafe_pay > 0`, ese ajuste de código de salida es el único cambio permitido fuera de `.github/`; documentarlo explícitamente en el diff y en `docs/AI_USAGE_LOG.md`, sin tocar la lógica de negocio del script.

## 1. Qué es T6.4

Dos workflows de GitHub Actions en `.github/workflows/`:

| Workflow | Qué corre | Qué bloquea |
|---|---|---|
| `ci.yml` | Python 3.11, `ruff check .`, `pytest -q`, `eval/run_motor.py` (gate `unsafe_pay > 0` falla el job), frontend `npm ci` + lint + `tsc --noEmit` + vitest | El job en rojo en cada push/PR |
| `codeql.yml` | Análisis estático CodeQL para `python` y `javascript-typescript` | Alertas de seguridad en la pestaña Security de GitHub |

**Honestidad sobre el alcance del gate**: este workflow corre en GitHub Actions, no en el pipeline de despliegue de Render. `render.yaml` (confirmado en esta sesión) solo define `buildCommand: pip install .` y `startCommand: uvicorn ...`; no invoca a CI ni a `eval/`. Un push a la rama de despliegue en Render se despliega igual aunque la CI de GitHub esté roja, **salvo que** el humano configure en el dashboard de Render o en la rama protegida de GitHub que el deploy espere al workflow — paso que esta tarea no puede hacer desde el repo y que no se afirma hecho. La fila de este spec en `docs/TASK_BOARD.md` y la posible actualización de T5.6 (ver `docs/T5_6_SPEC.md` §4) deben decir, tal cual: el gate de eval queda cableado en CI, no en el despliegue de Render.

## 2. Por qué `eval/run_motor.py` y no `eval/run_eval.py`

`eval/run_eval.py` (T5.1, D042) llama a `run_invoice_folder` con `phase=eval`, que usa red real (extractor, verificador, JEV, LangSmith) y necesita las claves de `.env`. Un workflow de CI sin secretos no puede correrlo. `eval/run_motor.py` ya corre el motor determinista contra `data/golden/dev.json` con extracción verdadera del golden, sin red y sin claves (es el mismo comando que cerró G2, D028): es el candidato correcto para un gate de CI sin secretos. Si al implementar esta tarea `eval/run_eval.py` ya existe y expone un modo sin red equivalente a `eval/run_motor.py`, se puede documentar la alternativa en el PR, pero el comando por defecto de `ci.yml` sigue siendo `eval/run_motor.py`.

## 3. `ci.yml`

- Disparadores: `push` y `pull_request`.
- `permissions: contents: read` a nivel de workflow (mínimo necesario; sin `write` salvo que un paso lo exija, y ninguno de los pasos de este spec lo exige).
- Acciones oficiales fijadas por versión mayor (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`), nunca `@main` o sin versión.
- Job `backend`:
  1. `actions/checkout@v4`.
  2. `actions/setup-python@v5` con `python-version: "3.11"` (de `runtime.txt`).
  3. `pip install -e ".[dev]"` (o equivalente a lo que ya hace T4.9 `pip install .` más las deps de `dev`).
  4. `ruff check .`
  5. `pytest -q` (ejecutar con `pythonpath` ya resuelto por `pyproject.toml`; sin red, sin variables de entorno de LLM/JEV/LangSmith — si algún test las necesita, es un defecto a reportar, no a silenciar con un secreto en CI).
  6. `python eval/run_motor.py`; el job **falla** si el proceso sale con código distinto de 0 (el ajuste del §0 asegura que ese código de salida refleje `unsafe_pay > 0`).
- Job `frontend` (puede correr en paralelo al de backend, sin dependencia entre ambos):
  1. `actions/checkout@v4`.
  2. `actions/setup-node@v4` con la versión de Node que ya usa `frontend/package.json` (o LTS vigente si el archivo no la fija).
  3. `npm ci` en `frontend/`.
  4. `npm run lint`.
  5. `npx tsc --noEmit`.
  6. `npm test` (vitest).
- Sin secretos en ningún paso. Sin `env:` con claves de LLM, JEV o LangSmith. Si un paso necesita una variable, debe tener un valor sintético inofensivo o el paso no se añade.

## 4. `codeql.yml`

- Disparadores: `push`, `pull_request` y, opcionalmente, un cron semanal (`schedule`); si se añade cron, documentarlo en el PR, no es obligatorio para el gate.
- `permissions`: `contents: read`, `security-events: write` (el mínimo que CodeQL necesita para subir resultados), `actions: read`.
- `languages: [python, javascript-typescript]` (una matriz, una entrada por lenguaje).
- Pasos: `github/codeql-action/init@v3`, `github/codeql-action/analyze@v3`, pinned por versión mayor. Sin build manual adicional si el autobuild de CodeQL basta para ambos lenguajes; si no basta para Python, usar el paso de `setup-python` del job de arriba como referencia, sin duplicar instalación innecesaria.

## 5. Fuera de alcance

- Configurar reglas de rama protegida en GitHub (requerir que el PR pase CI antes de mergear). Es un ajuste de configuración del repositorio en GitHub, no un archivo de este repo; se anota como pendiente humano.
- Hacer que Render espere a CI. Ver §1: no se afirma que eso quede resuelto.
- Desplegar, publicar un release, o subir artefactos de build.
- Cambiar `eval/run_motor.py` más allá de, si hace falta, el código de salida del §0.
- Añadir cobertura de tests (`coverage`), linters nuevos para Python o JS, o Dependabot. CodeQL y el pipeline de pytest/ruff/vitest ya existentes son el alcance.
- Ejecutar `eval/run_eval.py`, el holdout o los adversariales en CI: necesitan red y secretos.

## 6. Criterios de aceptación

1. `.github/workflows/ci.yml` existe, con los dos jobs del §3, `permissions: contents: read`, acciones pinneadas por versión mayor.
2. `.github/workflows/codeql.yml` existe, con la matriz `python` + `javascript-typescript`, permisos mínimos, acciones pinneadas.
3. Un push o PR de prueba (o una corrida local equivalente de cada paso, documentada en el diff si no hay forma de disparar Actions desde esta sesión) muestra: `ruff check .` ok, `pytest -q` en verde, `eval/run_motor.py` con `unsafe_pay=0` y el job en verde; si `unsafe_pay` fuera mayor que 0, el job de backend debe fallar (documentar cómo se verificó esto sin forzar un `unsafe_pay` real, por ejemplo revisando el código de salida del script con un golden de prueba aparte, sin tocar `data/golden/dev.json`).
4. El README o el tablero dicen, en una frase, que el gate de eval está cableado en CI (GitHub Actions) y no en el despliegue de Render, a menos que el humano confirme lo contrario.
5. Diff limpio: solo `.github/`, y el ajuste puntual de `eval/run_motor.py` si hacía falta (documentado). Sin cambios en `backend/app/`, `frontend/app/`, `data/` ni `eval/reports/`.
6. `docs/TASK_BOARD.md`: T6.4 pasa a HECHA. La nota de G5 (fila T5.6, §4 de `docs/T5_6_SPEC.md`) puede actualizarse para decir que el gate ya está en CI, si T6.4 llegó HECHA antes de que T5.6 se audite de nuevo.
7. Fila en `docs/AI_USAGE_LOG.md`.
8. Commit y push con el mensaje del §7.

## 7. Commit

```text
T6.4: add CI with eval unsafe_pay gate and CodeQL
```

## 8. Mensaje para la sesión que implementa

```text
Implementa T6.4 según docs/T6_4_SPEC.md. Decisión D055. Depende de T5.7
(el import roto de backend.app.* no debe tumbar la CI por una razón ajena).
No existe .github/ en el repo: créalo.
ci.yml: push y pull_request, permissions contents: read, acciones pinneadas
por versión mayor (checkout@v4, setup-python@v5, setup-node@v4). Job
backend: Python 3.11 (runtime.txt), pip install -e ".[dev]", ruff check .,
pytest -q, y python eval/run_motor.py que falle el job si unsafe_pay > 0
(revisa el código de salida real del script antes de asumir que ya falla).
No uses eval/run_eval.py: necesita red y claves; run_motor.py no. Job
frontend: npm ci, lint, tsc --noEmit, vitest, en frontend/. Sin secretos en
ningún paso.
codeql.yml: matriz python + javascript-typescript, permisos mínimos
(contents: read, security-events: write, actions: read), codeql-action
init/analyze@v3.
No hagas que Render espere a CI: eso no se puede resolver desde este repo.
Dilo tal cual en el tablero y en el README si corresponde.
Al terminar: evidencia de los comandos en verde, tablero y AI_USAGE_LOG.
Commit y push: T6.4: add CI with eval unsafe_pay gate and CodeQL
```
