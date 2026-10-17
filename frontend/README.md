# Frontend — Blinka

Next.js (App Router) + TypeScript estricto. Fase F4.

## Pantallas disponibles

- **`/reglas`** — edición del `RulesConfig` vigente vía proxy same-origin a `GET`/`PUT /rules` (T4.3).
- **`/decisiones`** — listado con filtros Pagadas / Frenadas / Pendientes vía `GET /api/decisions?decision=` (T4.4).
- **`/decisiones/[id]`** — ficha de un `DecisionRecord` (solo lectura) vía proxy `GET /api/decisions/{id}` (T4.5). El `{id}` es `DecisionRecord.id`, no `invoice_id`.
- **`/aprobaciones`** — cola `ESCALAR` y eventos humanos approve/reject (T4.6).
- **`/metricas`** — lectura de `GET /metrics` (autonomía y `unsafe_pay`; T4.7).
- **`/subir`** — subida de factura sintética vía `POST /api/invoices` (proxy multipart a `${API_URL}/invoices`; T4.8). Éxito solo con HTTP 201 y cuerpo `DecisionRecord`.

T4.9 (deploy público) sigue fuera de este README hasta que haya URL en producción.

## Desarrollo local

1. API en `127.0.0.1:8000` (sesión local; ver `docs/T4_3_SPEC.md` §8).
2. Copiar `frontend/.env.example` → `frontend/.env.local` y ajustar `API_URL` si hace falta.
3. En `frontend/`:

```bash
npm install
npm run dev
```

Abrir [http://localhost:3000/reglas](http://localhost:3000/reglas) o [http://localhost:3000/subir](http://localhost:3000/subir) con el API en marcha.

## Comprobaciones

```bash
npx tsc --noEmit
npm run lint
npm test
```

El navegador llama a rutas `/api/*` en el mismo origen; Next reenvía a `${API_URL}` (sin CORS en el cliente). Subida: `POST /api/invoices` → `POST /invoices` con `multipart/form-data` (Next no fija `Content-Type`; el boundary lo añade `fetch`).

## Referencias

- `docs/T4_3_SPEC.md` — contrato de la pantalla de reglas.
- `docs/T4_4_SPEC.md` — listado de decisiones.
- `docs/T4_5_SPEC.md` — contrato del detalle de decisión.
- `docs/T4_6_SPEC.md` — cola de aprobaciones.
- `docs/T4_7_SPEC.md` — métricas de evaluación.
- `docs/T4_8_SPEC.md` — subida de factura desde la UI.
- `AGENTS.md` — invariantes (I2, I6, I8).
