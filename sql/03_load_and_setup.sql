-- 2.2 Bulk load (timed) then keys, indexes and ANALYZE (timed separately).
-- Run from the project root (CSV paths are relative): psqlmm -f sql/03_load_and_setup.sql
-- Start from empty tables: run sql/01_schema.sql first.
\pset pager off
\timing on

-- ---------------- PHASE 1: LOADING ----------------
SELECT extract(epoch FROM clock_timestamp()) AS load_t0, clock_timestamp() AS load_start_cat \gset
\echo Loading started :load_start_cat

\copy customers FROM 'data/customers.csv' CSV HEADER
\copy devices FROM 'data/devices.csv' CSV HEADER
\copy accounts FROM 'data/accounts.csv' CSV HEADER
\copy account_devices FROM 'data/account_devices.csv' CSV HEADER
\copy transfers FROM 'data/transfers.csv' CSV HEADER

SELECT extract(epoch FROM clock_timestamp()) AS load_t1, clock_timestamp() AS load_end_cat \gset

-- ---------------- PHASE 2: KEYS, INDEXES, ANALYZE ----------------
SET maintenance_work_mem = '1GB';   -- this session only: faster index builds
SELECT extract(epoch FROM clock_timestamp()) AS setup_t0, clock_timestamp() AS setup_start_cat \gset

\ir 02_keys.sql

CREATE INDEX accounts_customer_account_idx ON accounts (customer_id, account_id);
CREATE INDEX account_devices_device_acct_idx  ON account_devices (device_id, account_id);
CREATE INDEX transfers_sender_time_idx ON transfers (sender_id, occurred_at) INCLUDE (receiver_id, amount_rwf, transfer_id);
CREATE INDEX transfers_receiver_time_idx ON transfers (receiver_id, occurred_at) INCLUDE (sender_id, amount_rwf, transfer_id);
CREATE INDEX transfers_occurred_brin ON transfers USING brin (occurred_at);

ANALYZE customers;
ANALYZE accounts;
ANALYZE devices;
ANALYZE account_devices;
ANALYZE transfers;

SELECT extract(epoch FROM clock_timestamp()) AS setup_t1, clock_timestamp() AS setup_end_cat \gset

\echo
\echo ================ 2.2 SUMMARY ================
SELECT :'load_start_cat'::timestamptz AS load_start_cat,
       :'load_end_cat'::timestamptz AS load_end_cat,
       ROUND((:load_t1 - :load_t0)::numeric, 2) AS load_seconds,
       :'setup_start_cat'::timestamptz AS setup_start_cat,
       :'setup_end_cat'::timestamptz AS setup_end_cat,
       ROUND((:setup_t1 - :setup_t0)::numeric, 2) AS index_constraint_setup_seconds;
