-- Esquema de Postgres/Supabase para el agente pagador de facturas.
--
-- Generado desde los modelos SQLAlchemy reales (backend/app/persistence/tables.py).
-- NO es obligatorio: el backend ejecuta lo mismo al arrancar en init_database()
-- (create_all + migraciones + bloqueo de acceso). Sirve para crear o revisar el
-- esquema a mano en el SQL Editor de Supabase. Es idempotente (IF NOT EXISTS).
--
-- Fuera de este archivo, a propósito:
--   * La bandeja de correos (T9.2) vive en memoria; no tiene tabla todavía.
--   * La configuración por cuenta (T9.6) aún no está implementada.
-- Regenerar si cambian los modelos: ver backend/tests/test_persistence_lockdown.py.

-- 1. Tablas

CREATE TABLE IF NOT EXISTS chain_entries (
	seq SERIAL NOT NULL, 
	kind VARCHAR NOT NULL, 
	ref_id VARCHAR NOT NULL, 
	payload TEXT, 
	prev_hash VARCHAR NOT NULL, 
	record_hash VARCHAR NOT NULL, 
	PRIMARY KEY (seq)
);

CREATE TABLE IF NOT EXISTS decision_record (
	id VARCHAR NOT NULL, 
	owner_id VARCHAR NOT NULL, 
	invoice_id VARCHAR NOT NULL, 
	decision VARCHAR NOT NULL, 
	position INTEGER NOT NULL, 
	payload TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_decision_owner_invoice UNIQUE (owner_id, invoice_id)
);

CREATE INDEX IF NOT EXISTS ix_decision_record_owner_id ON decision_record (owner_id);

CREATE TABLE IF NOT EXISTS rules_document (
	id SERIAL NOT NULL, 
	payload TEXT NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS vendor_agreement_version (
	id SERIAL NOT NULL, 
	vendor_key VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	terms_json TEXT NOT NULL, 
	source_sha256 VARCHAR, 
	spans_json TEXT NOT NULL, 
	confirmed_by VARCHAR NOT NULL, 
	confirmed_at VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_agreement_vendor_version UNIQUE (vendor_key, version)
);

CREATE INDEX IF NOT EXISTS ix_vendor_agreement_version_vendor_key ON vendor_agreement_version (vendor_key);


-- 2. Bloqueo de acceso público (T5.9 + Supabase)
-- El backend se conecta con DATABASE_URL (rol con dueño de las tablas). El
-- navegador usa la clave pública "anon" de Supabase: ninguna tabla debe ser
-- legible ni escribible por "anon" o "authenticated" vía la API REST de Supabase.
-- RLS activado sin políticas = todo denegado para esos roles.

ALTER TABLE rules_document           ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_record          ENABLE ROW LEVEL SECURITY;
ALTER TABLE chain_entries            ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_agreement_version ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE rules_document           FROM anon, authenticated;
REVOKE ALL ON TABLE decision_record          FROM anon, authenticated;
REVOKE ALL ON TABLE chain_entries            FROM anon, authenticated;
REVOKE ALL ON TABLE vendor_agreement_version FROM anon, authenticated;

-- 3. Notas
-- * chain_entries es solo-anexar por diseño (T5.10): la app nunca hace UPDATE ni
--   DELETE. Para reforzarlo en la base se podría revocar UPDATE/DELETE también al
--   rol del backend; no se hace aquí porque el reinicio de la demo (T9.3) aún no
--   está definido.
-- * Las reglas iniciales (data/rules.json) las siembra el backend al arrancar si
--   rules_document está vacía.
