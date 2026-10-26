"""6.3 Q7 SQL improvement (bidirectional bounded search). Original Q7_SQL is kept unchanged.

  python3 run_6_3.py --check   # both services: 12 cases, V2 lengths vs Cypher + path checks
  python3 run_6_3.py --time    # PostgreSQL only (Neo4j stopped): retime B/E at bounds 4 and 6
  python3 run_6_3.py --plan    # PostgreSQL: EXPLAIN (ANALYZE, BUFFERS) of V2 for B bound 6
"""
import argparse
import csv
import json
import os
import statistics
from datetime import datetime
from time import perf_counter

import db
from bench import MEASURE_LIMIT, RUNS, WARMUP_LIMIT, WARMUPS, run_once
from cases import CAT, SETS
from compare import check_path
from plans import pg_plan
from queries import Q7_SQL_V2, q7_cypher


def check():
    ok_all = True
    print(f"{'set':<4}{'bound':>6}  {'V2 len':>6}{'Cyp len':>8}  same  V2 path valid  V2 events")
    print("-" * 90)
    for n, (src, dst, _d) in SETS.items():
        for bound in (4, 6):
            p = {"source": src, "dest": dst, "max_depth": bound}
            t0 = perf_counter(); pg = db.run_pg(Q7_SQL_V2, p); tp = perf_counter() - t0
            neo = db.run_neo(q7_cypher(bound), {"source": src, "dest": dst})
            pl, pp = pg[0] if pg else (None, None)
            nl = neo[0][0] if neo else None
            valid, events = check_path(pp, src, dst, pl)
            same = pl == nl
            ok_all &= same and valid in (True, None)
            print(f"{n:<4}{bound:>6}  {str(pl):>6}{str(nl):>8}  {'YES' if same else 'NO ':<4}  "
                  f"{str(valid):<13}  {events}  path {pp}  ({tp * 1000:.1f} ms)")
    print(f"\nAll 12 V2 lengths match Cypher and all V2 paths valid: {ok_all}")


def timing():
    os.makedirs("results/timing", exist_ok=True)
    before = {}
    if os.path.exists("results/timing/summary_pg.csv"):
        with open("results/timing/summary_pg.csv") as f:
            before = {r["case"]: r for r in csv.DictReader(f)}
    raw, rows = [], []
    print(f"6.3 retiming Q7 V2 | {datetime.now(CAT):%Y-%m-%d %H:%M:%S} CAT | {WARMUPS} warm-ups + {RUNS} runs\n")
    for n in ("B", "E"):
        src, dst, _ = SETS[n]
        for bound in (4, 6):
            name = f"Q7 {n} b{bound}"
            params = {"source": src, "dest": dst, "max_depth": bound}
            for _ in range(WARMUPS):
                run_once("pg", Q7_SQL_V2, None, params, WARMUP_LIMIT)
            durs, sts = [], []
            for r in range(RUNS):
                started = datetime.now(CAT).isoformat(timespec="milliseconds")
                st, dur, nrows = run_once("pg", Q7_SQL_V2, None, params, MEASURE_LIMIT)
                sts.append(st)
                if st == "ok":
                    durs.append(dur * 1000)
                raw.append({"case": name, "params": json.dumps(params), "engine": "pg_v2", "run": r + 1,
                            "start_cat": started, "duration_ms": round(dur * 1000, 3) if dur else "",
                            "rows": nrows, "status": st})
            med = statistics.median(durs) if durs else None
            old = float(before[name]["median_ms"]) if name in before and before[name]["median_ms"] else None
            rows.append({"case": name, "v1_median_ms": old, "v2_median_ms": round(med, 3) if med else "",
                         "v2_min_ms": round(min(durs), 3) if durs else "", "v2_max_ms": round(max(durs), 3) if durs else "",
                         "ok_runs": len(durs), "timeouts": sts.count("timeout"), "errors": sts.count("error"),
                         "speedup": round(old / med, 1) if old and med else ""})
            print(f"{name:<10} V1 median {str(old):>11} ms | V2 median {med:>9.3f} ms  min {min(durs):.3f}  "
                  f"max {max(durs):.3f}  ok {len(durs)}/5 | speed-up {rows[-1]['speedup']}x")
    with open("results/timing/raw_pg_q7v2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=raw[0].keys()); w.writeheader(); w.writerows(raw)
    with open("results/timing/summary_pg_q7v2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print("\nSaved results/timing/raw_pg_q7v2.csv and summary_pg_q7v2.csv")


def plan():
    os.makedirs("results/plans", exist_ok=True)
    src, dst, _ = SETS["B"]
    pg_plan("q7_B_bound6_v2", Q7_SQL_V2, {"source": src, "dest": dst, "max_depth": 6})


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true"); g.add_argument("--time", action="store_true")
    g.add_argument("--plan", action="store_true")
    a = ap.parse_args()
    check() if a.check else timing() if a.time else plan()
    db.close()


if __name__ == "__main__":
    main()
