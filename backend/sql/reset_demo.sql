-- REINICIO DE DATOS DE LA DEMO — DESTRUCTIVO.
--
-- Borra TODAS las decisiones, la cadena de huellas, los acuerdos, las reglas
-- guardadas, las empresas y las membresías (T9.8). auth.users de Supabase no se
-- toca. Úsalo solo en la base de la demo, antes de presentarla.
--
-- Después de correrlo:
--   1. Reinicia el servicio en Render: al arrancar recrea la empresa demo
--      «P.J Gorman» (USD) y vuelve a sembrar sus reglas desde data/rules.json.
--   2. Siembra política, acuerdos y adjunta tu usuario de Supabase a la demo:
--        ADMIN_API_KEY=<clave> python backend/scripts/seed_demo.py --apply --with-rules \
--          --member-user-id <uuid de Supabase> --member-email <correo> --role admin
--   3. Comprueba GET /decisions/verify-chain → {"ok": true, ...}
--
-- La cadena de huellas vuelve a empezar desde el génesis: esto solo es
-- aceptable en la demo (T9.3), nunca con datos reales.

BEGIN;
TRUNCATE TABLE decision_record, chain_entries, vendor_agreement_version, rules_document,
    company_members, companies
    RESTART IDENTITY;
COMMIT;
