"""4.1 Q1 Account activity: outgoing count and total RWF in the review hour, all six sets."""
import csv
import os

import db
from cases import SETS, cat_text, hour_window
from queries import Q1_CYPHER, Q1_SQL


def main():
    os.makedirs("results", exist_ok=True)
    rows = []
    print("Q1: outgoing transfers in 09:45:00 (inclusive) to 10:45:00 (exclusive) CAT, all receiver roles\n")
    header = f"{'set':<4}{'account':>8}  {'window (CAT)':<41}{'start':>12}{'end':>12}  " \
             f"{'SQL count':>9}{'SQL RWF':>11}  {'Cyp count':>9}{'Cyp RWF':>11}  match"
    print(header)
    print("-" * len(header))
    for name, (account, _dest, day) in SETS.items():
        start, end = hour_window(day)
        params = {"account": account, "start": start, "end": end}
        pg = db.run_pg(Q1_SQL, params)
        neo = db.run_neo(Q1_CYPHER, params)
        match = pg == neo
        (pc, ps), (nc, ns) = pg[0], neo[0]
        window = f"{cat_text(start)} to {cat_text(end)[11:]}"
        print(f"{name:<4}{account:>8}  {window:<41}{start:>12}{end:>12}  "
              f"{pc:>9}{ps:>11,}  {nc:>9}{ns:>11,}  {'YES' if match else 'NO'}")
        rows.append({"set": name, "account": account, "start_epoch": start, "end_epoch": end,
                     "start_cat": cat_text(start), "end_cat": cat_text(end),
                     "sql_count": pc, "sql_total_rwf": ps, "cypher_count": nc, "cypher_total_rwf": ns,
                     "match": match})
    with open("results/q1_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(f"\nAll six sets match: {all(r['match'] for r in rows)}  (saved results/q1_results.csv)")
    db.close()


if __name__ == "__main__":
    main()
