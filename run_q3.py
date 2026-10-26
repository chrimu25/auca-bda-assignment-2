"""4.3 Q3 Shared devices: other accounts on the review account's devices with overlapping days."""
import csv
import os

import db
from cases import SETS
from queries import Q3_CYPHER, Q3_SQL


def main():
    os.makedirs("results", exist_ok=True)
    out, summary = [], []
    for name, (account, _dest, _day) in SETS.items():
        pg = db.run_pg(Q3_SQL, {"account": account})
        neo = db.run_neo(Q3_CYPHER, {"account": account})
        match = pg == neo
        summary.append((name, account, len(pg), len(neo), match))
        print(f"\n=== Set {name}: review account {account} | SQL rows {len(pg)} | Cypher rows {len(neo)} | "
              f"identical {match}")
        print(f"{'other_account':>14}{'device_id':>11}  {'access_type':<16}{'overlap_start':>14}{'overlap_end':>12}")
        for r in pg:
            print(f"{r[0]:>14}{r[1]:>11}  {r[2]:<16}{r[3]:>14}{r[4]:>12}")
            out.append({"set": name, "review_account": account, "other_account": r[0], "device_id": r[1],
                        "access_type": r[2], "overlap_start": r[3], "overlap_end": r[4]})
    print("\n=== Q3 SUMMARY ===")
    print(f"{'set':<5}{'account':>8}{'SQL rows':>10}{'Cypher rows':>13}  identical")
    for name, account, a, b, m in summary:
        print(f"{name:<5}{account:>8}{a:>10}{b:>13}  {'YES' if m else 'NO'}")
    print(f"Total rows: {sum(s[2] for s in summary)} | all sets identical: {all(s[4] for s in summary)}")
    with open("results/q3_shared_devices.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out[0].keys()); w.writeheader(); w.writerows(out)
    print("Saved results/q3_shared_devices.csv")
    db.close()


if __name__ == "__main__":
    main()
