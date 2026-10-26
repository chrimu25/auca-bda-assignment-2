"""6.2 Plans outside timing: EXPLAIN (ANALYZE, BUFFERS) / PROFILE for Q2, Q4 B depth 10, Q7 B bound 6.

  python3 plans.py --engine pg
  python3 plans.py --engine neo
"""
import argparse
import os

import psycopg

import db
from cases import SETS
from queries import Q2_CYPHER, Q2_SQL, Q4_SQL, Q7_SQL, q4_cypher, q7_cypher

B_ACC, B_DEST, _ = SETS["B"]
PLANS = [
    ("q2_month", Q2_SQL, Q2_CYPHER, {}),
    ("q4_B_depth10", Q4_SQL, q4_cypher(10), {"account": B_ACC, "depth": 10}),
    ("q7_B_bound6", Q7_SQL, q7_cypher(6), {"source": B_ACC, "dest": B_DEST, "max_depth": 6}),
]


def pg_plan(name, sql, params, prefix="pg"):
    conn = db.pg_conn()
    with psycopg.ClientCursor(conn) as cur:          # client-side binding so EXPLAIN accepts the parameters
        cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + sql, params)
        text = "\n".join(r[0] for r in cur.fetchall())
    path = f"results/plans/{prefix}_{name}.txt"
    open(path, "w").write(text + "\n")
    print(f"\n===== PostgreSQL {name} =====\n{text}\nsaved {path}")


def fmt_profile(node, depth=0, lines=None):
    lines = [] if lines is None else lines
    args = node.get("args", {})
    detail = args.get("Details", "")
    lines.append(f"{'  ' * depth}+{node.get('operatorType', '?')}  rows={node.get('rows', args.get('Rows', '?'))}  "
                 f"dbHits={node.get('dbHits', args.get('DbHits', '?'))}  {detail}")
    for child in node.get("children", []):
        fmt_profile(child, depth + 1, lines)
    return lines


def neo_plan(name, cyp, params):
    with db.neo_driver().session(database="neo4j") as session:
        summary = session.run("PROFILE " + cyp, params).consume()
        profile = summary.profile
        lines = fmt_profile(profile)
        total_hits = sum(int(l.split("dbHits=")[1].split()[0]) for l in lines
                         if "dbHits=" in l and l.split("dbHits=")[1].split()[0].isdigit())
        lines.append(f"\nTotal dbHits: {total_hits:,} | result available after {summary.result_available_after} ms, "
                     f"consumed after {summary.result_consumed_after} ms")
    text = "\n".join(lines)
    path = f"results/plans/neo_{name}.txt"
    open(path, "w").write(text + "\n")
    print(f"\n===== Neo4j {name} =====\n{text}\nsaved {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["pg", "neo"], required=True)
    engine = ap.parse_args().engine
    os.makedirs("results/plans", exist_ok=True)
    for name, sql, cyp, params in PLANS:
        if engine == "pg":
            pg_plan(name, sql, params)
        else:
            neo_plan(name, cyp, params)
    db.close()


if __name__ == "__main__":
    main()
