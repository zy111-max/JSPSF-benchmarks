#!/usr/bin/env python3
"""Verify published hashes and 221 canonical JSPSF instances; no dependencies."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from load_instance import load_instance, mathematical_fingerprint


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_file(root: Path, value: str) -> Path:
    if "\\" in value or ":" in value:
        raise ValueError("repo_path must use a relative POSIX path")
    relative = PurePosixPath(value)
    if not value or relative.is_absolute() or any(part in (".", "..") for part in value.split("/")):
        raise ValueError("repo_path must stay within the repository")
    candidate = root.joinpath(*relative.parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("repo_path resolves outside the repository") from exc
    if not candidate.is_file():
        raise ValueError("repo_path does not identify an existing file")
    return candidate


def _is_or18(path: Path, data: dict[str, Any]) -> bool:
    labels = [path.stem, str(data.get("InstanceName", "")), str(data.get("SourceInstance", ""))]
    return any(re.search(r"(?:^|[^a-z0-9])or0*18(?:[^a-z0-9]|$)", label.lower()) for label in labels)


def validate_dataset(
    root: str | Path,
    files_csv: str | Path = "metadata/files.csv",
    canonical_dir: str | Path = "data/canonical",
    expected_instances: int = 221,
) -> dict[str, Any]:
    """Return a report. All errors cause CLI exit 1; warnings are nonfatal."""
    root = Path(root).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    declared: set[str] = set()
    verified = 0
    manifest = root / files_csv
    try:
        with manifest.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not {"repo_path", "published_sha256"}.issubset(reader.fieldnames or []):
                errors.append("files.csv needs repo_path and published_sha256 columns")
            else:
                for line, row in enumerate(reader, 2):
                    repo_path = (row.get("repo_path") or "").strip()
                    expected_hash = (row.get("published_sha256") or "").strip()
                    label = f"files.csv line {line} ({repo_path or '<empty>'})"
                    if repo_path in declared:
                        errors.append(f"{label}: duplicate repo_path")
                        continue
                    declared.add(repo_path)
                    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                        errors.append(f"{label}: published_sha256 must be 64 lowercase hexadecimal characters")
                        continue
                    try:
                        path = _relative_file(root, repo_path)
                        actual_hash = _file_sha256(path)
                    except (OSError, ValueError) as exc:
                        errors.append(f"{label}: {exc}")
                        continue
                    if actual_hash != expected_hash:
                        errors.append(f"{label}: SHA256 mismatch (expected {expected_hash}, found {actual_hash})")
                    else:
                        verified += 1
    except (OSError, UnicodeError, csv.Error) as exc:
        errors.append(f"Cannot read files.csv: {exc}")

    # The checksum manifest need not include itself, but all dataset files
    # must be listed, including archival DAT, TXT, and MAT sources.
    data_dir = root / "data"
    for path in sorted(data_dir.rglob("*")) if data_dir.is_dir() else []:
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative not in declared:
                errors.append(f"Unlisted dataset file: {relative}")

    canonical = root / canonical_dir
    paths = sorted(canonical.rglob("*.json")) if canonical.is_dir() else []
    if len(paths) != expected_instances:
        errors.append(f"Expected {expected_instances} canonical JSON files, found {len(paths)}")
    direct: dict[str, list[str]] = defaultdict(list)
    closure: dict[str, list[str]] = defaultdict(list)
    valid_instances = 0
    zero_operations: list[dict[str, Any]] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            data = load_instance(path)
        except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
            errors.append(f"{relative}: {exc}")
            continue
        valid_instances += 1
        direct[mathematical_fingerprint(data)].append(relative)
        closure[mathematical_fingerprint(data, closure=True)].append(relative)
        for job, row in enumerate(data["P"], 1):
            for operation, duration in enumerate(row, 1):
                if duration == 0:
                    machine = data["M"][job - 1][operation - 1]
                    allowed = _is_or18(path, data) and (job, operation, machine) == (10, 10, 4)
                    zero_operations.append({"repo_path": relative, "job": job, "operation": operation, "machine": machine, "allowed_or18": allowed})
                    if allowed:
                        warnings.append(f"{relative}: preserved source or18 zero duration at job 10, operation 10, machine 4")
                    else:
                        errors.append(f"{relative}: unexpected zero duration at job {job}, operation {operation}, machine {machine}")
    if sum(entry["allowed_or18"] for entry in zero_operations) > 1:
        errors.append("The or18 zero-duration exception appears more than once")
    direct_duplicates = {key: values for key, values in direct.items() if len(values) > 1}
    closure_duplicates = {key: values for key, values in closure.items() if len(values) > 1}
    for values in direct_duplicates.values():
        errors.append("Duplicate mathematical input (supplied FF): " + ", ".join(values))
    for values in closure_duplicates.values():
        errors.append("Duplicate mathematical input (FF transitive closure): " + ", ".join(values))
    return {
        "ok": not errors,
        "manifest_rows": len(declared),
        "verified_file_hashes": verified,
        "expected_canonical_instances": expected_instances,
        "canonical_json_files": len(paths),
        "valid_canonical_instances": valid_instances,
        "unique_input_ff_fingerprints": len(direct),
        "unique_closure_fingerprints": len(closure),
        "input_ff_duplicates": direct_duplicates,
        "closure_duplicates": closure_duplicates,
        "zero_duration_operations": zero_operations,
        "warnings": warnings,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."), help="Repository root (default: current directory)")
    parser.add_argument("--files-csv", default="metadata/files.csv", help="Checksum CSV relative to repository root")
    parser.add_argument("--canonical-dir", default="data/canonical", help="Canonical JSON directory relative to repository root")
    parser.add_argument("--expected-instances", type=int, default=221)
    parser.add_argument("--json", action="store_true", help="Print a machine-readable report")
    parser.add_argument("--report", type=Path, help="Also save the JSON report at this path")
    args = parser.parse_args()
    if args.expected_instances <= 0:
        parser.error("--expected-instances must be positive")
    report = validate_dataset(args.root, args.files_csv, args.canonical_dir, args.expected_instances)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{'PASS' if report['ok'] else 'FAIL'}: {report['verified_file_hashes']}/{report['manifest_rows']} published hashes verified; {report['valid_canonical_instances']}/{report['expected_canonical_instances']} canonical instances valid.")
        print(f"Unique scheduling fingerprints: supplied FF={report['unique_input_ff_fingerprints']}; transitive closure={report['unique_closure_fingerprints']}.")
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        for error in report["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
