"""7.1 Load test: multiprocessing clients, one persistent connection each, synchronised by a Barrier.

  python3 loadtest.py --engine pg     # Neo4j stopped
  python3 loadtest.py --engine neo    # PostgreSQL stopped

Workloads: Q4 depth 10 and Q7 length-only bound 6, cycling A-B-C.
Clients 1, 4, 8, 16; three repetitions each. 15 s window; started cycles finish; 60 s query timeout.
"""
import argparse
import csv
import math
import multiprocessing as mp
import os
import statistics
import time
from datetime import datetime

import psutil

import db
from bench import run_once
from cases import CAT, SETS
from queries import Q4_SQL, Q7_LEN_SQL_V2, q4_cypher, q7_len_cypher

WINDOW, TIMEOUT, CLIENTS, REPS = 15.0, 60, (1, 4, 8, 16), 3
CYCLE = ("A", "B", "C")


def requests_for(workload):
    reqs = []
    for n in CYCLE:
        acc, dest, _ = SETS[n]
        if workload == "Q4_d10":
            reqs.append((n, Q4_SQL, q4_cypher(10), {"account": acc, "depth": 10}))
        else:
            reqs.append((n, Q7_LEN_SQL_V2, q7_len_cypher(6), {"source": acc, "dest": dest, "max_depth": 6}))
    return reqs


def execute(engine, sql, cyp, params):
    """One request with the 60 s timeout; returns (status, latency_s, rows)."""
    try:
        if engine == "pg":
            conn = db.pg_conn()
            with conn.cursor() as cur:
                cur.execute(f"SET statement_timeout = '{TIMEOUT}s'")
                t0 = time.perf_counter(); cur.execute(sql, params); rows = cur.fetchall()
                lat = time.perf_counter() - t0
            return "ok", lat, [tuple(db.normalise(v) for v in r) for r in rows]
        from neo4j import Query
        with db.neo_driver().session(database="neo4j") as s:
            t0 = time.perf_counter(); rows = list(s.run(Query(cyp, timeout=TIMEOUT), params))
            lat = time.perf_counter() - t0
        return "ok", lat, [tuple(db.normalise(v) for v in r.values()) for r in rows]
    except Exception as exc:                       # noqa: BLE001
        text = f"{type(exc).__name__} {getattr(exc, 'code', '')}"
        return ("timeout" if any(k in text for k in ("QueryCanceled", "Timeout", "TimedOut", "Terminated"))
                else "error"), None, None


def client(cid, engine, workload, barrier, start_val, out_q):
    reqs = requests_for(workload)
    for n, sql, cyp, p in reqs:                     # warm up A-B-C once (also opens the persistent connection)
        execute(engine, sql, cyp, p)
    if barrier.wait() == 0:                         # all clients ready: one of them records the common start
        start_val.value = time.time()
    barrier.wait()                                  # release together, after the start time is set
    start = start_val.value
    deadline = start + WINDOW
    log = []
    while time.time() < deadline:                   # start cycles until the deadline...
        for n, sql, cyp, p in reqs:                 # ...and finish any started cycle
            sent = time.time()
            st, lat, rows = execute(engine, sql, cyp, p)
            log.append({"client": cid, "set": n, "sent": sent, "done": time.time(),
                        "latency_ms": lat * 1000 if lat is not None else None, "status": st, "rows": rows})
    db.close()
    out_q.put(log)


def monitor_active(engine, stop_evt, out_q):
    """Samples active server-side queries and CPU while clients run (evidence for 'active clients')."""
    samples, cpu = [], []
    psutil.cpu_percent(None)
    while not stop_evt.is_set():
        try:
            if engine == "pg":
                n = db.run_pg("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                              "AND state = 'active' AND pid <> pg_backend_pid()")[0][0]
            else:
                n = len(db.run_neo("SHOW TRANSACTIONS YIELD currentQuery, status "
                                   "WHERE NOT currentQuery STARTS WITH 'SHOW' RETURN status"))
            samples.append(n)
        except Exception:                           # noqa: BLE001
            pass
        cpu.append(psutil.cpu_percent(None))
        stop_evt.wait(0.5)
    db.close()
    out_q.put((samples, cpu))


def reference(engine, workload):
    return {n: execute(engine, sql, cyp, p)[2] for n, sql, cyp, p in requests_for(workload)}


def run_test(engine, workload, clients, rep, ref):
    ctx = mp.get_context("spawn")
    start_val = ctx.Value("d", 0.0)
    barrier = ctx.Barrier(clients)
    out_q, mon_q, stop_evt = ctx.Queue(), ctx.Queue(), ctx.Event()
    procs = [ctx.Process(target=client, args=(i, engine, workload, barrier, start_val, out_q)) for i in range(clients)]
    mon = ctx.Process(target=monitor_active, args=(engine, stop_evt, mon_q))
    mon.start()
    for p in procs:
        p.start()
    logs = [r for _ in procs for r in out_q.get()]
    for p in procs:
        p.join()
    stop_evt.set(); samples, cpu = mon_q.get(); mon.join()

    start = start_val.value
    elapsed = max(r["done"] for r in logs) - start
    for r in logs:                                  # correctness checked after timing
        r["correct"] = r["status"] == "ok" and r["rows"] == ref[r["set"]]
    ok = sorted(r["latency_ms"] for r in logs if r["correct"])
    n_ok = len(ok)
    p95 = ok[math.ceil(0.95 * n_ok) - 1] if n_ok else None
    res = {"engine": engine, "workload": workload, "clients": clients, "rep": rep,
           "start_cat": datetime.fromtimestamp(start, CAT).isoformat(timespec="milliseconds"),
           "requests": len(logs), "correct": n_ok,
           "wrong": sum(1 for r in logs if r["status"] == "ok" and not r["correct"]),
           "errors": sum(r["status"] == "error" for r in logs), "timeouts": sum(r["status"] == "timeout" for r in logs),
           "elapsed_s": round(elapsed, 3), "throughput_rps": round(n_ok / elapsed, 3),
           "median_ms": round(statistics.median(ok), 3) if ok else "", "p95_ms": round(p95, 3) if p95 else "",
           "max_active_seen": max(samples) if samples else "", "mean_cpu_pct": round(statistics.mean(cpu), 1) if cpu else ""}
    return res, logs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["pg", "neo"], required=True)
    ap.add_argument("--workloads", nargs="+", default=["Q4_d10", "Q7_len_b6"])
    a = ap.parse_args()
    os.makedirs("results/load", exist_ok=True)
    print(f"7.1 load test | engine {a.engine} | {datetime.now(CAT):%Y-%m-%d %H:%M:%S} CAT | window {WINDOW:.0f} s | "
          f"CPU cores {psutil.cpu_count()}\n")
    results, all_logs = [], []
    for wl in a.workloads:
        ref = reference(a.engine, wl)
        print(f"Reference answers ({wl}): {ref}")
        for c in CLIENTS:
            for rep in range(1, REPS + 1):
                res, logs = run_test(a.engine, wl, c, rep, ref)
                results.append(res)
                for r in logs:
                    all_logs.append({"engine": a.engine, "workload": wl, "clients": c, "rep": rep, "client": r["client"],
                                     "set": r["set"], "sent": round(r["sent"], 6), "done": round(r["done"], 6),
                                     "latency_ms": round(r["latency_ms"], 3) if r["latency_ms"] is not None else "",
                                     "status": r["status"], "correct": r["correct"]})
                print(f"{wl:<10} clients {c:>2} rep {rep}  thr {res['throughput_rps']:>8.2f}/s  "
                      f"median {str(res['median_ms']):>9} ms  p95 {str(res['p95_ms']):>9} ms  "
                      f"correct {res['correct']}/{res['requests']}  err {res['errors']}  to {res['timeouts']}  "
                      f"active max {res['max_active_seen']}  cpu {res['mean_cpu_pct']}%")
    with open(f"results/load/reps_{a.engine}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    with open(f"results/load/requests_{a.engine}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_logs[0].keys()); w.writeheader(); w.writerows(all_logs)

    print("\n=== SUMMARY (median of 3 repetitions) ===")
    print(f"{'workload':<10}{'clients':>8}{'throughput/s':>14}{'median ms':>11}{'p95 ms':>10}{'errors':>8}{'timeouts':>9}")
    for wl in a.workloads:
        for c in CLIENTS:
            rs = [r for r in results if r["workload"] == wl and r["clients"] == c]
            med = lambda k: statistics.median(float(r[k]) for r in rs if r[k] != "")
            print(f"{wl:<10}{c:>8}{med('throughput_rps'):>14.2f}{med('median_ms'):>11.2f}{med('p95_ms'):>10.2f}"
                  f"{sum(r['errors'] for r in rs):>8}{sum(r['timeouts'] for r in rs):>9}")
    print(f"\nSaved results/load/reps_{a.engine}.csv and requests_{a.engine}.csv")
    db.close()


if __name__ == "__main__":
    main()
