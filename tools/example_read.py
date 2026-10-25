#!/usr/bin/env python3
"""Print a JSPSF instance's dimensions, processing workload, and arc counts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from load_instance import instance_summary, load_instance, mathematical_fingerprint


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Canonical JSON, OPL DAT, or generic TXT instance")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = parser.parse_args()
    try:
        data = load_instance(args.path)
        summary = instance_summary(data)
        summary["input_ff_sha256"] = mathematical_fingerprint(data)
        summary["closure_sha256"] = mathematical_fingerprint(data, closure=True)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Instance: {summary['instance'] or args.path.stem}")
        print(f"Jobs: {summary['jobs']}; machines: {summary['machines']}; operations: {summary['operations']}")
        print(f"Operations per job: {', '.join(map(str, summary['operations_per_job']))}")
        print(f"Total processing time: {summary['total_processing_time']}")
        print(f"Precedence arcs: {summary['direct_arcs']} supplied; {summary['closure_arcs']} in transitive closure")
        print(f"Input FF SHA256: {summary['input_ff_sha256']}")
        print(f"Closure SHA256: {summary['closure_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
