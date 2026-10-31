#!/usr/bin/env python3
"""Check JSPSF v2.0 against its own tables and against v1; standard library only.

    python v2/tools/validate_v2.py [--v1-root .] [--v2-root v2]

Runs tools/validate_dataset.py on v2/ for hashes and structure, then checks that P and M
equal the base instance, that every arc keeps the reference order, that FF holds direct
arcs only, that JSON, DAT and TXT agree, and recomputes every published measure.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from build_v2 import flexibility, load_bound
from generate_v2 import closure_of, lower_bound, reduction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-root", type=Path, default=Path("."))
    parser.add_argument("--v2-root", type=Path, default=Path("v2"))
    args = parser.parse_args()
    sys.path.insert(0, str(args.v1_root / "tools"))
    from load_instance import load_instance, mathematical_fingerprint
    from validate_dataset import validate_dataset

    rows = list(csv.DictReader(open(args.v2_root / "metadata" / "instances.csv", encoding="utf-8")))
    report = validate_dataset(args.v2_root, expected_instances=len(rows))
    errors = list(report["errors"])
    v1 = {r["canonical_id"]: r for r in csv.DictReader(open(args.v1_root / "metadata" / "instances.csv", encoding="utf-8"))}
    v1_closures = {r["reachability_fingerprint"] for r in v1.values()}

    def check(condition, row, text):
        if not condition:
            errors.append(f"{row['instance_name']}: {text}")

    for row in rows:
        data = load_instance(args.v2_root / row["canonical_path"])
        base = load_instance(args.v1_root / v1[row["base_canonical_id"]]["canonical_path"])
        check(data["P"] == base["P"], row, "P differs from the base instance")
        check(data["M"] == base["M"], row, "M differs from the base instance")
        check(data["NbOps"] == base["NbOps"], row, "NbOps differs from the base instance")
        for matrix in data["FF"]:
            check(all(not edge or a < b for a, line in enumerate(matrix) for b, edge in enumerate(line)), row, "an arc breaks the reference order")
            check(reduction(closure_of(matrix)) == matrix, row, "FF is not the transitive reduction")
        direct, closed = mathematical_fingerprint(data), mathematical_fingerprint(data, closure=True)
        check(direct == row["input_fingerprint"], row, "input fingerprint")
        check(closed == row["reachability_fingerprint"], row, "reachability fingerprint")
        check(closed not in v1_closures, row, "same precedence relation as a v1 instance")
        for path in data["SourceFiles"]:
            other = load_instance(args.v2_root / path)
            check(mathematical_fingerprint(other) == direct, row, f"{path} differs from the JSON")
        measured = flexibility(data["FF"], data["NbOps"])
        check(f"{measured['share']:.4f}" == row["unordered_share"], row, "unordered share")
        check(f"{measured['space']:.2f}" == row["log10_job_sequences"], row, "log10 job sequences")
        check(max(load_bound(data), lower_bound(data)) == int(row["lower_bound"]), row, "lower bound")
        check(load_bound(data) == int(row["load_bound"]), row, "load bound")

    print(f"{'PASS' if not errors else 'FAIL'}: {report['verified_file_hashes']}/{report['manifest_rows']} hashes, {len(rows)} instances checked against v1.")
    for error in errors[:40]:
        print("ERROR:", error, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
