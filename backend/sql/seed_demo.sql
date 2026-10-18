-- Semilla de demo para Postgres/Supabase (bypassa la cadena de auditoria) --------------------
--
-- Estos INSERT escriben directamente en `rules_document` y
-- `vendor_agreement_version` sin pasar por la API real (`PUT /rules`,
-- `PUT /agreements/{vendor_key}`), por lo que NO agregan la fila
-- correspondiente en `chain_entries` que el flujo de confirmacion real
-- (`SqlStore.confirm_agreement`) escribe en la misma transaccion.
--
-- Para la demo, prefiere `backend/scripts/seed_demo.py --apply --with-rules`
-- (usa la API real y mantiene la cadena de auditoria intacta). Este archivo
-- SQL es solo para inspeccion rapida local -- por ejemplo abrir la base de
-- datos directamente y ver datos de ejemplo ya cargados -- nunca para un
-- entorno donde el gate de auditoria deba quedar completo.
--
-- Generado por backend/scripts/generate_seed_sql.py a partir de los mismos
-- modelos Pydantic (RulesConfig / VendorAgreement) que usa seed_demo.py.
-- No editar a mano: regenerar con ese script si cambian los datos de demo.


-- 0. Empresa demo (T9.8)

INSERT INTO companies (id, name, name_key, base_currency, is_demo, created_by, created_at)
VALUES ('demo-acme', 'P.J Gorman', 'p.j gorman', 'USD', TRUE, NULL, '2026-01-01T00:00:00+00:00')
ON CONFLICT (id) DO NOTHING;

-- 1. Reglas base (rules_document)

INSERT INTO rules_document (id, payload, company_id)
SELECT COALESCE((SELECT MAX(id) FROM rules_document), 0) + 1, '{"company":{"name":"P.J Gorman","base_currency":"USD"},"limits":{"per_payment":5000.0,"per_period":{"type":"calendar_month","amount":20000.0}},"human_approval_threshold":3000.0,"allowed_beneficiaries":["Globex LLC","Initech SAS","Norteclaro SpA","Andesbyte SAS","Pampaluz Ltda","Rioseco Servicios SAS","Luma Austral SA","Cuotasur SAS"],"department_budgets":{"Ingenieria":8000.0,"Marketing":5000.0},"approvers":{"Ingenieria":"finanzas@demo.test","default":"cfo@demo.test"},"manual_blocks":[],"on_fail":{"R01":"FRENAR","R02":"ESCALAR","R03":"ESCALAR","R04":"ESCALAR","R05":"FRENAR","R06":"ESCALAR","R07":"FRENAR","R08":"ESCALAR","R09":"ESCALAR","R10":"ESCALAR","R11":"ESCALAR","R12":"FRENAR","R13":"ESCALAR","R14":"ESCALAR","R15":"ESCALAR","R16":"FRENAR","R17":"FRENAR","R19":"FRENAR","R20":"ESCALAR","R21":"ESCALAR"},"jev_thresholds":{"J1":0.9,"J2":0.9,"J3":0.85,"J4":0.85,"J6":0.85,"J7":0.5},"approval_policy":{"routes":[{"id":"high-amount-2of-finanzas-cfo","match":{"amount_base_gte":3000.0,"amount_base_lt":null,"beneficiary":null,"department":null,"invoice_type":null},"require":{"mode":"approvals","min_approvals":2,"from_groups":["finanzas","cfo"]}},{"id":"catch-all","match":{"amount_base_gte":null,"amount_base_lt":null,"beneficiary":null,"department":null,"invoice_type":null},"require":{"mode":"auto","min_approvals":null,"from_groups":[]}}]},"payment_series":[],"variable_pricing":[],"vendor_onboarding":null,"vendor_additions":[],"splitting_window_days":30}', 'demo-acme'
WHERE NOT EXISTS (SELECT 1 FROM rules_document WHERE company_id = 'demo-acme');

-- 2. Acuerdos de proveedores demo (vendor_agreement_version, v1 activa)

INSERT INTO vendor_agreement_version (company_id, vendor_key, version, terms_json, source_sha256, spans_json, confirmed_by, confirmed_at, status)
VALUES (
    'demo-acme',
    'globex',
    1,
    '{"vendor_name":"Globex LLC","vendor_key":"globex","department":null,"currency":"USD","valid_from":"2026-01-01","valid_to":null,"sender_emails":[],"source_clauses":{},"kind":"retainer","periodicity":"monthly","amount":{"min":1200.0,"max":1200.0},"total_cap":null}',
    NULL,
    '[]',
    'cfo@demo.test',
    '2026-01-01T00:00:00+00:00',
    'active'
)
ON CONFLICT (company_id, vendor_key, version) DO NOTHING;

INSERT INTO vendor_agreement_version (company_id, vendor_key, version, terms_json, source_sha256, spans_json, confirmed_by, confirmed_at, status)
VALUES (
    'demo-acme',
    'andesbyte',
    1,
    '{"vendor_name":"Andesbyte SAS","vendor_key":"andesbyte","department":null,"currency":"USD","valid_from":"2026-01-01","valid_to":null,"sender_emails":[],"source_clauses":{},"kind":"hourly","unit":"hora","rate":45.0,"included_hours":160.0,"overtime":{"multiplier":1.5,"max_hours":40.0},"period_cap":10000.0}',
    NULL,
    '[]',
    'cfo@demo.test',
    '2026-01-01T00:00:00+00:00',
    'active'
)
ON CONFLICT (company_id, vendor_key, version) DO NOTHING;

INSERT INTO vendor_agreement_version (company_id, vendor_key, version, terms_json, source_sha256, spans_json, confirmed_by, confirmed_at, status)
VALUES (
    'demo-acme',
    'cuotasur',
    1,
    '{"vendor_name":"Cuotasur SAS","vendor_key":"cuotasur","department":null,"currency":"USD","valid_from":"2026-01-01","valid_to":null,"sender_emails":[],"source_clauses":{},"kind":"installments","items":[{"key":"q1","due_from":"2026-01-01","due_to":"2026-03-31","amount":2500.0},{"key":"q2","due_from":"2026-04-01","due_to":"2026-06-30","amount":2500.0},{"key":"q3","due_from":"2026-07-01","due_to":"2026-09-30","amount":2500.0},{"key":"q4","due_from":"2026-10-01","due_to":"2026-12-31","amount":2500.0}],"total_cap":10000.0}',
    NULL,
    '[]',
    'cfo@demo.test',
    '2026-01-01T00:00:00+00:00',
    'active'
)
ON CONFLICT (company_id, vendor_key, version) DO NOTHING;
