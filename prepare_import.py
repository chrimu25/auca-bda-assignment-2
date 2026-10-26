"""3.2 Prepare temporary Neo4j import copies with typed headers.

Source CSVs in data/ are left unchanged. Copies are written to import/:
  customers.csv    customer_id:ID(Customer),region:string
  accounts.csv     account_id:ID(Account),:IGNORE,role:string
  devices.csv      device_id:ID(Device),access_type:string
  owns.csv         :START_ID(Customer),:END_ID(Account)        (derived, customer_id, account_id order)
  used_device.csv  :START_ID(Account),:END_ID(Device),first_day:int,last_day:int,observations:int
  transfers.csv    transfer_id:long,:START_ID(Account),:END_ID(Account),occurred_at:long,amount_rwf:int
Data rows are streamed (never loaded fully into memory), except owns.csv,
which is sorted (248,000 small rows).
"""
import csv
import os
import shutil
import time

SRC = "data"
DST = "import"

HEADERS = {
    "customers.csv": "customer_id:ID(Customer),region:string",
    "accounts.csv": "account_id:ID(Account),:IGNORE,role:string",
    "devices.csv": "device_id:ID(Device),access_type:string",
    "account_devices.csv": ":START_ID(Account),:END_ID(Device),first_day:int,last_day:int,observations:int",
    "transfers.csv": "transfer_id:long,:START_ID(Account),:END_ID(Account),occurred_at:long,amount_rwf:int",
}
TARGET_NAME = {"account_devices.csv": "used_device.csv"}


def copy_with_header(name, header):
    src = os.path.join(SRC, name)
    dst = os.path.join(DST, TARGET_NAME.get(name, name))
    rows = 0
    with open(src, "r", newline="") as fin, open(dst, "w", newline="") as fout:
        original_header = fin.readline()
        fout.write(header + "\r\n")   # same line ending as the csv module rows
        for line in fin:
            fout.write(line)
            rows += 1
    print(f"  {dst:<24} rows {rows:>12,}   original header: {original_header.strip()}")
    print(f"  {'':<24} typed header : {header}")
    return rows


def make_owns():
    src = os.path.join(SRC, "accounts.csv")
    dst = os.path.join(DST, "owns.csv")
    with open(src, newline="") as f:
        pairs = [(int(r["customer_id"]), int(r["account_id"])) for r in csv.DictReader(f)]
    pairs.sort()  # customer_id, then account_id
    with open(dst, "w", newline="") as f:
        f.write(":START_ID(Customer),:END_ID(Account)\r\n")
        w = csv.writer(f)
        w.writerows(pairs)
    print(f"  {dst:<24} rows {len(pairs):>12,}   derived from accounts.csv, sorted by customer_id, account_id")
    return len(pairs)


def main():
    t0 = time.perf_counter()
    if os.path.exists(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)
    print(f"Preparing Neo4j import copies in {DST}/ (sources in {SRC}/ unchanged)")
    counts = {name: copy_with_header(name, h) for name, h in HEADERS.items()}
    counts["owns.csv"] = make_owns()
    total_bytes = sum(os.path.getsize(os.path.join(DST, f)) for f in os.listdir(DST))
    print(f"\nFiles: {sorted(os.listdir(DST))}")
    print(f"Nodes to import        : {counts['customers.csv'] + counts['accounts.csv'] + counts['devices.csv']:,} (expected 704,600)")
    print(f"Relationships to import: {counts['owns.csv'] + counts['account_devices.csv'] + counts['transfers.csv']:,} (expected 20,536,900)")
    print(f"Import copies size     : {total_bytes / 1e9:.4f} GB | prepared in {time.perf_counter() - t0:.2f} s")


if __name__ == "__main__":
    main()
