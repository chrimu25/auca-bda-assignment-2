"""4.2 Q2 Daily activity: transfers and total RWF per CAT day for the full month, both engines."""
import csv
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import db
from queries import Q2_CYPHER, Q2_SQL

CAPTURE_COUNT = 20_003_300
CAPTURE_SUM = 231_482_327_870


def main():
    os.makedirs("results", exist_ok=True)
    t0 = time.perf_counter(); pg = db.run_pg(Q2_SQL); t_pg = time.perf_counter() - t0
    t0 = time.perf_counter(); neo = db.run_neo(Q2_CYPHER); t_neo = time.perf_counter() - t0

    print("Q2: transfers and total RWF per CAT day (September 2026)\n")
    print(f"{'day':<12}{'SQL count':>11}{'SQL total RWF':>17}{'Cypher count':>14}{'Cypher total RWF':>18}  match")
    print("-" * 79)
    rows = []
    for (pd_, pc, ps), (nd, nc, ns) in zip(pg, neo):
        m = (pd_, pc, ps) == (nd, nc, ns)
        print(f"{pd_:<12}{pc:>11,}{ps:>17,}{nc:>14,}{ns:>18,}  {'YES' if m else 'NO'}")
        rows.append({"day": pd_, "sql_transfers": pc, "sql_total_rwf": ps,
                     "cypher_transfers": nc, "cypher_total_rwf": ns, "match": m})

    sum_count = sum(r["sql_transfers"] for r in rows)
    sum_value = sum(r["sql_total_rwf"] for r in rows)
    print("\nChecks")
    print(f"  days returned        : SQL {len(pg)}, Cypher {len(neo)} (expected 30)")
    print(f"  all rows identical   : {pg == neo}")
    print(f"  sum of daily counts  : {sum_count:,}  (capture {CAPTURE_COUNT:,})  -> {sum_count == CAPTURE_COUNT}")
    print(f"  sum of daily totals  : {sum_value:,} RWF  (capture {CAPTURE_SUM:,})  -> {sum_value == CAPTURE_SUM}")
    print(f"  query time (single run, not the 6.2 benchmark): SQL {t_pg:.2f} s, Cypher {t_neo:.2f} s")

    with open("results/q2_daily.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    days = [r["day"][5:] for r in rows]
    counts = [r["sql_transfers"] for r in rows]
    values = [r["sql_total_rwf"] / 1e9 for r in rows]

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.bar(days, counts, color="#2b6cb0")
    ax.set_title("Q2: transfers per CAT day, September 2026")
    ax.set_xlabel("Day (MM-DD, CAT)")
    ax.set_ylabel("Transfers (count)")
    ax.set_ylim(min(counts) - 100, max(counts) + 60)
    ax.tick_params(axis="x", rotation=90)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig("results/q2_daily_count.png", dpi=150)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.bar(days, values, color="#d9822b")
    ax.set_title("Q2: total transfer value per CAT day, September 2026")
    ax.set_xlabel("Day (MM-DD, CAT)")
    ax.set_ylabel("Total value (billion RWF)")
    ax.set_ylim(min(values) * 0.99, max(values) * 1.005)
    ax.tick_params(axis="x", rotation=90)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig("results/q2_daily_value.png", dpi=150)

    print("\nSaved results/q2_daily.csv, results/q2_daily_count.png, results/q2_daily_value.png")
    print("Note: both chart y-axes start above zero so the small day-to-day differences are visible.")
    db.close()


if __name__ == "__main__":
    main()
