"""5.4 Q7 Shortest person-only directed payment path, bounds 4 and 6, full month."""
import csv
import os
import time

import db
from cases import SETS
from queries import Q7_EDGE_CHECK_SQL, Q7_SQL, q7_cypher


def valid_path(path, source, dest):
    """Every step must be a stored transfer and every account a person."""
    if path is None:
        return None
    if path[0] != source or path[-1] != dest:
        return False
    for s, r in zip(path, path[1:]):
        exists, role = db.run_pg(Q7_EDGE_CHECK_SQL, {"s": s, "r": r})[0]
        if not exists or role != "person":
            return False
    return True


def main():
    os.makedirs("results", exist_ok=True)
    out = []
    print(f"{'set':<4}{'source':>8}{'dest':>8}{'bound':>6}  {'SQL len':>7}{'Cyp len':>8}  "
          f"{'SQL s':>7}{'Cyp s':>7}  same len  paths valid  SQL path | Cypher path")
    print("-" * 150)
    for name, (source, dest, _day) in SETS.items():
        for bound in (4, 6):
            p = {"source": source, "dest": dest, "max_depth": bound}
            t0 = time.perf_counter(); pg = db.run_pg(Q7_SQL, p); tp = time.perf_counter() - t0
            t0 = time.perf_counter(); neo = db.run_neo(q7_cypher(bound), {"source": source, "dest": dest}); tn = time.perf_counter() - t0
            pl, pp = (pg[0] if pg else (None, None))
            nl, np_ = neo[0] if neo else (None, None)
            same = pl == nl
            vp, vn = valid_path(pp, source, dest), valid_path(np_, source, dest)
            valid = "n/a (none)" if pp is None and np_ is None else f"{vp}/{vn}"
            print(f"{name:<4}{source:>8}{dest:>8}{bound:>6}  {str(pl):>7}{str(nl):>8}  {tp:>7.2f}{tn:>7.2f}  "
                  f"{'YES' if same else 'NO':<8}  {valid:<11}  {pp} | {np_}")
            out.append({"set": name, "source": source, "dest": dest, "bound": bound,
                        "sql_length": pl, "cypher_length": nl, "same_length": same,
                        "sql_path": pp, "cypher_path": np_, "sql_valid": vp, "cypher_valid": vn,
                        "sql_seconds": round(tp, 3), "cypher_seconds": round(tn, 3)})
    print(f"\nAll lengths identical: {all(r['same_length'] for r in out)}")
    print("Paths may differ between engines when several shortest paths exist; each is checked against stored data.")
    with open("results/q7_shortest_paths.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out[0].keys()); w.writeheader(); w.writerows(out)
    db.close()


if __name__ == "__main__":
    main()
