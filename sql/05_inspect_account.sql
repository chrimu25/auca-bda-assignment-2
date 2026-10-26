\pset pager off
SELECT a.account_id, a.role, c.customer_id, c.region, d.device_id, d.access_type, ad.first_day, ad.last_day, ad.observations, t.transfer_id, t.receiver_id, t.occurred_at, to_timestamp(t.occurred_at) AS occurred_cat, t.amount_rwf
FROM accounts a JOIN customers c ON c.customer_id = a.customer_id JOIN account_devices ad ON ad.account_id = a.account_id JOIN devices d ON d.device_id   = ad.device_id JOIN LATERAL (
 SELECT * FROM transfers t WHERE t.sender_id = a.account_id ORDER BY t.occurred_at, t.transfer_id LIMIT 1) t ON true WHERE a.account_id = 998 ORDER BY d.device_id;

-- Repeated payments
SELECT receiver_id, COUNT(*) AS payments, MIN(to_timestamp(occurred_at)) AS first_cat, MAX(to_timestamp(occurred_at)) AS last_cat, SUM(amount_rwf) AS total_rwf FROM transfers WHERE sender_id = 998 GROUP BY receiver_id HAVING COUNT(*) > 1 ORDER BY payments DESC, receiver_id LIMIT 5;