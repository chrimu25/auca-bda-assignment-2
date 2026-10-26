"""5.1 Q4 Ownership and device network: distinct accounts reached within 4/6/8/10 links, by owner region.

Usage:
  python3 run_q4.py --depths 4 6     # first run, then write your prediction for 8 and 10
  python3 run_q4.py --depths 8 10    # then test the prediction
  python3 run_q4.py                  # all four depths, plot and supporting path
"""
import argparse
import csv
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import db
from cases import SETS
from queries import Q4_PATH_CYPHER, Q4_SQL, q4_cypher


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depths", nargs="+", type=int, default=[4, 6, 8, 10])
    depths = ap.parse_args().depths
    os.makedirs("results", exist_ok=True)

    rows, totals = [], {}
    print("Q4: distinct other accounts reached through OWNS / USED_DEVICE (either direction), by owner region\n")
    print(f"{'set':<4}{'account':>8}{'depth':>6}  {'regions (SQL)':<66}{'total':>6}  "
          f"{'SQL s':>7}{'Cyp s':>8}  identical")
    print("-" * 118)
    for name, (account, _dest, _day) in SETS.items():
        for depth in depths:
            params = {"account": account, "depth": depth}
            t0 = time.perf_counter(); pg = db.run_pg(Q4_SQL, params); tp = time.perf_counter() - t0
            t0 = time.perf_counter(); neo = db.run_neo(q4_cypher(depth), {"account": account}); tn = time.perf_counter() - t0
            same = pg == neo
            total = sum(r[1] for r in pg)
            totals[(name, depth)] = total
            regions = ", ".join(f"{r[0]} {r[1]}" for r in pg)
            print(f"{name:<4}{account:>8}{depth:>6}  {regions:<66}{total:>6}  {tp:>7.2f}{tn:>8.2f}  {'YES' if same else 'NO'}")
            rows.append({"set": name, "account": account, "depth": depth,
                         "sql": ";".join(f"{r[0]}={r[1]}" for r in pg),
                         "cypher": ";".join(f"{r[0]}={r[1]}" for r in neo),
                         "total_accounts": total, "identical": same,
                         "sql_seconds": round(tp, 3), "cypher_seconds": round(tn, 3)})

    tag = "_".join(map(str, depths))
    with open(f"results/q4_network_{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(f"\nComparisons: {len(rows)} | all identical: {all(r['identical'] for r in rows)} "
          f"| saved results/q4_network_{tag}.csv")

    if len(depths) > 1:
        fig, ax = plt.subplots(figsize=(8, 5))
        for name in SETS:
            ax.plot(depths, [totals[(name, d)] for d in depths], marker="o", label=f"Set {name} ({SETS[name][0]})")
        ax.set_title("Q4: distinct accounts reached vs maximum number of links")
        ax.set_xlabel("Maximum links (depth)")
        ax.set_ylabel("Distinct accounts reached (count)")
        ax.set_xticks(depths)
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(f"results/q4_count_vs_depth_{tag}.png", dpi=150)
        print(f"Plot saved: results/q4_count_vs_depth_{tag}.png")

    # One supporting path (set A, an account four links away through a shared device and an owner)
    path = db.run_neo(Q4_PATH_CYPHER, {"account": 998, "target": 228917})
    print("\nSupporting path (Cypher SHORTEST 1), account 998 -> account 228917:")
    for p, links, length in path:
        print("  " + "  ".join(f"{n} -[{l}]-" for n, l in zip(p, links)) + f"  {p[-1]}   (length {length})")
    db.close()


if __name__ == "__main__":
    main()
