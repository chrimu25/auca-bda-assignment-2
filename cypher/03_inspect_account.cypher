// Account -> owner (OWNS), devices (USED_DEVICE), first outgoing TRANSFER
MATCH (c:Customer)-[:OWNS]->(a:Account {account_id: 998})-[u:USED_DEVICE]->(d:Device)
CALL (a) {
  MATCH (a)-[t:TRANSFER]->(r:Account)
  RETURN t, r ORDER BY t.occurred_at, t.transfer_id LIMIT 1
}
RETURN a.account_id AS account_id, a.role AS role,
       c.customer_id AS customer_id, c.region AS region,
       d.device_id AS device_id, d.access_type AS access_type,
       u.first_day AS first_day, u.last_day AS last_day, u.observations AS observations,
       t.transfer_id AS transfer_id, r.account_id AS receiver_id, t.occurred_at AS occurred_at,
       datetime({epochSeconds: t.occurred_at, timezone: 'Africa/Kigali'}) AS occurred_cat,
       t.amount_rwf AS amount_rwf
ORDER BY device_id;

// Repeated payments stay separate TRANSFER relationships
MATCH (:Account {account_id: 998})-[t:TRANSFER]->(r:Account)
WITH r.account_id AS receiver_id, count(t) AS payments,
     min(t.occurred_at) AS first_ts, max(t.occurred_at) AS last_ts, sum(t.amount_rwf) AS total_rwf
WHERE payments > 1
RETURN receiver_id, payments,
       datetime({epochSeconds: first_ts, timezone: 'Africa/Kigali'}) AS first_cat,
       datetime({epochSeconds: last_ts,  timezone: 'Africa/Kigali'}) AS last_cat, total_rwf
ORDER BY payments DESC, receiver_id
LIMIT 5;