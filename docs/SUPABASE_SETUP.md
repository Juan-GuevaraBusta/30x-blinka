# Supabase (plan gratis) para Blinka

El plugin de Supabase en Cursor **no crea proyectos en tier 0 USD** sin confirmar un cargo de referencia (~10 USD/mes en la API). Para la hackathon, crea el proyecto **manualmente** en el plan **Free**:

1. Abre [https://supabase.com/dashboard](https://supabase.com/dashboard) e inicia sesión.
2. **New project** → organización `Juan-GuevaraBust's Org`.
3. Nombre: `blinka`. Región: **South America (São Paulo)** (`sa-east-1`).
4. Contraseña de base de datos: guárdala en un gestor (no en el repo).
5. Espera estado **Active**.

## Enlaces (sustituye `<ref>` por el id del proyecto, p. ej. `abcdefghijklmnop`)

| Qué | URL |
|-----|-----|
| Panel | `https://supabase.com/dashboard/project/<ref>` |
| API y claves | `https://supabase.com/dashboard/project/<ref>/settings/api` |
| Base de datos | `https://supabase.com/dashboard/project/<ref>/settings/database` |
| Auth (desactivar confirmación de email) | `https://supabase.com/dashboard/project/<ref>/auth/providers` |

En **Email** → desactiva **Confirm email** para que registro e inicio de sesión entren al momento.

## Variables locales (no commitear)

**Raíz** [`.env`](.env):

- `DATABASE_URL=postgresql+psycopg://postgres.[ref]:[PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres` (URI de *Connection pooling*, modo Session, desde Database settings).
- Opcional documentación: `SUPABASE_PROJECT_REF=<ref>`.

**Frontend** [`frontend/.env.local`](frontend/.env.local):

- `NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=` (clave **publishable** en Settings → API).

Arranca el API desde la **raíz** del repo (no desde `backend/`), con `.env` cargado:

```bash
set -a && source .env && set +a
PYTHONPATH=backend .venv/bin/uvicorn app.api.asgi:create_production_app --factory --host 127.0.0.1 --port 8000
```

Al primer arranque contra Postgres, el backend aplica RLS en tablas de la app; `REVOKE` a `anon`/`authenticated` solo si esos roles existen (Supabase). En Postgres de Render no hay esos roles y el arranque no debe fallar.

## Seguridad (demo hackathon)

- El front envía `X-User-Id` (id de Supabase Auth). **El API no verifica JWT** a propósito (KISS).
- No expongas `service_role` ni la contraseña de la base en el cliente.
