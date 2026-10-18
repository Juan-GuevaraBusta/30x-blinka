-- Esquema de Postgres/Supabase para el agente pagador de facturas.
--
-- Generado desde los modelos SQLAlchemy reales (backend/app/persistence/tables.py).
-- NO es obligatorio: el backend ejecuta lo mismo al arrancar en init_database()
-- (create_all + migraciones + bloqueo de acceso). Sirve para crear o revisar el
-- esquema a mano en el SQL Editor de Supabase. Es idempotente (IF NOT EXISTS).
--
-- T9.8 (D067): multiempresa. `companies` y `company_members` son la fuente de
-- verdad de la pertenencia; `auth.users` de Supabase NO se modifica.
--
-- Fuera de este archivo, a propósito:
--   * La bandeja de correos (T9.2) vive en memoria; no tiene tabla todavía.
-- Regenerar si cambian los modelos: ver backend/tests/test_persistence_lockdown.py.

-- 1. Tablas

CREATE TABLE IF NOT EXISTS chain_entries (
	seq SERIAL NOT NULL, 
	kind VARCHAR NOT NULL, 
	ref_id VARCHAR NOT NULL, 
	payload TEXT, 
	prev_hash VARCHAR NOT NULL, 
	record_hash VARCHAR NOT NULL, 
	company_id VARCHAR, 
	PRIMARY KEY (seq)
);

CREATE TABLE IF NOT EXISTS companies (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	name_key VARCHAR NOT NULL, 
	base_currency VARCHAR NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_by VARCHAR, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name_key)
);

CREATE TABLE IF NOT EXISTS company_members (
	id SERIAL NOT NULL, 
	company_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	approver_groups TEXT NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_company_member UNIQUE (company_id, user_id), 
	UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS ix_company_members_company_id ON company_members (company_id);

CREATE TABLE IF NOT EXISTS decision_record (
	id VARCHAR NOT NULL, 
	owner_id VARCHAR NOT NULL, 
	invoice_id VARCHAR NOT NULL, 
	decision VARCHAR NOT NULL, 
	position INTEGER NOT NULL, 
	payload TEXT NOT NULL, 
	company_id VARCHAR, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_decision_owner_invoice UNIQUE (owner_id, invoice_id)
);

CREATE INDEX IF NOT EXISTS ix_decision_record_company_id ON decision_record (company_id);

CREATE INDEX IF NOT EXISTS ix_decision_record_owner_id ON decision_record (owner_id);

CREATE TABLE IF NOT EXISTS rules_document (
	id SERIAL NOT NULL, 
	payload TEXT NOT NULL, 
	company_id VARCHAR, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_rules_document_company_id ON rules_document (company_id);

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
	company_id VARCHAR, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_agreement_company_vendor_version UNIQUE (company_id, vendor_key, version)
);

CREATE INDEX IF NOT EXISTS ix_vendor_agreement_version_company_id ON vendor_agreement_version (company_id);

CREATE INDEX IF NOT EXISTS ix_vendor_agreement_version_vendor_key ON vendor_agreement_version (vendor_key);

-- 1b. Bases creadas antes de T9.8: agregar company_id y asignar la empresa demo
-- (lo mismo que hace ensure_company_tenancy al arrancar).

ALTER TABLE rules_document           ADD COLUMN IF NOT EXISTS company_id VARCHAR;
ALTER TABLE vendor_agreement_version ADD COLUMN IF NOT EXISTS company_id VARCHAR;
ALTER TABLE decision_record          ADD COLUMN IF NOT EXISTS company_id VARCHAR;
ALTER TABLE chain_entries            ADD COLUMN IF NOT EXISTS company_id VARCHAR;

INSERT INTO companies (id, name, name_key, base_currency, is_demo, created_by, created_at)
VALUES ('demo-acme', 'Acme Demo Inc.', 'acme demo inc.', 'USD', TRUE, NULL, now()::text)
ON CONFLICT (id) DO NOTHING;

UPDATE rules_document           SET company_id = 'demo-acme' WHERE company_id IS NULL;
UPDATE vendor_agreement_version SET company_id = 'demo-acme' WHERE company_id IS NULL;
UPDATE decision_record          SET company_id = 'demo-acme' WHERE company_id IS NULL;
UPDATE chain_entries            SET company_id = 'demo-acme' WHERE company_id IS NULL;

ALTER TABLE vendor_agreement_version DROP CONSTRAINT IF EXISTS uq_agreement_vendor_version;
CREATE UNIQUE INDEX IF NOT EXISTS uq_agreement_company_vendor_version_idx
    ON vendor_agreement_version (company_id, vendor_key, version);


-- 2. Bloqueo de acceso público (T5.9 + Supabase)
-- El backend se conecta con DATABASE_URL (rol con dueño de las tablas). El
-- navegador usa la clave pública "anon" de Supabase: ninguna tabla debe ser
-- legible ni escribible por "anon" o "authenticated" vía la API REST de Supabase.
-- RLS activado sin políticas = todo denegado para esos roles.

ALTER TABLE rules_document           ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_record          ENABLE ROW LEVEL SECURITY;
ALTER TABLE chain_entries            ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_agreement_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies                ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_members          ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE rules_document           FROM anon, authenticated;
REVOKE ALL ON TABLE decision_record          FROM anon, authenticated;
REVOKE ALL ON TABLE chain_entries            FROM anon, authenticated;
REVOKE ALL ON TABLE vendor_agreement_version FROM anon, authenticated;
REVOKE ALL ON TABLE companies                FROM anon, authenticated;
REVOKE ALL ON TABLE company_members          FROM anon, authenticated;

-- 3. Vista para revisar quién pertenece a qué empresa (solo en Supabase).
-- auth.users solo se lee; la vista no es accesible para anon/authenticated.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN
        EXECUTE $view$
            CREATE OR REPLACE VIEW public.users_with_company AS
            SELECT u.id            AS user_id,
                   u.email         AS email,
                   c.id            AS company_id,
                   c.name          AS company_name,
                   m.role          AS role,
                   m.approver_groups AS approver_groups,
                   c.base_currency AS base_currency,
                   c.is_demo       AS is_demo
            FROM auth.users u
            JOIN public.company_members m ON m.user_id = u.id::text
            JOIN public.companies c ON c.id = m.company_id
        $view$;
        EXECUTE 'REVOKE ALL ON public.users_with_company FROM anon, authenticated';
    END IF;
END
$$;

-- 4. Notas
-- * chain_entries es solo-anexar por diseño (T5.10): la app nunca hace UPDATE ni
--   DELETE (salvo el relleno único de company_id en filas viejas, arriba).
-- * Las reglas de la empresa demo (data/rules.json) las siembra el backend al
--   arrancar si no tiene rules_document. Una empresa nueva empieza sin reglas
--   (todo ESCALAR) hasta que un admin las guarda.
