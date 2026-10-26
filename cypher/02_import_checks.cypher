// 3.2 Import checks against the source streams and capture.py audit totals

// Node counts per label (expected Customer 228,000 / Account 248,000 / Device 228,600)
MATCH (c:Customer) WITH count(c) AS customers
MATCH (a:Account)  WITH customers, count(a) AS accounts
MATCH (d:Device)   WITH customers, accounts, count(d) AS devices
RETURN customers, accounts, devices, customers + accounts + devices AS total_nodes,
       customers + accounts + devices = 704600 AS nodes_ok;

// Relationship counts per type (expected 248,000 / 285,600 / 20,003,300)
MATCH ()-[o:OWNS]->()        WITH count(o) AS owns
MATCH ()-[u:USED_DEVICE]->() WITH owns, count(u) AS used_device
MATCH ()-[t:TRANSFER]->()    WITH owns, used_device, count(t) AS transfer
RETURN owns, used_device, transfer, owns + used_device + transfer AS total_relationships,
       owns + used_device + transfer = 20536900 AS relationships_ok;

// Account roles (expected person 240,000 / merchant 6,000 / agent 2,000)
MATCH (a:Account) RETURN a.role AS role, count(*) AS accounts ORDER BY role;

// One owner per account (expected 0 accounts with a different number of owners)
MATCH (a:Account)
WITH a, COUNT { (:Customer)-[:OWNS]->(a) } AS owners
WHERE owners <> 1
RETURN count(a) AS accounts_without_exactly_one_owner;

// Unique transfer_id
MATCH ()-[t:TRANSFER]->()
RETURN count(t) AS transfers, count(DISTINCT t.transfer_id) AS distinct_transfer_ids,
       count(t) = count(DISTINCT t.transfer_id) AS transfer_id_unique;

// Transfer audit totals (capture.py: 1788235200 / 1790798399 / 231,482,327,870)
MATCH ()-[t:TRANSFER]->()
RETURN count(t) AS transfers, min(t.occurred_at) AS min_occurred_at,
       max(t.occurred_at) AS max_occurred_at, sum(t.amount_rwf) AS sum_amount_rwf,
       count(t) = 20003300 AND min(t.occurred_at) = 1788235200
         AND max(t.occurred_at) = 1790798399 AND sum(t.amount_rwf) = 231482327870 AS audit_matches_capture;
