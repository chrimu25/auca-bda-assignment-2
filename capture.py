"""1.2 Capture the five generator streams to CSV.

- Inspects g.dataset_info() and g.FIELDS.
- Previews ten records from each iter_<stream>() with itertools.islice (fresh iterators).
- Writes each stream progressively with csv.DictWriter (header first, one row at a time).
- Counts consumed and written rows and compares them with the expected counts.
- Logs every million transfers; records capture seconds and CSV sizes (1 GB = 1e9 bytes).
- Audits transfers: count, earliest/latest occurred_at and sum of amount_rwf.
Never collects a full stream in memory.

Usage:  python3 capture.py  (preview + full capture)
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from itertools import islice

import mobile_money_generator as g

CAT = timezone(timedelta(hours=2), "CAT")
STREAMS = ["customers", "accounts", "devices", "account_devices", "transfers"]
DATA_DIR = "data"
RESULTS_DIR = "results"
TOTAL_EXPECTED = 20_993_500


def now_cat():
    return datetime.now(CAT).isoformat(timespec="seconds")


def cat_text(epoch):
    return datetime.fromtimestamp(epoch, CAT).isoformat(timespec="seconds")


def preview():
    print("=" * 90)
    print("g.dataset_info():")
    print(json.dumps(g.dataset_info(), indent=2, default=list))
    print("\ng.FIELDS:")
    for name, fields in g.FIELDS.items():
        print(f"  {name:<16} {fields}")
    for stream in STREAMS:
        rows = list(islice(getattr(g, f"iter_{stream}")(), 10))   # fresh iterator each time
        print("\n" + "=" * 90)
        print(f"PREVIEW iter_{stream}() - first {len(rows)} records")
        print("=" * 90)
        fields = g.FIELDS[stream]
        print("  ".join(f"{f:>13}" for f in fields))
        for r in rows:
            print("  ".join(f"{r[f]!s:>13}" for f in fields))


def capture_stream(stream, expected):
    path = os.path.join(DATA_DIR, f"{stream}.csv")
    consumed = written = 0
    audit = {"count": 0, "min_occurred_at": None, "max_occurred_at": None, "sum_amount_rwf": 0}
    start_cat = now_cat()
    t0 = time.perf_counter()
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=g.FIELDS[stream])
        writer.writeheader()
        for row in getattr(g, f"iter_{stream}")():
            consumed += 1
            writer.writerow(row)
            written += 1
            if stream == "transfers":
                ts, amt = row["occurred_at"], row["amount_rwf"]
                audit["count"] += 1
                audit["sum_amount_rwf"] += amt
                if audit["min_occurred_at"] is None or ts < audit["min_occurred_at"]:
                    audit["min_occurred_at"] = ts
                if audit["max_occurred_at"] is None or ts > audit["max_occurred_at"]:
                    audit["max_occurred_at"] = ts
                if consumed % 1_000_000 == 0:
                    print(f"  transfers: {consumed:>12,} / {expected:,}  "
                          f"({consumed / expected:6.1%})  {time.perf_counter() - t0:8.1f} s", flush=True)
    seconds = time.perf_counter() - t0
    size = os.path.getsize(path)
    result = {"stream": stream, "csv": path, "consumed": consumed, "written": written,
              "expected": expected, "match": consumed == written == expected,
              "start_cat": start_cat, "end_cat": now_cat(),
              "seconds": round(seconds, 3), "bytes": size, "gb": round(size / 1e9, 6)}
    if stream == "transfers":
        audit["min_occurred_at_cat"] = cat_text(audit["min_occurred_at"])
        audit["max_occurred_at_cat"] = cat_text(audit["max_occurred_at"])
        result["audit"] = audit
    print(f"{stream:<16} consumed {consumed:>12,}  written {written:>12,}  expected {expected:>12,}  "
          f"{'OK' if result['match'] else 'MISMATCH'}  {seconds:8.2f} s  {size / 1e9:8.4f} GB", flush=True)
    return result


def main():
    preview()
    if "--preview" in sys.argv:
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    expected_counts = g.dataset_info()["expected_counts"]

    print("\n" + "=" * 90)
    print(f"CAPTURE started {now_cat()}")
    print("=" * 90)
    t0 = time.perf_counter()
    results = [capture_stream(s, expected_counts[s]) for s in STREAMS]
    total_seconds = time.perf_counter() - t0

    total_consumed = sum(r["consumed"] for r in results)
    total_written = sum(r["written"] for r in results)
    total_bytes = sum(r["bytes"] for r in results)
    audit = results[-1]["audit"]
    all_ok = all(r["match"] for r in results) and total_consumed == total_written == TOTAL_EXPECTED

    print("\n" + "=" * 90)
    print("CAPTURE SUMMARY")
    print("=" * 90)
    print(f"{'stream':<16}{'consumed':>14}{'written':>14}{'expected':>14}{'seconds':>10}{'size GB':>11}  check")
    for r in results:
        print(f"{r['stream']:<16}{r['consumed']:>14,}{r['written']:>14,}{r['expected']:>14,}"
              f"{r['seconds']:>10.2f}{r['gb']:>11.4f}  {'OK' if r['match'] else 'MISMATCH'}")
    print(f"{'TOTAL':<16}{total_consumed:>14,}{total_written:>14,}{TOTAL_EXPECTED:>14,}"
          f"{total_seconds:>10.2f}{total_bytes / 1e9:>11.4f}  {'OK' if all_ok else 'MISMATCH'}")
    print("\nTransfer audit")
    print(f"  count              : {audit['count']:,}")
    print(f"  earliest occurred_at: {audit['min_occurred_at']}  ({audit['min_occurred_at_cat']})")
    print(f"  latest occurred_at : {audit['max_occurred_at']}  ({audit['max_occurred_at_cat']})")
    print(f"  sum amount_rwf     : {audit['sum_amount_rwf']:,} RWF")
    print(f"\nCapture finished {now_cat()}  |  total {total_seconds:.2f} s  |  "
          f"{total_bytes:,} bytes ({total_bytes / 1e9:.4f} GB)")

    with open(os.path.join(RESULTS_DIR, "capture_summary.json"), "w") as f:
        json.dump({"streams": results, "total_consumed": total_consumed, "total_written": total_written,
                   "total_expected": TOTAL_EXPECTED, "total_seconds": round(total_seconds, 3),
                   "total_bytes": total_bytes, "total_gb": round(total_bytes / 1e9, 6),
                   "transfer_audit": audit, "all_counts_match": all_ok}, f, indent=2)
    print(f"Summary saved to {RESULTS_DIR}/capture_summary.json")


if __name__ == "__main__":
    main()