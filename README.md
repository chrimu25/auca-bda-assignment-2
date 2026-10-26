# Project 2: Mobile Money Investigations (PostgreSQL vs Neo4j)

MSc Advanced Big Data Analytics, AUCA, 2026

**Group members:** _[Member 1 name, ID]_ · _[Member 2 name, ID]_ · _[Member 3 name, ID]_ · _[Member 4 name, ID]_
**Repository:** _[GitHub URL]_

We load the same mobile money data into PostgreSQL (tables) and Neo4j (graph), answer seven investigation questions (Q1–Q7) in both, check that the answers agree, then compare speed, load time, storage and concurrent use.

## Environment we used

| Item | Version / setting |
|---|---|
| Machine | Apple M1, 16 GB RAM, macOS 26.6.2 (8 CPU cores) |
| PostgreSQL | 17.2 (EDB installer), database `mobile_money`, timezone `Africa/Kigali` |
| Neo4j | 2026.10.0 Community (Homebrew), Cypher 25, heap 4 GiB, page cache 3 GiB |
| Java | OpenJDK 21.0.13 |
| Python | 3.14.4 in `.venv` |

## Folder layout

```
mobile_money_generator.py   supplied generator (unchanged, checksum in docs/)
capture.py                  1.2  consume generator streams -> data/*.csv + counts/audit
prepare_import.py           3.2  typed-header copies for neo4j-admin import -> import/
sql/                        2.1-2.2 schema, keys, load/setup, checks; 3.3 account trace
cypher/                     3.2 constraints/indexes and import checks; 3.3 account trace
cases.py                    review sets A-F and CAT time windows
db.py                       run_pg() / run_neo() with persistent connections
queries.py                  all SQL/Cypher pairs (Q1-Q7, Q7 V2, length-only Q7)
run_q1.py ... run_q7.py     4-5  one runner per question
compare.py                  6.1  61-case comparison + 2 independent CSV checks
bench.py                    6.2  21-case timing (one engine at a time)
plans.py                    6.2  EXPLAIN (ANALYZE, BUFFERS) / PROFILE
summarize_timing.py         6.2  combine both engines, ratios, chart
run_6_3.py                  6.3  Q7 bidirectional SQL: check, time, plan
loadtest.py                 7.1  multiprocessing load test with Barrier
loadtest_summary.py         7.2  medians of repetitions + plots
diagrams/                   8.1  transfer cycle and ownership-device diagrams
results/                    all outputs, raw timing runs, plans, load logs
```

CSV files (`data/`, `import/`) and database stores are kept local and are **not** in this repository.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install numpy "psycopg[binary]" neo4j pandas matplotlib python-dotenv psutil
cp .env.example .env        # then fill in your own passwords
```

`.env.example` (placeholder secrets only):

```
PGHOST=localhost
PGPORT=5432
PGDATABASE=mobile_money
PGUSER=postgres
PGPASSWORD=change_me
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change_me
CSV_DIR=data
```

Shell helper used in the commands below:

```bash
psqlmm() { /Library/PostgreSQL/17/bin/psql -h localhost -U postgres -d mobile_money "$@"; }
```

## Commands in execution order

### 0. Check the generator is unchanged

```bash
shasum -a 256 mobile_money_generator.py
cat docs/generator_checksum.txt      # both must show 2ea0e59d...e9455a
```

### 1. Capture (1.2)

```bash
python3 capture.py                    # writes data/*.csv and results/capture_summary.json
```

### 2. PostgreSQL (2.1-2.2, 3.3)

```bash
psqlmm -c "ALTER DATABASE mobile_money SET timezone TO 'Africa/Kigali';"
psqlmm -f sql/01_schema.sql
psqlmm -f sql/03_load_and_setup.sql | tee results/pg_load_2_2.txt    # \copy, then keys (02_keys.sql), indexes, ANALYZE
psqlmm -f sql/04_load_checks.sql   | tee results/pg_checks_2_2.txt
psqlmm -f sql/05_inspect_account.sql | tee results/inspect_998_sql.txt
```

### 3. Neo4j (3.2-3.3)

```bash
python3 prepare_import.py             # typed-header copies in import/
neo4j stop
neo4j-admin database import full neo4j --overwrite-destination=true --id-type=integer \
  --nodes=Customer=import/customers.csv --nodes=Account=import/accounts.csv --nodes=Device=import/devices.csv \
  --relationships=OWNS=import/owns.csv --relationships=USED_DEVICE=import/used_device.csv \
  --relationships=TRANSFER=import/transfers.csv | tee results/neo4j_import_3_2.txt
neo4j start
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f cypher/01_constraints_indexes.cypher | tee results/neo4j_setup_3_2.txt
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f cypher/02_import_checks.cypher      | tee results/neo4j_checks_3_2.txt
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f cypher/03_inspect_account.cypher    | tee results/inspect_998_cypher.txt
rm -rf import/                         # import copies no longer needed
```

### 4-5. Questions Q1-Q7 (both services running)

```bash
mkdir -p results/timing results/plans results/load
python3 run_q1.py | tee results/q1_results.txt
python3 run_q2.py | tee results/q2_results.txt
python3 run_q3.py | tee results/q3_results.txt
python3 run_q4.py | tee results/q4_all_depths.txt
python3 run_q5.py | tee results/q5_results.txt
python3 run_q6.py | tee results/q6_results.txt
python3 run_q7.py | tee results/q7_results.txt
```

### 6.1 Comparison (both services running)

```bash
python3 compare.py | tee results/compare_61.txt      # expect TOTAL: 61/61 match
```

### 6.2 Timing (one service at a time)

```bash
neo4j stop                                            # PostgreSQL only
python3 bench.py --engine pg | tee results/timing/bench_pg.txt
python3 plans.py --engine pg | tee results/plans/plans_pg.txt

sudo -u postgres /Library/PostgreSQL/17/bin/pg_ctl -D /Library/PostgreSQL/17/data stop -m fast
neo4j start                                           # Neo4j only
python3 bench.py --engine neo | tee results/timing/bench_neo.txt
python3 plans.py --engine neo | tee results/plans/plans_neo.txt

python3 summarize_timing.py | tee results/timing/comparison_6_2.txt
```

### 6.3 Q7 SQL improvement

```bash
sudo -u postgres /Library/PostgreSQL/17/bin/pg_ctl -D /Library/PostgreSQL/17/data start
python3 run_6_3.py --check | tee results/q7_v2_check.txt          # both services
neo4j stop
python3 run_6_3.py --time  | tee results/timing/q7_v2_timing.txt  # PostgreSQL only
python3 run_6_3.py --plan  | tee results/plans/plan_q7_v2.txt
```

### 7. Load test (one service at a time)

```bash
python3 loadtest.py --engine pg  | tee results/load/load_pg.txt   # Neo4j stopped
sudo -u postgres /Library/PostgreSQL/17/bin/pg_ctl -D /Library/PostgreSQL/17/data stop -m fast
neo4j start
python3 loadtest.py --engine neo | tee results/load/load_neo.txt  # PostgreSQL stopped
python3 loadtest_summary.py | tee results/load/summary_7.txt
```

### 9.2 Final verification

```bash
sudo -u postgres /Library/PostgreSQL/17/bin/pg_ctl -D /Library/PostgreSQL/17/data start
python3 compare.py | tee results/compare_61_final.txt    # screenshot the 61/61 summary
neo4j stop && neo4j status
sudo -u postgres /Library/PostgreSQL/17/bin/pg_ctl -D /Library/PostgreSQL/17/data stop -m fast
sudo -u postgres /Library/PostgreSQL/17/bin/pg_ctl -D /Library/PostgreSQL/17/data status   # screenshot stopped status
```

## Main results (short)

- All 61 cases give the same answers in both engines; all Q7 paths checked against stored transfers.
- PostgreSQL is faster for lookups and the monthly report (Q2: 1.22 s vs 23.4 s).
- Neo4j is much faster for shortest paths with the first SQL (13.8 s vs 7.5 ms). After our bidirectional SQL rewrite PostgreSQL takes 26-28 ms.
- With 16 clients Neo4j served about 9x (Q4) and 23x (Q7) more requests per second than PostgreSQL.
- Storage: PostgreSQL 3.72 GB, Neo4j 2.06 GB (decimal GB).

Full discussion is in the report PDF.
