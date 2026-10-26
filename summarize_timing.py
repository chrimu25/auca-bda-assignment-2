"""6.2 Combine the two engine summaries: medians, min/max and PostgreSQL/Neo4j median ratio + chart."""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    with open(path) as f:
        return {r["case"]: r for r in csv.DictReader(f)}


def main():
    pg, neo = load("results/timing/summary_pg.csv"), load("results/timing/summary_neo.csv")
    rows = []
    print(f"{'case':<12}{'PG median':>12}{'PG min':>10}{'PG max':>10}{'Neo median':>12}{'Neo min':>10}"
          f"{'Neo max':>10}{'PG/Neo':>9}  faster")
    print("-" * 95)
    for case in pg:
        p, n = pg[case], neo[case]
        pm = float(p["median_ms"]) if p["median_ms"] else None
        nm = float(n["median_ms"]) if n["median_ms"] else None
        ratio = pm / nm if pm and nm else None
        faster = "" if ratio is None else ("Neo4j" if ratio > 1 else "PostgreSQL")
        print(f"{case:<12}{str(p['median_ms']):>12}{str(p['min_ms']):>10}{str(p['max_ms']):>10}"
              f"{str(n['median_ms']):>12}{str(n['min_ms']):>10}{str(n['max_ms']):>10}"
              f"{(f'{ratio:.2f}' if ratio else 'n/a'):>9}  {faster}")
        rows.append({"case": case, "pg_median_ms": p["median_ms"], "pg_min_ms": p["min_ms"], "pg_max_ms": p["max_ms"],
                     "neo_median_ms": n["median_ms"], "neo_min_ms": n["min_ms"], "neo_max_ms": n["max_ms"],
                     "pg_neo_ratio": round(ratio, 3) if ratio else "", "pg_timeouts": p["timeouts"],
                     "neo_timeouts": n["timeouts"], "pg_errors": p["errors"], "neo_errors": n["errors"]})
    with open("results/timing/comparison_6_2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    cases = [r["case"] for r in rows]
    pv = [float(r["pg_median_ms"]) if r["pg_median_ms"] else 0 for r in rows]
    nv = [float(r["neo_median_ms"]) if r["neo_median_ms"] else 0 for r in rows]
    x = range(len(cases))
    fig, ax = plt.subplots(figsize=(14, 5.5))
    ax.bar([i - 0.2 for i in x], pv, width=0.4, label="PostgreSQL", color="#336791")
    ax.bar([i + 0.2 for i in x], nv, width=0.4, label="Neo4j", color="#018bff")
    ax.set_yscale("log")
    ax.set_xticks(list(x)); ax.set_xticklabels(cases, rotation=60, ha="right")
    ax.set_ylabel("Median duration (ms, log scale)")
    ax.set_title("6.2 Median query time per case (5 measured runs after 3 warm-ups)")
    ax.grid(axis="y", alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig("results/timing/medians_6_2.png", dpi=150)
    print("\nSaved results/timing/comparison_6_2.csv and results/timing/medians_6_2.png")


if __name__ == "__main__":
    main()
