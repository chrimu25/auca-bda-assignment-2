"""5.2 Q5 Rapid onward payments: 3 transfers, 4 distinct accounts, <=600 s per step, 90-105 % amounts."""
import csv
import os

import db
from cases import SETS, cat_text, hour_window
from queries import Q5_CYPHER, Q5_SQL

DETAIL = "SELECT transfer_id, sender_id, receiver_id, occurred_at, amount_rwf FROM transfers WHERE transfer_id = %(t)s"


def main():
    os.makedirs("results", exist_ok=True)
    out, summary = [], []
    for name, (account, _dest, day) in SETS.items():
        start, end = hour_window(day)
        p = {"account": account, "start": start, "end": end}
        pg, neo = db.run_pg(Q5_SQL, p), db.run_neo(Q5_CYPHER, p)
        summary.append((name, account, len(pg), len(neo), pg == neo))
        print(f"\n=== Set {name}: account {account} | SQL chains {len(pg)} | Cypher chains {len(neo)} | identical {pg == neo}")
        for t1, t2, t3, final in pg:
            print(f"  chain t1={t1} t2={t2} t3={t3} final receiver={final}")
            prev = None
            for t in (t1, t2, t3):
                tid, snd, rcv, ts, amt = db.run_pg(DETAIL, {"t": t})[0]
                gap = "" if prev is None else f"  +{ts - prev[0]} s, {100 * amt / prev[1]:.1f}% of previous"
                print(f"    {tid}: {snd} -> {rcv}  {cat_text(ts)} CAT  {amt:,} RWF{gap}")
                prev = (ts, amt)
            out.append({"set": name, "account": account, "t1": t1, "t2": t2, "t3": t3, "final_receiver": final})
    print("\n=== Q5 SUMMARY ===")
    for name, account, a, b, m in summary:
        print(f"{name:<3}{account:>8}  SQL {a}  Cypher {b}  identical {'YES' if m else 'NO'}")
    print(f"All sets identical: {all(s[4] for s in summary)}")
    with open("results/q5_rapid_chains.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set", "account", "t1", "t2", "t3", "final_receiver"])
        w.writeheader(); w.writerows(out)
    db.close()


if __name__ == "__main__":
    main()
