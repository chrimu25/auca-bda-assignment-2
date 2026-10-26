"""SQL / Cypher pairs for Q1-Q7 (parameterised; stored data only)."""

Q1_SQL = """
SELECT COUNT(*) AS transfers, COALESCE(SUM(amount_rwf), 0) AS total_rwf
FROM transfers
WHERE sender_id = %(account)s
  AND occurred_at >= %(start)s
  AND occurred_at <  %(end)s
"""

Q1_CYPHER = """
MATCH (a:Account {account_id: $account})-[t:TRANSFER]->()
WHERE t.occurred_at >= $start AND t.occurred_at < $end
RETURN count(t) AS transfers, coalesce(sum(t.amount_rwf), 0) AS total_rwf
"""

Q2_SQL = """
SELECT (to_timestamp(occurred_at) AT TIME ZONE 'Africa/Kigali')::date AS day,
       COUNT(*)                AS transfers,
       SUM(amount_rwf)::bigint AS total_rwf
FROM transfers
GROUP BY day
ORDER BY day
"""

Q2_CYPHER = """
MATCH ()-[t:TRANSFER]->()
WITH date(datetime({epochSeconds: t.occurred_at, timezone: 'Africa/Kigali'})) AS day, t.amount_rwf AS amount
RETURN day, count(*) AS transfers, sum(amount) AS total_rwf
ORDER BY day
"""

Q3_SQL = """
SELECT o.account_id AS other_account, o.device_id, d.access_type,
       GREATEST(r.first_day, o.first_day) AS overlap_start,
       LEAST(r.last_day, o.last_day)      AS overlap_end
FROM account_devices r
JOIN account_devices o ON o.device_id = r.device_id AND o.account_id <> r.account_id
JOIN devices d         ON d.device_id = r.device_id
WHERE r.account_id = %(account)s
  AND GREATEST(r.first_day, o.first_day) <= LEAST(r.last_day, o.last_day)
ORDER BY other_account, o.device_id
"""

Q3_CYPHER = """
MATCH (a:Account {account_id: $account})-[r:USED_DEVICE]->(d:Device)<-[o:USED_DEVICE]-(b:Account)
WHERE b <> a
WITH b, d,
     CASE WHEN r.first_day > o.first_day THEN r.first_day ELSE o.first_day END AS overlap_start,
     CASE WHEN r.last_day  < o.last_day  THEN r.last_day  ELSE o.last_day  END AS overlap_end
WHERE overlap_start <= overlap_end
RETURN b.account_id AS other_account, d.device_id AS device_id, d.access_type AS access_type,
       overlap_start, overlap_end
ORDER BY other_account, device_id
"""

Q4_SQL = """
WITH RECURSIVE edges(sk, si, dk, di) AS (
    SELECT 'Customer', customer_id, 'Account', account_id FROM accounts
    UNION ALL
    SELECT 'Account', account_id, 'Customer', customer_id FROM accounts
    UNION ALL
    SELECT 'Account', account_id, 'Device', device_id FROM account_devices
    UNION ALL
    SELECT 'Device', device_id, 'Account', account_id FROM account_devices
), walk(kind, id, depth) AS (
    SELECT 'Account', %(account)s::integer, 0
    UNION
    SELECT e.dk, e.di, w.depth + 1
    FROM walk w
    JOIN edges e ON e.sk = w.kind AND e.si = w.id
    WHERE w.depth < %(depth)s
)
SELECT c.region, COUNT(DISTINCT w.id) AS accounts
FROM walk w
JOIN accounts a  ON a.account_id = w.id
JOIN customers c ON c.customer_id = a.customer_id
WHERE w.kind = 'Account' AND w.id <> %(account)s
GROUP BY c.region
ORDER BY c.region
"""

# The variable-length bound cannot be a Cypher parameter, so it is inserted as an integer.
Q4_CYPHER_TEMPLATE = """
MATCH (a:Account {{account_id: $account}})
MATCH (a)-[:OWNS|USED_DEVICE*1..{depth}]-(b:Account)
WHERE b <> a
WITH DISTINCT b
MATCH (c:Customer)-[:OWNS]->(b)
RETURN c.region AS region, count(b) AS accounts
ORDER BY region
"""


def q4_cypher(depth):
    return Q4_CYPHER_TEMPLATE.format(depth=int(depth))


Q4_PATH_CYPHER = """
MATCH p = SHORTEST 1 (a:Account {account_id: $account})-[:OWNS|USED_DEVICE]-{1,10}(b:Account {account_id: $target})
RETURN [n IN nodes(p) | labels(n)[0] + ' ' + toString(coalesce(n.account_id, n.customer_id, n.device_id))] AS path,
       [r IN relationships(p) | type(r)] AS links,
       length(p) AS length
"""

# ---------- Q5 Rapid onward payments ----------
Q5_SQL = """
SELECT t1.transfer_id AS t1, t2.transfer_id AS t2, t3.transfer_id AS t3, t3.receiver_id AS final_receiver
FROM transfers t1
JOIN transfers t2 ON t2.sender_id = t1.receiver_id
                 AND t2.occurred_at >  t1.occurred_at
                 AND t2.occurred_at <= t1.occurred_at + 600
JOIN transfers t3 ON t3.sender_id = t2.receiver_id
                 AND t3.occurred_at >  t2.occurred_at
                 AND t3.occurred_at <= t2.occurred_at + 600
WHERE t1.sender_id = %(account)s
  AND t1.occurred_at >= %(start)s AND t1.occurred_at < %(end)s
  AND 90::bigint * t1.amount_rwf <= 100::bigint * t2.amount_rwf
  AND 100::bigint * t2.amount_rwf <= 105::bigint * t1.amount_rwf
  AND 90::bigint * t2.amount_rwf <= 100::bigint * t3.amount_rwf
  AND 100::bigint * t3.amount_rwf <= 105::bigint * t2.amount_rwf
  AND t1.sender_id   <> t1.receiver_id AND t1.sender_id   <> t2.receiver_id
  AND t1.sender_id   <> t3.receiver_id AND t1.receiver_id <> t2.receiver_id
  AND t1.receiver_id <> t3.receiver_id AND t2.receiver_id <> t3.receiver_id
ORDER BY t1, t2, t3, final_receiver
"""

Q5_CYPHER = """
MATCH (a:Account {account_id: $account})-[t1:TRANSFER]->(b:Account)-[t2:TRANSFER]->(c:Account)-[t3:TRANSFER]->(d:Account)
WHERE t1.occurred_at >= $start AND t1.occurred_at < $end
  AND t2.occurred_at > t1.occurred_at AND t2.occurred_at <= t1.occurred_at + 600
  AND t3.occurred_at > t2.occurred_at AND t3.occurred_at <= t2.occurred_at + 600
  AND 90 * t1.amount_rwf <= 100 * t2.amount_rwf AND 100 * t2.amount_rwf <= 105 * t1.amount_rwf
  AND 90 * t2.amount_rwf <= 100 * t3.amount_rwf AND 100 * t3.amount_rwf <= 105 * t2.amount_rwf
  AND a <> b AND a <> c AND a <> d AND b <> c AND b <> d AND c <> d
RETURN t1.transfer_id AS t1, t2.transfer_id AS t2, t3.transfer_id AS t3, d.account_id AS final_receiver
ORDER BY t1, t2, t3, final_receiver
"""

# ---------- Q6 Circular payments ----------
Q6_SQL = """
WITH RECURSIVE cyc(path, cur, first_at, last_at, last_amt, steps) AS (
    SELECT ARRAY[t.transfer_id], t.receiver_id, t.occurred_at, t.occurred_at, t.amount_rwf, 1
    FROM transfers t
    WHERE t.sender_id = %(account)s
      AND t.occurred_at >= %(start)s AND t.occurred_at < %(end)s
      AND t.receiver_id <> %(account)s
    UNION ALL
    SELECT c.path || t.transfer_id, t.receiver_id, c.first_at, t.occurred_at, t.amount_rwf, c.steps + 1
    FROM cyc c
    JOIN transfers t ON t.sender_id = c.cur
    WHERE c.cur <> %(account)s                 -- stop at the first return
      AND c.steps < 8
      AND t.occurred_at >  c.last_at
      AND t.occurred_at <  %(end)s
      AND t.occurred_at - c.first_at <= 1800
      AND 90::bigint * c.last_amt <= 100::bigint * t.amount_rwf
      AND 100::bigint * t.amount_rwf <= 105::bigint * c.last_amt
)
SELECT path, steps
FROM cyc
WHERE cur = %(account)s AND steps BETWEEN 3 AND 8
ORDER BY path
"""

Q6_CYPHER = """
MATCH (a:Account {account_id: $account})
MATCH (a)(()-[t:TRANSFER WHERE t.occurred_at >= $start AND t.occurred_at < $end]->(n WHERE n <> a)){2,7}
      ()-[last:TRANSFER WHERE last.occurred_at >= $start AND last.occurred_at < $end]->(a)
WITH t + [last] AS ts
WHERE all(i IN range(0, size(ts) - 2) WHERE
          ts[i + 1].occurred_at > ts[i].occurred_at
          AND 90 * ts[i].amount_rwf <= 100 * ts[i + 1].amount_rwf
          AND 100 * ts[i + 1].amount_rwf <= 105 * ts[i].amount_rwf)
  AND ts[size(ts) - 1].occurred_at - ts[0].occurred_at <= 1800
RETURN [x IN ts | x.transfer_id] AS path, size(ts) AS steps
ORDER BY path
"""

# ---------- Q7 Shortest person-only payment path ----------
Q7_SQL = """
WITH RECURSIVE fwd(account_id, depth) AS (
    SELECT %(source)s::integer, 0
    UNION
    SELECT t.receiver_id, f.depth + 1
    FROM fwd f
    JOIN transfers t ON t.sender_id = f.account_id
    JOIN accounts r  ON r.account_id = t.receiver_id AND r.role = 'person'
    WHERE f.depth < %(max_depth)s
),
fd AS (SELECT account_id, MIN(depth) AS d FROM fwd GROUP BY account_id),
target AS (SELECT d AS len FROM fd WHERE account_id = %(dest)s),
back(account_id, depth, path) AS (
    SELECT %(dest)s::integer, (SELECT len FROM target), ARRAY[%(dest)s::integer]
    WHERE EXISTS (SELECT 1 FROM target)
    UNION ALL
    SELECT x.sender_id, b.depth - 1, x.sender_id || b.path
    FROM back b
    CROSS JOIN LATERAL (
        SELECT t.sender_id
        FROM transfers t
        JOIN fd ON fd.account_id = t.sender_id AND fd.d = b.depth - 1
        WHERE t.receiver_id = b.account_id
        ORDER BY t.sender_id
        LIMIT 1
    ) x
    WHERE b.depth > 0
)
SELECT array_length(path, 1) - 1 AS length, path
FROM back
WHERE depth = 0
"""

Q7_CYPHER_TEMPLATE = """
MATCH (a:Account {{account_id: $source}}), (b:Account {{account_id: $dest}})
WHERE a.role = 'person'
OPTIONAL MATCH p = SHORTEST 1 (a)(()-[:TRANSFER]->(x:Account WHERE x.role = 'person')){{1,{max_depth}}}(b)
RETURN length(p) AS length, [n IN nodes(p) | n.account_id] AS path
"""


def q7_cypher(max_depth):
    return Q7_CYPHER_TEMPLATE.format(max_depth=int(max_depth))


Q7_EDGE_CHECK_SQL = """
SELECT EXISTS (SELECT 1 FROM transfers WHERE sender_id = %(s)s AND receiver_id = %(r)s),
       (SELECT role FROM accounts WHERE account_id = %(r)s)
"""

# ---------- 6.3 Q7 improved: bidirectional bounded search (same output as Q7_SQL) ----------
Q7_SQL_V2 = """
WITH RECURSIVE fwd(account_id, depth) AS (
    SELECT %(source)s::integer, 0
    UNION
    SELECT t.receiver_id, f.depth + 1
    FROM fwd f
    JOIN transfers t ON t.sender_id = f.account_id
    JOIN accounts r  ON r.account_id = t.receiver_id AND r.role = 'person'
    WHERE f.depth < (%(max_depth)s + 1) / 2                 -- ceil(bound / 2)
),
bwd(account_id, depth) AS (
    SELECT %(dest)s::integer, 0
    WHERE EXISTS (SELECT 1 FROM accounts WHERE account_id = %(dest)s AND role = 'person')
    UNION
    SELECT t.sender_id, b.depth + 1
    FROM bwd b
    JOIN transfers t ON t.receiver_id = b.account_id
    JOIN accounts s  ON s.account_id = t.sender_id AND s.role = 'person'
    WHERE b.depth < %(max_depth)s / 2                       -- floor(bound / 2)
),
f AS (SELECT account_id, MIN(depth) AS d FROM fwd GROUP BY account_id),
b AS (SELECT account_id, MIN(depth) AS d FROM bwd GROUP BY account_id),
best AS (
    SELECT f.d + b.d AS len, f.account_id AS m, f.d AS fd, b.d AS bd
    FROM f JOIN b USING (account_id)
    WHERE f.d + b.d <= %(max_depth)s
    ORDER BY f.d + b.d, f.account_id
    LIMIT 1
),
left_part(account_id, depth, path) AS (          -- meeting account back to the source
    SELECT m, fd, ARRAY[m] FROM best
    UNION ALL
    SELECT x.sender_id, l.depth - 1, x.sender_id || l.path
    FROM left_part l
    CROSS JOIN LATERAL (
        SELECT t.sender_id FROM transfers t
        JOIN f ON f.account_id = t.sender_id AND f.d = l.depth - 1
        WHERE t.receiver_id = l.account_id
        ORDER BY t.sender_id LIMIT 1
    ) x
    WHERE l.depth > 0
),
right_part(account_id, depth, path) AS (         -- meeting account forward to the destination
    SELECT m, bd, ARRAY[]::integer[] FROM best
    UNION ALL
    SELECT x.receiver_id, r.depth - 1, r.path || x.receiver_id
    FROM right_part r
    CROSS JOIN LATERAL (
        SELECT t.receiver_id FROM transfers t
        JOIN b ON b.account_id = t.receiver_id AND b.d = r.depth - 1
        WHERE t.sender_id = r.account_id
        ORDER BY t.receiver_id LIMIT 1
    ) x
    WHERE r.depth > 0
)
SELECT best.len AS length,
       (SELECT path FROM left_part WHERE depth = 0) || (SELECT path FROM right_part WHERE depth = 0) AS path
FROM best
"""

# ---------- Section 7: length-only Q7 versions ----------
Q7_LEN_SQL_V1 = """
WITH RECURSIVE fwd(account_id, depth) AS (
    SELECT %(source)s::integer, 0
    UNION
    SELECT t.receiver_id, f.depth + 1
    FROM fwd f
    JOIN transfers t ON t.sender_id = f.account_id
    JOIN accounts r  ON r.account_id = t.receiver_id AND r.role = 'person'
    WHERE f.depth < %(max_depth)s
)
SELECT MIN(depth) AS length FROM fwd WHERE account_id = %(dest)s
"""

Q7_LEN_SQL_V2 = """
WITH RECURSIVE fwd(account_id, depth) AS (
    SELECT %(source)s::integer, 0
    UNION
    SELECT t.receiver_id, f.depth + 1
    FROM fwd f
    JOIN transfers t ON t.sender_id = f.account_id
    JOIN accounts r  ON r.account_id = t.receiver_id AND r.role = 'person'
    WHERE f.depth < (%(max_depth)s + 1) / 2
),
bwd(account_id, depth) AS (
    SELECT %(dest)s::integer, 0
    WHERE EXISTS (SELECT 1 FROM accounts WHERE account_id = %(dest)s AND role = 'person')
    UNION
    SELECT t.sender_id, b.depth + 1
    FROM bwd b
    JOIN transfers t ON t.receiver_id = b.account_id
    JOIN accounts s  ON s.account_id = t.sender_id AND s.role = 'person'
    WHERE b.depth < %(max_depth)s / 2
),
f AS (SELECT account_id, MIN(depth) AS d FROM fwd GROUP BY account_id),
b AS (SELECT account_id, MIN(depth) AS d FROM bwd GROUP BY account_id)
SELECT MIN(f.d + b.d) AS length
FROM f JOIN b USING (account_id)
WHERE f.d + b.d <= %(max_depth)s
"""

Q7_LEN_CYPHER_TEMPLATE = """
MATCH (a:Account {{account_id: $source}}), (b:Account {{account_id: $dest}})
WHERE a.role = 'person'
OPTIONAL MATCH p = SHORTEST 1 (a)(()-[:TRANSFER]->(x:Account WHERE x.role = 'person')){{1,{max_depth}}}(b)
RETURN length(p) AS length
"""


def q7_len_cypher(max_depth):
    return Q7_LEN_CYPHER_TEMPLATE.format(max_depth=int(max_depth))
