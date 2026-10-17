# Frontend — Blinka

Next.js (App Router) + TypeScript estricto. Fase F4.

## Pantallas disponibles

- **`/reglas`** — edición del `RulesConfig` vigente vía proxy same-origin a `GET`/`PUT /rules` (T4.3).
- **`/decisiones/[id]`** — ficha de un `DecisionRecord` (solo lectura) vía proxy `GET /api/decisions/{id}` (T4.5). El `{id}` es `DecisionRecord.id`, no `invoice_id`.

Otras rutas (`/decisiones` índice, `/aprobaciones`, `/metricas`, `/subir`, etc.) siguen fuera de alcance hasta sus tareas T4.x.

## Desarrollo local

1. API en `127.0.0.1:8000` (sesión local; ver `docs/T4_3_SPEC.md` §8).
2. Copiar `frontend/.env.example` → `frontend/.env.local` y ajustar `API_URL` si hace falta.
3. En `frontend/`:

```bash
npm install
npm run dev
```

Abrir [http://localhost:3000/reglas](http://localhost:3000/reglas).

## Comprobaciones

```bash
npx tsc --noEmit
npm run lint
npm test
```

El navegador llama a `/api/rules`; Next reenvía a `${API_URL}/rules` (sin CORS en el cliente).

## Referencias

- `docs/T4_3_SPEC.md` — contrato de la pantalla de reglas.
- `docs/T4_5_SPEC.md` — contrato del detalle de decisión.
- `AGENTS.md` — invariantes (I2, I6, I8).
