"""5.3 Q6 Circular payments: 3-8 transfers back to the review account inside its hour, span <= 1800 s."""
import csv
import os

import db
from cases import SETS, cat_text, hour_window
from queries import Q6_CYPHER, Q6_SQL

DETAIL = "SELECT transfer_id, sender_id, receiver_id, occurred_at, amount_rwf FROM transfers WHERE transfer_id = %(t)s"


def main():
    os.makedirs("results", exist_ok=True)
    out, summary = [], []
    for name, (account, _dest, day) in SETS.items():
        start, end = hour_window(day)
        p = {"account": account, "start": start, "end": end}
        pg, neo = db.run_pg(Q6_SQL, p), db.run_neo(Q6_CYPHER, p)
        summary.append((name, account, len(pg), len(neo), pg == neo))
        print(f"\n=== Set {name}: account {account} | SQL cycles {len(pg)} | Cypher cycles {len(neo)} | identical {pg == neo}")
        for path, steps in pg:
            first = last = None
            print(f"  cycle of {steps} transfers: {list(path)}")
            for t in path:
                tid, snd, rcv, ts, amt = db.run_pg(DETAIL, {"t": t})[0]
                first = ts if first is None else first; last = ts
                print(f"    {tid}: {snd} -> {rcv}  {cat_text(ts)} CAT  {amt:,} RWF")
            print(f"    span {last - first} s (limit 1800)")
            out.append({"set": name, "account": account, "steps": steps, "path": " ".join(map(str, path))})
    print("\n=== Q6 SUMMARY ===")
    for name, account, a, b, m in summary:
        print(f"{name:<3}{account:>8}  SQL {a}  Cypher {b}  identical {'YES' if m else 'NO'}")
    print(f"All sets identical: {all(s[4] for s in summary)}")
    with open("results/q6_cycles.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set", "account", "steps", "path"]); w.writeheader(); w.writerows(out)
    db.close()


if __name__ == "__main__":
    main()
