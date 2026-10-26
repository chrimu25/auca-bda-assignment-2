-- 2.2 Checks: counts, transfer audit, roles, validated constraints, indexes, sizes (1 GB = 1e9 bytes)
\pset pager off

\echo ================ Row counts against capture.py ================
SELECT 'customers' AS table_name, COUNT(*) AS loaded, 228000 AS expected, COUNT(*) = 228000 AS ok FROM customers
UNION ALL SELECT 'accounts',        COUNT(*), 248000,   COUNT(*) = 248000   FROM accounts
UNION ALL SELECT 'devices',         COUNT(*), 228600,   COUNT(*) = 228600   FROM devices
UNION ALL SELECT 'account_devices', COUNT(*), 285600,   COUNT(*) = 285600   FROM account_devices
UNION ALL SELECT 'transfers',       COUNT(*), 20003300, COUNT(*) = 20003300 FROM transfers;

\echo ================ Transfer audit against capture.py ================
SELECT COUNT(*)                                        AS transfers,
       MIN(occurred_at)                                AS min_occurred_at,
       MAX(occurred_at)                                AS max_occurred_at,
       to_timestamp(MIN(occurred_at))                  AS min_cat,
       to_timestamp(MAX(occurred_at))                  AS max_cat,
       SUM(amount_rwf::bigint)                         AS sum_amount_rwf,
       COUNT(*) = 20003300
         AND MIN(occurred_at) = 1788235200
         AND MAX(occurred_at) = 1790798399
         AND SUM(amount_rwf::bigint) = 231482327870    AS audit_matches_capture
FROM transfers;

\echo ================ Account roles ================
SELECT role, COUNT(*) AS accounts,
       CASE role WHEN 'person' THEN 240000 WHEN 'merchant' THEN 6000 WHEN 'agent' THEN 2000 END AS expected
FROM accounts GROUP BY role ORDER BY role;

\echo ================ Constraints (all must be validated) ================
SELECT conrelid::regclass AS table_name, conname AS constraint_name,
       CASE contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY' WHEN 'c' THEN 'CHECK' END AS type,
       convalidated AS validated,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid IN ('customers'::regclass, 'accounts'::regclass, 'devices'::regclass,
                   'account_devices'::regclass, 'transfers'::regclass)
ORDER BY conrelid::regclass::text, contype, conname;

SELECT COUNT(*) AS not_null_columns
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('customers','accounts','devices','account_devices','transfers')
  AND is_nullable = 'NO';

\echo ================ Indexes ================
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('customers','accounts','devices','account_devices','transfers')
ORDER BY tablename, indexname;

\echo ================ Sizes (GB = 1,000,000,000 bytes) ================
SELECT c.relname AS table_name,
       ROUND(pg_table_size(c.oid)   / 1e9, 4) AS data_gb,
       ROUND(pg_indexes_size(c.oid) / 1e9, 4) AS index_gb,
       ROUND(pg_total_relation_size(c.oid) / 1e9, 4) AS total_gb
FROM pg_class c
WHERE c.relname IN ('customers','accounts','devices','account_devices','transfers') AND c.relkind = 'r'
UNION ALL
SELECT 'ALL FIVE TABLES',
       ROUND(SUM(pg_table_size(c.oid))   / 1e9, 4),
       ROUND(SUM(pg_indexes_size(c.oid)) / 1e9, 4),
       ROUND(SUM(pg_total_relation_size(c.oid)) / 1e9, 4)
FROM pg_class c
WHERE c.relname IN ('customers','accounts','devices','account_devices','transfers') AND c.relkind = 'r'
ORDER BY 1;

SELECT ROUND(pg_database_size(current_database()) / 1e9, 4) AS database_size_gb;
