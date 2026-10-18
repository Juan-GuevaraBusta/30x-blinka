# Spec T6.1 — Guion de demo de 3 minutos

Dueño: **Docs & Judge**. Carril: A. Skill de dominio: NINGUNA (`docs/SKILLS_MAP.md`); proceso: `sales-enablement` PARCIAL (solo la forma de un guion de demo; es skill de marketing, no decide contenido del producto).

Depende de: **G4** (HECHA, `docs/DECISIONS_LOG.md` D040) y **G5** (PENDIENTE: depende de T5.1, T5.3, T5.6; T5.8 y T5.9 ya HECHA — `docs/STATUS.md`, `docs/TASK_BOARD.md`). T6.1 desbloquea **T6.2** y, junto con T6.2 y T6.3, cierra **G6**.

Estado: contrato para la sesión que **escribe** el guion. Este archivo no cierra la tarea ni escribe `docs/DEMO_SCRIPT.md` por sí mismo.

Decisión que fija este contrato: **D059** (`docs/DECISIONS_LOG.md`, usuario = equipo de finanzas de una empresa cliente de Blinka).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Skill `sales-enablement` (PARCIAL): solo cubre la forma (ritmo, ganchos, duración), no el contenido — el contenido sale de los documentos del producto, no de criterio de ventas.

Lecturas obligatorias antes de escribir una sola línea del guion:

- `docs/01_CONTEXT_AND_SCOPE.md` (ficha, D059: usuario = equipo de finanzas de un cliente de Blinka que paga a sus proveedores; qué entra/no entra; glosario PAGAR/FRENAR/ESCALAR).
- `docs/05_PHASES_AND_ROADMAP.md` línea T6.1 (frase de referencia: «factura normal pagada → duplicado frenado → monto alto escalado → aprobación humana → registro y traza → métricas»).
- `docs/TASK_BOARD.md` filas T6.1, T6.2, G5, G6 (dependencias y qué evidencia falta).
- `docs/T7_1_SPEC.md` §4 (aprobaciones «x de N», `GET /decisions/{id}/approval`), `docs/T7_2_SPEC.md` (R15–R17, series), `docs/T7_3_SPEC.md` (R19, variables) — las tres HECHA (fila T7.1/T7.2/T7.3 de `docs/TASK_BOARD.md`), para el bloque opcional de F7.
- `docs/04_RULES_AND_DECISION_SPEC.md` §R01–R19 (qué regla dispara cada caso; plantillas de explicación).
- `docs/STATUS.md` (qué métrica existe hoy y en qué archivo; `eval/reports/latest.md` **no existe todavía** — T5.1 PENDIENTE).
- Catálogo real de facturas: `data/invoices/dev/` (sin `catalog.json` propio; usar `data/golden/dev.json` para `expected_decision`/`expected_rules` por `invoice_id`) y `data/invoices/f7/catalog.json`.
- Rutas reales del frontend: `frontend/app/{page,reglas,decisiones,decisiones/[id],aprobaciones,metricas,subir,ajustes/*,entrar}` (listar con `ls`, no inventar una ruta).

## 1. Qué es T6.1

Un guion de demo de voz alta para quien presenta el proyecto: qué decir, qué pantalla mostrar, qué factura subir y en qué orden, en no más de 3 minutos. No es el video de respaldo (T6.2) ni el tablero de cierre (T6.3). El producto final de T6.1 es `docs/DEMO_SCRIPT.md`.

## 2. Alcance

- Escribir `docs/DEMO_SCRIPT.md` como **BORRADOR** mientras G5 esté PENDIENTE: encabezado explícito de que las cifras de autonomía dependen de T5.1/G5, con marcadores de posición (`[autonomía de latest.md]`) en vez de números inventados.
- Cada paso del guion nombra: la pantalla exacta (ruta real del frontend, p. ej. `/subir`, `/decisiones/{id}`, `/aprobaciones`, `/ajustes/politica`), el archivo de factura exacto a subir (ruta real bajo `data/invoices/dev/` o `data/invoices/f7/`, verificado contra `data/golden/dev.json` o `data/invoices/f7/catalog.json`), y la decisión/regla esperada citando esos archivos.
- Cada frase que el presentador dice en voz alta, si afirma una cifra o un hecho verificable, cita el archivo/reporte que la sostiene (`eval/reports/*.md`, `docs/STATUS.md`, `docs/DECISIONS_LOG.md`) o se retira del guion. Ninguna frase inventa una métrica que no está en un reporte commiteado.
- Incluir un **camino alterno** («si algo falla») para dos fallos previsibles: Render en frío (primera llamada al backend tarda o cae) y el LLM/verificador no responde o se degrada. El camino alterno usa decisiones **pre-sembradas** (registros ya existentes en el ambiente desplegado o en `data/golden/*.json`) para no depender de una llamada en vivo.
- Timing por paso (segundos u mm:ss), de modo que la suma no pase de 3:00.
- El guion puede incluir, como bloque claramente separado y opcional, un ejemplo de F7 (política de aprobación, serie o variable) citando `data/invoices/f7/catalog.json`; no es obligatorio para los 3 minutos base.

## 3. Fuera de alcance

- Grabar o editar el video de respaldo (T6.2) — eso cita este guion, no lo reemplaza.
- Congelar rama, etiquetar o armar la lista de entrega (T6.3).
- Generar el reporte de eval completa (T5.1) o cerrar G5: T6.1 **consume** esos artefactos cuando existan, no los crea.
- Tocar código, `data/`, `backend/`, `frontend/` (más allá de leer rutas para citarlas) o cualquier archivo de seguimiento fuera de `docs/DEMO_SCRIPT.md` y este spec.
- Editar `docs/TASK_BOARD.md`, `docs/DECISIONS_LOG.md`, `docs/AI_USAGE_LOG.md`, `README.md` o `JUDGE_GUIDE.md` desde esta tarea (los actualiza quien cierra T6.1, no este contrato).

## 4. Criterios de aceptación

1. `docs/DEMO_SCRIPT.md` existe, está marcado como BORRADOR con la razón (cifras pendientes de T5.1/G5), y la suma de los tiempos por paso es ≤ 3:00.
2. Cada paso nombra una pantalla real (ruta verificada en `frontend/app/`) y, cuando aplica, un archivo de factura real (verificado en `data/invoices/dev/` o `data/invoices/f7/`, con su `expected_decision`/`expected_rules` tomado de `data/golden/dev.json` o `data/invoices/f7/catalog.json`, no inventado).
3. Toda frase hablada que afirme una cifra, una regla o un resultado cita el archivo o reporte exacto que la respalda (p. ej. `docs/STATUS.md`, `eval/reports/g3_closure_2026-10-17.md`, `data/golden/dev.json`); si no hay archivo que la sostenga, la frase se retira o se marca como marcador de posición explícito.
4. El guion incluye una sección «si algo falla» con al menos dos fallos cubiertos (Render en frío; LLM/verificador no responde) y su salida (decisión pre-sembrada o registro ya existente), sin dejar al presentador sin plan.
5. Ninguna métrica de autonomía/seguridad/explicabilidad aparece como cifra fija si no existe hoy un reporte commiteado que la sostenga; donde el valor real todavía no existe, aparece un marcador de posición legible.
6. `git diff --check` limpio (sin conflictos de espacio en blanco) sobre los archivos tocados por esta tarea.

## 5. Commit

```text
T6.1: write 3-minute demo script (draft pending T5.1/G5 figures)
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T6.1 según docs/T6_1_SPEC.md. Decisión D059. Usuario: equipo de
finanzas de un cliente de Blinka. Escribe docs/DEMO_SCRIPT.md como BORRADOR
(cifras de autonomía pendientes de T5.1/G5: usa marcadores de posición, no
inventes números). Cada paso nombra la pantalla real (ruta de frontend/app)
y el archivo de factura real (data/invoices/dev/ o data/invoices/f7/,
decisión esperada tomada de data/golden/dev.json o
data/invoices/f7/catalog.json). Toda frase hablada que afirme una cifra o
un hecho cita el archivo/reporte exacto o se retira. Incluye un camino
alterno «si algo falla» para Render en frío y para el LLM/verificador sin
respuesta, usando decisiones pre-sembradas. Timing por paso, suma ≤ 3:00.
No tocar código, data/, TASK_BOARD, DECISIONS_LOG, AI_USAGE_LOG, README ni
JUDGE_GUIDE desde esta tarea. Al terminar: git diff --check limpio.
```
