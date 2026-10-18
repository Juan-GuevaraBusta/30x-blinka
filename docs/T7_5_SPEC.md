# Spec T7.5 — Pantallas para el equipo de finanzas: política, proveedores y aprobaciones

Dueño: **Frontend** (`frontend/`). Carril: B. Colabora: **API** (solo lectura de los endpoints de T7.1, T7.2 y T7.4). Skill de dominio: `frontend-design` (TOTAL en UI); proceso: `vercel-react-best-practices` PARCIAL.

Prioridad: **P1**. Depende de: T7.1 (política y `GET /decisions/{id}/approval`); la vista de proveedor depende de T7.2; la acción de alta, de T7.4. Cada pantalla puede salir por separado.

Estado: contrato para la sesión que **implemente** T7.5. Este archivo no cierra la tarea.

Decisión que fija este contrato: **D059** (`docs/DECISIONS_LOG.md`).

## 0. Para el agente que implementa

Pegar este archivo entero en el primer mensaje. Declarar `frontend-design` y leerla. Lecturas:

- `docs/T7_1_SPEC.md` §2 y §4, `docs/T7_2_SPEC.md` §2–§3, `docs/T7_4_SPEC.md` §2.
- `frontend/app/` (`GlobalNav.tsx`, `/reglas`, `/aprobaciones`, `/decisiones/[id]`) y `frontend/lib/` (proxies que inyectan `X-Admin-Key` en servidor, T5.9; 502 `upstream_unreachable`, T6.7).
- `docs/T6_7_SPEC.md` y D057 (marca solo en texto; sin logo ni diseño de Blinka).

## 1. Qué es T7.5

El usuario es el equipo de finanzas de una empresa cliente de Blinka que paga a sus proveedores (D059). Necesita ver y editar su propia política de aprobación, entender el calendario de cada proveedor y saber, en la cola, cuántas firmas faltan y por qué ruta. Todo en español llano, sin códigos internos como texto principal.

## 2. Alcance

- **Diseño de ajustes:** `/ajustes` con navegación lateral izquierda tipo espacio de trabajo (secciones: «Reglas generales» → enlaza a `/reglas`, «Política de aprobación», «Proveedores»). En móvil la navegación lateral pasa a lista arriba. Estilo propio; **no copiar el diseño, colores ni logo de la app de Blinka**.
- **Editor de política** (`/ajustes/politica`): tabla de rutas en orden (columnas: Nombre, Cuándo aplica, Quién aprueba, Aprobaciones). Agregar, editar, borrar y reordenar con botones subir/bajar (sin arrastrar obligatorio). La última fila es «Todo lo demás» y no se puede borrar. Guarda con `PUT /rules`; los errores 422 del validador se muestran junto a la fila. Texto fijo visible: «Estas rutas solo pueden pedir más aprobaciones; nunca autorizan un pago que las reglas frenen o escalen.»
- **Vista de proveedor** (`/ajustes/proveedores` y `/ajustes/proveedores/[nombre]`): lista de proveedores permitidos; en el detalle, calendario de la serie (T7.2) por periodo con estados «Pagado», «Pendiente de aprobación», «Frenado», «Sin factura» y el total pagado frente al tope. Si no hay serie configurada: «Este proveedor no tiene un calendario de pagos.»
- **Cola de aprobaciones** (`/aprobaciones` y `/decisiones/[id]`): por fila, «1 de 2 aprobaciones» y «Ruta: Alto monto». En el detalle: quién ya aprobó, quién puede aprobar y, si `payment_ready=false` por otros chequeos, «Aprobaciones completas, pero falta resolver: Cuadra con contrato (R06).»
- **Alta de proveedor** (T7.4): botón y aviso en `/decisiones/[id]` cuando R01 falló.
- Proxies nuevos en `frontend/app/api/` para `GET /decisions/{id}/approval` y `POST /decisions/{id}/add-beneficiary`, con el mismo patrón de clave en servidor y 502 explícito.

Copias de ejemplo (plantillas fijas, nunca texto de LLM):

| Lugar | Texto |
|---|---|
| Fila de cola | «Falta 1 aprobación de Finanzas o CFO (ruta Alto monto).» |
| Detalle, serie | «Periodo 2026-03 ya pagado con la factura GX-0312.» |
| Política vacía | «Sin política propia: toda factura escalada necesita una aprobación.» |

## 3. Fuera de alcance

- Editar `approver_groups` (viven en `data/company.json`).
- Arrastrar y soltar obligatorio, modo oscuro nuevo, internacionalización a otros idiomas.
- Cualquier cálculo de decisión en el navegador: la UI solo muestra lo que devuelve el API.

## 4. Criterios de aceptación

1. `cd frontend && npx tsc --noEmit && npm run lint && npm test` — ok, con pruebas vitest para: tabla de rutas (agregar, reordenar, no borrar «Todo lo demás»), texto «x de N» a partir de una respuesta simulada de `/approval`, estados del calendario.
2. Error 422 de `PUT /rules` se muestra en la fila; 502 del proxy se muestra como «No se pudo conectar con el servidor».
3. Ninguna pantalla muestra un botón de pagar ni cambia `decision`; aprobar sigue llamando al endpoint existente.
4. Revisión a 375 px de ancho sin desplazamiento horizontal; navegación con teclado en la tabla de rutas.
5. Evidencia de prueba manual o Playwright de las tres pantallas en `docs/TASK_BOARD.md`; tablero T7.5 → HECHA (o PARCIAL con la pantalla que faltó); fila en `docs/AI_USAGE_LOG.md`; commit y push con el §5.

## 5. Commit

```text
T7.5: finance team settings for approval policy, vendors and approvals
```

## 6. Mensaje para la sesión que implementa

```text
Implementa T7.5 según docs/T7_5_SPEC.md. Decisión D059. Skill
frontend-design. Usuario: equipo de finanzas de un cliente de Blinka.
/ajustes con navegación lateral (Reglas generales, Política de aprobación,
Proveedores); editor de rutas en tabla ordenada con «Todo lo demás» fijo
al final; vista de proveedor con calendario de la serie (Pagado, Pendiente,
Frenado, Sin factura) y total frente al tope; en /aprobaciones y la ficha,
«x de N aprobaciones» y la ruta aplicada desde GET /decisions/{id}/approval.
Español llano, sin copiar diseño ni logo de Blinka, sin decidir nada en el
navegador. Proxies con clave en servidor y 502 explícito. Al terminar: tsc,
lint, vitest, revisión a 375 px, tablero y AI_USAGE_LOG. Commit y push:
T7.5: finance team settings for approval policy, vendors and approvals
```
