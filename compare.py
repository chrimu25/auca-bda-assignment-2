"""6.1 One comparison program: 61 cases across Q1-Q7 in PostgreSQL and Neo4j, plus independent CSV checks.

Q1 6 | Q2 1 | Q3 6 | Q4 24 | Q5 6 | Q6 6 | Q7 12  = 61
Rows are normalised (db.normalise) and sorted before exact comparison.
Q7 lengths are compared separately from the validity of each engine's supporting path.
"""
import csv
import json
import os
from datetime import datetime

import db
from cases import CAT, SETS, hour_window
from queries import (Q1_CYPHER, Q1_SQL, Q2_CYPHER, Q2_SQL, Q3_CYPHER, Q3_SQL, Q4_SQL, Q5_CYPHER, Q5_SQL,
                     Q6_CYPHER, Q6_SQL, Q7_SQL, q4_cypher, q7_cypher)

CSV_DIR = os.getenv("CSV_DIR", "data")      # folder holding the captured source CSVs

PATH_STEP_SQL = """
SELECT t.transfer_id, s.role, r.role
FROM transfers t
JOIN accounts s ON s.account_id = t.sender_id
JOIN accounts r ON r.account_id = t.receiver_id
WHERE t.sender_id = %(s)s AND t.receiver_id = %(r)s
ORDER BY t.transfer_id
LIMIT 1
"""


def build_cases():
    cases = []
    for n, (acc, _d, day) in SETS.items():
        s, e = hour_window(day)
        cases.append(("Q1", n, Q1_SQL, Q1_CYPHER, {"account": acc, "start": s, "end": e}))
    cases.append(("Q2", "month", Q2_SQL, Q2_CYPHER, {}))
    for n, (acc, _d, _day) in SETS.items():
        cases.append(("Q3", n, Q3_SQL, Q3_CYPHER, {"account": acc}))
    for n, (acc, _d, _day) in SETS.items():
        for depth in (4, 6, 8, 10):
            cases.append(("Q4", f"{n} d{depth}", Q4_SQL, q4_cypher(depth), {"account": acc, "depth": depth}))
    for q, sql, cyp in (("Q5", Q5_SQL, Q5_CYPHER), ("Q6", Q6_SQL, Q6_CYPHER)):
        for n, (acc, _d, day) in SETS.items():
            s, e = hour_window(day)
            cases.append((q, n, sql, cyp, {"account": acc, "start": s, "end": e}))
    for n, (acc, dest, _day) in SETS.items():
        for bound in (4, 6):
            cases.append(("Q7", f"{n} b{bound}", Q7_SQL, q7_cypher(bound),
                          {"source": acc, "dest": dest, "max_depth": bound}))
    return cases


def check_path(path, source, dest, length):
    """IDs, direction, roles, event existence and length of one supporting path."""
    if path is None:
        return None, []
    problems, events = [], []
    if path[0] != source or path[-1] != dest:
        problems.append("wrong endpoints")
    if len(path) - 1 != length:
        problems.append("length mismatch")
    for s, r in zip(path, path[1:]):
        row = db.run_pg(PATH_STEP_SQL, {"s": s, "r": r})
        if not row:
            problems.append(f"no transfer {s}->{r}")
            continue
        tid, srole, rrole = row[0]
        events.append(tid)
        if srole != "person" or rrole != "person":
            problems.append(f"non-person on {s}->{r}")
    return (not problems), events


def csv_rows(name, key, wanted):
    found = {}
    with open(os.path.join(CSV_DIR, name), newline="") as f:
        for row in csv.DictReader(f):
            k = int(row[key]) if not isinstance(key, tuple) else tuple(int(row[c]) for c in key)
            if k in wanted:
                found[k] = row
    return found


def independent_checks(pg_q3_a, pg_q6_a):
    print("\n=== INDEPENDENT CSV CHECKS (Python csv module, no database) ===")
    # 1. Device overlap: account 998 and account 24755 on device 228001
    ad = csv_rows("account_devices.csv", ("account_id", "device_id"), {(998, 228001), (24755, 228001)})
    dev = csv_rows("devices.csv", "device_id", {228001})
    a, b = ad[(998, 228001)], ad[(24755, 228001)]
    start = max(int(a["first_day"]), int(b["first_day"]))
    end = min(int(a["last_day"]), int(b["last_day"]))
    csv_row = (24755, 228001, dev[228001]["access_type"], start, end)
    db_row = next(r for r in pg_q3_a if r[0] == 24755 and r[1] == 228001)
    print(f"Device overlap  998 [{a['first_day']},{a['last_day']}]  24755 [{b['first_day']},{b['last_day']}]  "
          f"on device 228001 ({dev[228001]['access_type']})")
    print(f"  CSV computed : {csv_row}\n  Q3 database  : {db_row}\n  agree: {csv_row == db_row}")

    # 2. Cycle: set A, transfers 20000001-20000004
    path = pg_q6_a[0][0]
    tr = csv_rows("transfers.csv", "transfer_id", set(path))
    rows = [tr[t] for t in path]
    s, e = hour_window(SETS["A"][2])
    ok_chain = all(int(rows[i]["receiver_id"]) == int(rows[i + 1]["sender_id"]) for i in range(len(rows) - 1))
    ok_ends = int(rows[0]["sender_id"]) == 998 and int(rows[-1]["receiver_id"]) == 998
    ok_returns = all(int(r["receiver_id"]) != 998 for r in rows[:-1])
    times = [int(r["occurred_at"]) for r in rows]
    amts = [int(r["amount_rwf"]) for r in rows]
    ok_time = all(times[i] < times[i + 1] for i in range(len(times) - 1)) and all(s <= t < e for t in times)
    ok_span = times[-1] - times[0] <= 1800
    ok_amt = all(90 * amts[i] <= 100 * amts[i + 1] <= 105 * amts[i] for i in range(len(amts) - 1))
    print(f"\nCycle (set A) {list(path)} read from transfers.csv:")
    for r in rows:
        ts = datetime.fromtimestamp(int(r["occurred_at"]), CAT).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {r['transfer_id']}: {r['sender_id']} -> {r['receiver_id']}  {ts} CAT  {int(r['amount_rwf']):,} RWF")
    print(f"  linked chain {ok_chain} | starts/ends at 998 {ok_ends} | first return only at end {ok_returns} | "
          f"increasing & inside hour {ok_time} | span {times[-1] - times[0]} s <= 1800 {ok_span} | "
          f"amounts 90-105% {ok_amt}")
    print(f"  all cycle rules confirmed from CSV: {all([ok_chain, ok_ends, ok_returns, ok_time, ok_span, ok_amt])}")


def main():
    os.makedirs("results", exist_ok=True)
    cases = build_cases()
    assert len(cases) == 61, len(cases)
    table, full, keep = [], [], {}
    print(f"{'#':>3}  {'Q':<3} {'case':<9}{'SQL rows':>9}{'Cyp rows':>9}  status")
    print("-" * 48)
    for i, (q, label, sql, cyp, params) in enumerate(cases, 1):
        pg = db.run_pg(sql, params)
        neo = db.run_neo(cyp, params)
        if q == "Q7":
            pl, pp = pg[0] if pg else (None, None)
            nl, np_ = neo[0] if neo else (None, None)
            status = "MATCH" if pl == nl else "MISMATCH"
            src, dst = params["source"], params["dest"]
            vs, es = check_path(pp, src, dst, pl)
            vn, en = check_path(np_, src, dst, nl)
            extra = {"sql_length": pl, "cypher_length": nl, "sql_path": pp, "cypher_path": np_,
                     "sql_path_valid": vs, "cypher_path_valid": vn, "sql_path_events": es, "cypher_path_events": en}
            nrows = (len(pg), len(neo))
        else:
            status = "MATCH" if sorted(pg) == sorted(neo) else "MISMATCH"
            extra = {"sql_rows": pg, "cypher_rows": neo}
            nrows = (len(pg), len(neo))
        if (q, label) in (("Q3", "A"), ("Q6", "A")):
            keep[q] = pg
        print(f"{i:>3}  {q:<3} {label:<9}{nrows[0]:>9}{nrows[1]:>9}  {status}")
        table.append({"case": i, "question": q, "label": label, "params": json.dumps(params),
                      "sql_rows": nrows[0], "cypher_rows": nrows[1], "status": status})
        full.append({"case": i, "question": q, "label": label, "params": params, "status": status, **extra})

    print("\n=== Q7 LENGTHS AND SUPPORTING PATH CHECKS (IDs, direction, roles, event existence, length) ===")
    for r in full:
        if r["question"] == "Q7":
            print(f"{r['label']:<6} length SQL {str(r['sql_length']):>4} Cypher {str(r['cypher_length']):>4} | "
                  f"SQL path valid {r['sql_path_valid']} events {r['sql_path_events']} | "
                  f"Cypher path valid {r['cypher_path_valid']} events {r['cypher_path_events']}")

    counts = {}
    for r in table:
        c = counts.setdefault(r["question"], [0, 0]); c[0] += 1; c[1] += r["status"] == "MATCH"
    print("\n=== 61-CASE STATUS SUMMARY ===")
    for q in sorted(counts):
        print(f"{q}: {counts[q][1]}/{counts[q][0]} match")
    total_ok = sum(c[1] for c in counts.values())
    paths_ok = all(r["sql_path_valid"] in (True, None) and r["cypher_path_valid"] in (True, None)
                   for r in full if r["question"] == "Q7")
    print(f"TOTAL: {total_ok}/61 match | all Q7 supporting paths valid: {paths_ok}")

    with open("results/compare_61.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=table[0].keys()); w.writeheader(); w.writerows(table)
    with open("results/compare_61_full.json", "w") as f:
        json.dump(full, f, indent=1, default=list)
    print("Saved results/compare_61.csv and results/compare_61_full.json")

    independent_checks(keep["Q3"], keep["Q6"])
    db.close()


if __name__ == "__main__":
    main()
