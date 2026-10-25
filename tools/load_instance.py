#!/usr/bin/env python3
"""Read portable JSPSF JSON, OPL DAT, or JSPSF-GENERIC-V1 TXT files.

Python 3.10+; standard library only. Arrays use Python's zero-based indexing,
while machine identifiers and identifiers in TXT files are one-based.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CORE_FIELDS = ("NbJobs", "NbMachines", "NbOps", "P", "M", "FF")


def _integer(value: Any) -> bool:
    return type(value) is int


def _without_opl_comments(text: str) -> str:
    # Preserve quoted strings, including paths, while removing comments.
    token = re.compile(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\r\n]*', re.S)
    return token.sub(lambda match: match[0] if match[0].startswith('"') else " ", text)


def _opl_array(text: str, name: str) -> list[Any]:
    match = re.search(r"\b" + re.escape(name) + r"\s*=\s*\[", text)
    if match is None:
        raise ValueError(f"Missing DAT array: {name}")
    start = match.end() - 1
    depth = 0
    for end in range(start, len(text)):
        depth += (text[end] == "[") - (text[end] == "]")
        if depth == 0:
            try:
                value = ast.literal_eval(text[start : end + 1])
            except (SyntaxError, ValueError) as exc:
                raise ValueError(f"Invalid DAT array: {name}") from exc
            if not isinstance(value, list):
                raise ValueError(f"DAT {name} must be an array")
            return value
    raise ValueError(f"Unclosed DAT array: {name}")


def _load_dat(text: str) -> dict[str, Any]:
    clean = _without_opl_comments(text)
    data: dict[str, Any] = {}
    for name in ("NbJobs", "NbMachines"):
        match = re.search(r"\b" + name + r"\s*=\s*([-+]?\d+)\s*;", clean)
        if match is None:
            raise ValueError(f"Missing DAT integer: {name}")
        data[name] = int(match[1])
    for name in ("NbOps", "P", "M", "FF"):
        data[name] = _opl_array(clean, name)
    for name in ("InstanceName", "SourceInstance"):
        match = re.search(r"\b" + name + r'\s*=\s*("(?:\\.|[^"\\])*")\s*;', clean)
        if match:
            data[name] = json.loads(match[1])

    # OPL uses rectangular MaxOps arrays. Only NbOps[job] entries exist.
    # Keep the complete job dimension so malformed extra/missing jobs fail.
    n = data["NbOps"]
    if not isinstance(n, list) or not all(_integer(v) and v > 0 for v in n):
        raise ValueError("DAT NbOps must contain positive integers")
    for name in ("P", "M"):
        if len(data[name]) != len(n) or not all(isinstance(row, list) for row in data[name]):
            raise ValueError(f"DAT {name} job dimension does not match NbOps")
        data[name] = [row[:count] for row, count in zip(data[name], n)]
    if len(data["FF"]) != len(n):
        raise ValueError("DAT FF job dimension does not match NbOps")
    normalized_ff = []
    for matrix, count in zip(data["FF"], n):
        if not isinstance(matrix, list) or not all(isinstance(row, list) for row in matrix):
            raise ValueError("DAT FF must contain adjacency matrices")
        normalized_ff.append([row[:count] for row in matrix[:count]])
    data["FF"] = normalized_ff
    return data


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    active: str | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"\[([A-Z_]+)\]", line)
        if match:
            name = match[1]
            if name.startswith("END_"):
                active = None
            else:
                active = name
                if name in sections:
                    raise ValueError(f"Duplicate TXT section: {name}")
                sections[name] = []
        elif active:
            sections[active].append(line)
    return sections


def _load_txt(text: str) -> dict[str, Any]:
    sections = _sections(text)
    for name in ("INSTANCE", "OPERATIONS", "PRECEDENCE"):
        if name not in sections:
            raise ValueError(f"Missing TXT section: [{name}]")
    metadata = {}
    for line in sections["INSTANCE"]:
        if "=" in line:
            name, value = line.split("=", 1)
            metadata[name.strip()] = value.strip()
    try:
        jobs, machines = int(metadata["NbJobs"]), int(metadata["NbMachines"])
    except (KeyError, ValueError) as exc:
        raise ValueError("TXT needs integer NbJobs and NbMachines metadata") from exc
    if jobs <= 0 or machines <= 0:
        raise ValueError("NbJobs and NbMachines must be positive")

    operations: dict[tuple[int, int], tuple[int, int]] = {}
    n = [0] * jobs
    for line in sections["OPERATIONS"]:
        try:
            job, operation, machine, duration = map(int, line.split())
        except ValueError as exc:
            raise ValueError(f"Invalid TXT operation row: {line}") from exc
        if not 1 <= job <= jobs or operation < 1:
            raise ValueError(f"TXT operation identifiers outside range: {line}")
        if (job, operation) in operations:
            raise ValueError(f"Duplicate TXT operation: job {job}, operation {operation}")
        operations[job, operation] = machine, duration
        n[job - 1] = max(n[job - 1], operation)
    if any(count == 0 for count in n):
        raise ValueError("Every TXT job must contain at least one operation")
    data: dict[str, Any] = {
        "NbJobs": jobs,
        "NbMachines": machines,
        "NbOps": n,
        "P": [[0] * count for count in n],
        "M": [[0] * count for count in n],
        "FF": [[[0] * count for _ in range(count)] for count in n],
    }
    for job, count in enumerate(n, 1):
        for operation in range(1, count + 1):
            if (job, operation) not in operations:
                raise ValueError(f"Missing TXT operation: job {job}, operation {operation}")
            machine, duration = operations[job, operation]
            data["M"][job - 1][operation - 1] = machine
            data["P"][job - 1][operation - 1] = duration
    for line in sections["PRECEDENCE"]:
        try:
            job, predecessor, successor = map(int, line.split())
        except ValueError as exc:
            raise ValueError(f"Invalid TXT precedence row: {line}") from exc
        if not 1 <= job <= jobs or not 1 <= predecessor <= n[job - 1] or not 1 <= successor <= n[job - 1]:
            raise ValueError(f"TXT precedence identifiers outside range: {line}")
        data["FF"][job - 1][predecessor - 1][successor - 1] = 1
    for name in ("InstanceName", "SourceInstance"):
        if name in metadata:
            data[name] = metadata[name]
    return data


def validate_instance(data: Any) -> list[str]:
    """Return structural/math errors. Zero durations are allowed at this layer."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Instance must be a JSON object"]
    missing = [name for name in CORE_FIELDS if name not in data]
    if missing:
        return ["Missing fields: " + ", ".join(missing)]
    jobs, machines, n = data["NbJobs"], data["NbMachines"], data["NbOps"]
    if not _integer(jobs) or jobs <= 0:
        errors.append("NbJobs must be a positive integer")
    if not _integer(machines) or machines <= 0:
        errors.append("NbMachines must be a positive integer")
    if not isinstance(n, list) or not all(_integer(count) and count > 0 for count in n):
        errors.append("NbOps must be a list of positive integers")
    if errors:
        return errors
    if len(n) != jobs:
        return ["NbOps length must equal NbJobs"]
    for name in ("P", "M", "FF"):
        if not isinstance(data[name], list) or len(data[name]) != jobs:
            errors.append(f"{name} must contain exactly NbJobs rows/matrices")
    if errors:
        return errors
    for job, count in enumerate(n):
        label = f"Job {job + 1}"
        times, routes, matrix = data["P"][job], data["M"][job], data["FF"][job]
        if not isinstance(times, list) or len(times) != count:
            errors.append(f"{label}: P width must equal NbOps")
        elif any(not _integer(v) or v < 0 for v in times):
            errors.append(f"{label}: P values must be nonnegative integers")
        if not isinstance(routes, list) or len(routes) != count:
            errors.append(f"{label}: M width must equal NbOps")
        elif any(not _integer(v) or not 1 <= v <= machines for v in routes):
            errors.append(f"{label}: machine identifiers must be integers in 1..NbMachines")
        if not isinstance(matrix, list) or len(matrix) != count or any(not isinstance(row, list) or len(row) != count for row in matrix):
            errors.append(f"{label}: FF must be a NbOps by NbOps matrix")
            continue
        if any(not _integer(v) or v not in (0, 1) for row in matrix for v in row):
            errors.append(f"{label}: FF values must be integer 0 or 1")
            continue
        if any(matrix[i][i] for i in range(count)):
            errors.append(f"{label}: FF contains a self-loop")
        incoming = [sum(row[i] for row in matrix) for i in range(count)]
        ready = [i for i, degree in enumerate(incoming) if degree == 0]
        visited = 0
        while ready:
            predecessor = ready.pop()
            visited += 1
            for successor, edge in enumerate(matrix[predecessor]):
                if edge:
                    incoming[successor] -= 1
                    if incoming[successor] == 0:
                        ready.append(successor)
        if visited != count:
            errors.append(f"{label}: FF contains a directed cycle")
    return errors


def load_instance(path: str | Path) -> dict[str, Any]:
    """Read an instance and validate its six core scheduling fields.

    JSON preserves additional metadata. DAT padding outside NbOps is removed.
    MAT files remain archival sources; read their canonical JSON counterparts.
    """
    path = Path(path)
    if path.suffix.lower() not in (".json", ".dat", ".txt"):
        raise ValueError(f"Unsupported extension {path.suffix!r}; use a JSON, DAT, or TXT counterpart")
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    elif path.suffix.lower() == ".dat":
        data = _load_dat(text)
    elif path.suffix.lower() == ".txt":
        data = _load_txt(text)
    errors = validate_instance(data)
    if errors:
        raise ValueError("; ".join(errors))
    return data


def transitive_closure(matrix: list[list[int]]) -> list[list[int]]:
    """Return the reachability adjacency matrix without changing the input."""
    count = len(matrix)
    masks = [sum(int(edge) << i for i, edge in enumerate(row)) for row in matrix]
    for intermediate in range(count):
        bit = 1 << intermediate
        for source in range(count):
            if masks[source] & bit:
                masks[source] |= masks[intermediate]
    return [[(mask >> target) & 1 for target in range(count)] for mask in masks]


def mathematical_fingerprint(data: dict[str, Any], closure: bool = False) -> str:
    """SHA256 of sorted compact JSON for the six fields, excluding metadata.

    closure=False preserves the supplied direct FF arcs; closure=True uses
    reachability, so adding a redundant direct arc does not change that hash.
    """
    core = {name: data[name] for name in CORE_FIELDS}
    if closure:
        core["FF"] = [transitive_closure(matrix) for matrix in data["FF"]]
    payload = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def instance_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Return dimensions, processing workload, and precedence arc counts."""
    return {
        "instance": data.get("InstanceName", data.get("SourceInstance", "")),
        "jobs": data["NbJobs"],
        "machines": data["NbMachines"],
        "operations": sum(data["NbOps"]),
        "operations_per_job": data["NbOps"],
        "total_processing_time": sum(sum(row) for row in data["P"]),
        "direct_arcs": sum(sum(sum(row) for row in matrix) for matrix in data["FF"]),
        "closure_arcs": sum(sum(sum(row) for row in transitive_closure(matrix)) for matrix in data["FF"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSON, DAT, or generic TXT instance")
    parser.add_argument("--summary", action="store_true", help="Print summary instead of normalized data")
    args = parser.parse_args()
    try:
        data = load_instance(args.path)
        print(json.dumps(instance_summary(data) if args.summary else data, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
