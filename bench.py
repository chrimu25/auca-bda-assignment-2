"""6.2 Timing of a fixed selection: 21 cases, ONE engine per run (stop the other service first).

  python3 bench.py --engine pg     # Neo4j stopped
  python3 bench.py --engine neo    # PostgreSQL stopped

3 untimed warm-ups (180 s limit) + 5 measured runs (60 s limit) per case.
perf_counter from submission to receipt of the final row. Timeouts/errors are recorded, never timed.
"""
import argparse
import csv
import json
import os
import statistics
from datetime import datetime
from time import perf_counter

import psycopg
from neo4j import Query
from neo4j.exceptions import Neo4jError

import db
from cases import CAT, SETS, hour_window
from queries import (Q1_CYPHER, Q1_SQL, Q2_CYPHER, Q2_SQL, Q3_CYPHER, Q3_SQL, Q4_SQL, Q5_CYPHER, Q5_SQL,
                     Q6_CYPHER, Q6_SQL, Q7_SQL, q4_cypher, q7_cypher)

WARMUP_LIMIT, MEASURE_LIMIT, WARMUPS, RUNS = 180, 60, 3, 5


def timing_cases(q7_sql=Q7_SQL):
    cases = []
    for n in ("B", "E"):
        acc, _d, day = SETS[n]; s, e = hour_window(day)
        hp = {"account": acc, "start": s, "end": e}
        cases += [(f"Q1 {n}", Q1_SQL, Q1_CYPHER, hp), (f"Q3 {n}", Q3_SQL, Q3_CYPHER, {"account": acc}),
                  (f"Q5 {n}", Q5_SQL, Q5_CYPHER, hp), (f"Q6 {n}", Q6_SQL, Q6_CYPHER, hp)]
    cases.append(("Q2 month", Q2_SQL, Q2_CYPHER, {}))
    for n in ("B", "E"):
        acc = SETS[n][0]
        for d in (4, 6, 8, 10):
            cases.append((f"Q4 {n} d{d}", Q4_SQL, q4_cypher(d), {"account": acc, "depth": d}))
    for n in ("B", "E"):
        acc, dest, _ = SETS[n]
        for b in (4, 6):
            cases.append((f"Q7 {n} b{b}", q7_sql, q7_cypher(b), {"source": acc, "dest": dest, "max_depth": b}))
    return cases


def run_once(engine, sql, cyp, params, limit):
    """Returns (status, seconds or None, row_count). Timer covers submission to final row."""
    try:
        if engine == "pg":
            conn = db.pg_conn()
            with conn.cursor() as cur:
                cur.execute(f"SET statement_timeout = '{limit}s'")
                start = perf_counter()
                cur.execute(sql, params)
                rows = cur.fetchall()
                dur = perf_counter() - start
        else:
            with db.neo_driver().session(database="neo4j") as session:
                start = perf_counter()
                result = session.run(Query(cyp, timeout=limit), params)
                rows = list(result)
                dur = perf_counter() - start
        return "ok", dur, len(rows)
    except psycopg.errors.QueryCanceled:
        return "timeout", None, 0
    except Neo4jError as exc:
        code = exc.code or ""
        return ("timeout" if "Timeout" in code or "TimedOut" in code or "Terminated" in code else "error"), None, 0
    except Exception as exc:          # noqa: BLE001
        print(f"      error: {exc}")
        return "error", None, 0


def bench(engine, cases, tag):
    os.makedirs("results/timing", exist_ok=True)
    raw, summary = [], []
    session_start = perf_counter()
    for name, sql, cyp, params in cases:
        for w in range(WARMUPS):
            st, _, _ = run_once(engine, sql, cyp, params, WARMUP_LIMIT)
            if st != "ok":
                print(f"   warm-up {w + 1} {name}: {st}")
        durs, statuses = [], []
        for r in range(RUNS):
            started = datetime.now(CAT).isoformat(timespec="milliseconds")
            st, dur, n = run_once(engine, sql, cyp, params, MEASURE_LIMIT)
            statuses.append(st)
            if st == "ok":
                durs.append(dur * 1000)
            raw.append({"case": name, "params": json.dumps(params), "engine": engine, "run": r + 1,
                        "start_cat": started, "duration_ms": round(dur * 1000, 3) if dur is not None else "",
                        "rows": n, "status": st})
        row = {"case": name, "engine": engine, "ok_runs": len(durs),
               "timeouts": statuses.count("timeout"), "errors": statuses.count("error"),
               "median_ms": round(statistics.median(durs), 3) if durs else "",
               "min_ms": round(min(durs), 3) if durs else "", "max_ms": round(max(durs), 3) if durs else ""}
        summary.append(row)
        print(f"{name:<12} median {str(row['median_ms']):>11} ms  min {str(row['min_ms']):>11}  "
              f"max {str(row['max_ms']):>11}  ok {row['ok_runs']}/5  timeouts {row['timeouts']}  errors {row['errors']}")
    with open(f"results/timing/raw_{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=raw[0].keys()); w.writeheader(); w.writerows(raw)
    with open(f"results/timing/summary_{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=summary[0].keys()); w.writeheader(); w.writerows(summary)
    print(f"\nSession {perf_counter() - session_start:.1f} s | saved results/timing/raw_{tag}.csv, summary_{tag}.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["pg", "neo"], required=True)
    engine = ap.parse_args().engine
    print(f"6.2 timing | engine {engine} | {datetime.now(CAT):%Y-%m-%d %H:%M:%S} CAT | "
          f"{WARMUPS} warm-ups ({WARMUP_LIMIT} s) + {RUNS} runs ({MEASURE_LIMIT} s)\n")
    bench(engine, timing_cases(), engine)
    db.close()


if __name__ == "__main__":
    main()
