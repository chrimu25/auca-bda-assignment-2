"""7.2 Combine load-test repetitions (median of 3) for both engines and plot throughput and p95 vs clients."""
import csv
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows = []
for eng in ("pg", "neo"):
    with open(f"results/load/reps_{eng}.csv") as f:
        rows += list(csv.DictReader(f))

summary = []
for wl in ("Q4_d10", "Q7_len_b6"):
    for eng in ("pg", "neo"):
        for c in (1, 4, 8, 16):
            rs = [r for r in rows if r["workload"] == wl and r["engine"] == eng and int(r["clients"]) == c]
            med = lambda k: statistics.median(float(r[k]) for r in rs if r[k] != "")
            summary.append({"workload": wl, "engine": eng, "clients": c, "throughput_rps": round(med("throughput_rps"), 2),
                            "median_ms": round(med("median_ms"), 2), "p95_ms": round(med("p95_ms"), 2),
                            "errors": sum(int(r["errors"]) for r in rs), "timeouts": sum(int(r["timeouts"]) for r in rs),
                            "cpu_pct": round(med("mean_cpu_pct"), 1)})
print(f"{'workload':<10}{'engine':>7}{'clients':>8}{'thr/s':>10}{'median ms':>11}{'p95 ms':>10}{'err':>5}{'to':>4}{'cpu%':>7}")
for s in summary:
    print(f"{s['workload']:<10}{s['engine']:>7}{s['clients']:>8}{s['throughput_rps']:>10.2f}{s['median_ms']:>11.2f}"
          f"{s['p95_ms']:>10.2f}{s['errors']:>5}{s['timeouts']:>4}{s['cpu_pct']:>7}")
with open("results/load/summary_7.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=summary[0].keys()); w.writeheader(); w.writerows(summary)

names = {"pg": "PostgreSQL", "neo": "Neo4j"}
for metric, label, log in (("throughput_rps", "Throughput (correct requests/s)", False),
                           ("p95_ms", "p95 latency (ms, log scale)", True)):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, wl in zip(axes, ("Q4_d10", "Q7_len_b6")):
        for eng in ("pg", "neo"):
            pts = [s for s in summary if s["workload"] == wl and s["engine"] == eng]
            ax.plot([p["clients"] for p in pts], [p[metric] for p in pts], marker="o", label=names[eng])
        ax.set_title(f"{wl}: {label.split(' (')[0]} vs clients")
        ax.set_xlabel("Concurrent clients"); ax.set_ylabel(label); ax.set_xticks([1, 4, 8, 16])
        if log:
            ax.set_yscale("log")
        ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(f"results/load/{metric}_vs_clients.png", dpi=150)
print("\nSaved results/load/summary_7.csv, throughput_rps_vs_clients.png, p95_ms_vs_clients.png")
