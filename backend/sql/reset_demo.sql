-- REINICIO DE DATOS DE LA DEMO — DESTRUCTIVO.
--
-- Borra TODAS las decisiones, la cadena de huellas, los acuerdos y las reglas
-- guardadas. Úsalo solo en la base de la demo, antes de presentarla.
--
-- Después de correrlo:
--   1. Reinicia el servicio en Render: al arrancar vuelve a sembrar las reglas
--      desde data/rules.json (rules_document vacía).
--   2. Carga los acuerdos de ejemplo con auditoría:
--        ADMIN_API_KEY=<clave> python backend/scripts/seed_demo.py --apply
--   3. Comprueba GET /decisions/verify-chain → {"ok": true, "length": 3...}
--
-- La cadena de huellas vuelve a empezar desde el génesis: esto solo es
-- aceptable en la demo (T9.3), nunca con datos reales.

BEGIN;
TRUNCATE TABLE decision_record, chain_entries, vendor_agreement_version, rules_document
    RESTART IDENTITY;
COMMIT;
