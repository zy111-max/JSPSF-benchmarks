#!/usr/bin/env python3
"""Build the JSPSF v2.0 data set from the v1 canonical JSON; standard library only.

    python v2/tools/build_v2.py [--v1-root .] [--out v2]

Python 3.10+. Same input, same bytes: seeds come from generate_v2.seed_for.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
from pathlib import Path

from generate_v2 import Design, closure_of, design_instance, log10_sequences, lower_bound, seed_for
from rule_v2 import plan

VERSION = "2.0.0"


def load_bound(data):
    """The bound of v1 experiments: largest machine load or job work."""
    load = {}
    for times, machines in zip(data["P"], data["M"]):
        for t, m in zip(times, machines):
            load[m] = load.get(m, 0) + t
    return max(max(load.values()), max(map(sum, data["P"])))


def flexibility(ff, counts):
    masks = [closure_of(m) for m in ff]
    pairs = sum(n * (n - 1) // 2 for n in counts)
    reachable = sum(m.bit_count() for job in masks for m in job)
    return dict(stored=sum(map(sum, (row for m in ff for row in m))), reachable=reachable,
                share=1 - reachable / pairs, space=sum(log10_sequences(job) for job in masks))


def dat_text(d, meta):
    n = d["NbOps"]
    rows = lambda table: ",\n".join(f"    [{', '.join(map(str, row))}]" for row in table)
    jobs_ff = ",\n".join("    [\n" + ",\n".join(f"        [{', '.join(map(str, row))}]" for row in matrix) + "\n    ]" for matrix in d["FF"])
    return (f"// JSPSF v{VERSION}, series {d['Series']}: P and M from {d['BaseCanonicalID']} ({d['BaseInstanceName']}), JSPLIB source {meta['source']}.\n"
            f"// FF source: staged sequence-flexibility design, tools/generate_v2.py.\n"
            f"// FF seed = {meta['seed']}; target unordered share {meta['design'].share}.\n\n"
            f'InstanceName = "{d["InstanceName"]}";\n'
            f'// BaseInstanceName = "{d["BaseInstanceName"]}"\n'
            f'ResultFile = "{d["InstanceName"]}_schedule.csv";\n\n'
            f"NbJobs = {d['NbJobs']};\nNbMachines = {d['NbMachines']};\nTotalOps = {sum(n)};\nMaxOps = {max(n)};\n\n"
            f"NbOps = [{', '.join(map(str, n))}];\n\n"
            f"Exists = [\n{rows([[1] * c for c in n])}\n];\n\n"
            f"P = [\n{rows(d['P'])}\n];\n\nM = [\n{rows(d['M'])}\n];\n\nFF = [\n{jobs_ff}\n];\n")


def txt_text(d, meta):
    n = d["NbOps"]
    out = ["# JSPSF-GENERIC-V1", "# Encoding: UTF-8", "# All Job, Operation and Machine identifiers are 1-based.", "",
           "[INSTANCE]", f"InstanceName = {d['InstanceName']}", f"BaseInstanceName = {d['BaseInstanceName']}",
           f"SourceInstance = {meta['source']}", f"NbJobs = {d['NbJobs']}", f"NbMachines = {d['NbMachines']}",
           f"TotalOps = {sum(n)}", f"MaxOps = {max(n)}", f"Version = {VERSION}", f"Series = {d['Series']}",
           "FFSource = staged sequence-flexibility design", f"Seed = {meta['seed']}",
           f"DirectEdges = {sum(map(sum, (row for m in d['FF'] for row in m)))}", "", "[OPERATIONS]",
           "# Job Operation Machine ProcessingTime"]
    for job, (times, machines) in enumerate(zip(d["P"], d["M"]), 1):
        out += [f"{job} {op} {m} {t}" for op, (t, m) in enumerate(zip(times, machines), 1)]
    out += ["[END_OPERATIONS]", "", "[PRECEDENCE]", "# Job PredecessorOperation SuccessorOperation"]
    for job, matrix in enumerate(d["FF"], 1):
        out += [f"{job} {a} {b}" for a, row in enumerate(matrix, 1) for b, edge in enumerate(row, 1) if edge]
    out += ["[END_PRECEDENCE]", "", "[END_INSTANCE]", ""]
    return "\n".join(out)


def csv_text(header, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("v2"))
    args = parser.parse_args()
    sys.path.insert(0, str(args.v1_root / "tools"))
    from load_instance import load_instance, mathematical_fingerprint

    sources = {r["InstanceName"]: r["SourceInstance"] for r in csv.DictReader(
        open(args.v1_root / "metadata" / "conversion_manifest.csv", encoding="utf-8"))}
    v1_rows = [r for r in csv.DictReader(open(args.v1_root / "metadata" / "instances.csv", encoding="utf-8"))
               if int(r["canonical_id"].split("-")[1]) <= 161]
    for folder in ("canonical", "dat", "txt"):
        (args.out / "data" / folder).mkdir(parents=True, exist_ok=True)
    (args.out / "metadata").mkdir(exist_ok=True)

    instances, manifest, changes, files = [], [], [], []
    complex_count = 0

    def add(path, text, collection, fmt, fingerprints):
        (args.out / path).write_bytes(text.encode("utf-8"))
        files.append(dict(repo_path=path, published_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          collection=collection, format=fmt, input_fingerprint=fingerprints[0], reachability_fingerprint=fingerprints[1]))

    for row in v1_rows:
        base = load_instance(args.v1_root / row["canonical_path"])
        number = row["canonical_id"].split("-")[1]
        counts = base["NbOps"]
        old = flexibility(base["FF"], counts)
        for variant in plan(base["InstanceName"].removesuffix("_SF"), base["NbJobs"], base["NbMachines"], sum(counts), counts[0]):
            design, suffix, series = variant.design, variant.suffix, variant.series
            name = base["InstanceName"] + "2" + suffix
            if series == "S":
                canonical_id = f"JSPSF2-S{number}"
            else:
                complex_count += 1
                canonical_id = f"JSPSF2-C{complex_count:03d}"
            seed = seed_for(base["InstanceName"], series + suffix, design.share)
            ff = design_instance(base, design, seed)
            data = dict(schema="JSPSF-JSON-V2", CanonicalID=canonical_id, InstanceName=name, Version=VERSION, Series=series,
                        BaseCanonicalID=row["canonical_id"], BaseInstanceName=base["InstanceName"],
                        OriginalInstanceName=sources[base["InstanceName"]], NbJobs=base["NbJobs"], NbMachines=base["NbMachines"],
                        NbOps=counts, P=base["P"], M=base["M"], FF=ff)
            new = flexibility(ff, counts)
            bound = max(load_bound(data), lower_bound(data))
            data.update(UnorderedShare=round(new["share"], 4), Log10JobSequences=round(new["space"], 2), LowerBound=bound,
                        FlexDesign=dict(share=design.share, spread=design.spread, longest=design.longest, rigid=design.rigid, seed=str(seed)),
                        SizeClass=variant.size_class, PositiveProcessingTimes=True, ZeroDurationOperations=[])
            canonical = f"data/canonical/{canonical_id}_{name}.json"
            dat, txt = f"data/dat/{name}.dat", f"data/txt/{name}.txt"
            data["SourceFiles"] = [dat, txt]
            prints = mathematical_fingerprint(data), mathematical_fingerprint(data, closure=True)
            meta = dict(source=sources[base["InstanceName"]], seed=seed, design=design)
            collection = "v2-standard" if series == "S" else "v2-complex"
            add(canonical, json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", collection, "json", prints)
            add(dat, dat_text(data, meta), collection, "dat", prints)
            add(txt, txt_text(data, meta), collection, "txt", prints)
            instances.append(dict(canonical_id=canonical_id, canonical_path=canonical, instance_name=name, series=series,
                                  size_class=variant.size_class, base_canonical_id=row["canonical_id"], base_instance=base["InstanceName"],
                                  source_instance=sources[base["InstanceName"]], jobs=base["NbJobs"], machines=base["NbMachines"],
                                  operations=sum(counts), stored_precedence_arcs=new["stored"], reachable_precedence_arcs=new["reachable"],
                                  unordered_share=f"{new['share']:.4f}", log10_job_sequences=f"{new['space']:.2f}", lower_bound=bound,
                                  load_bound=load_bound(data), input_fingerprint=prints[0], reachability_fingerprint=prints[1],
                                  source_files=f"{dat};{txt}"))
            manifest.append(dict(canonical_id=canonical_id, instance_name=name, seed=seed, share=design.share, spread=design.spread,
                                 longest=design.longest, rigid=design.rigid, rule=variant.rule))
            changes.append(dict(instance_name=name, base_instance=base["InstanceName"], series=series,
                                v1_unordered_share=f"{old['share']:.4f}", v2_unordered_share=f"{new['share']:.4f}",
                                v1_log10_job_sequences=f"{old['space']:.2f}", v2_log10_job_sequences=f"{new['space']:.2f}",
                                v1_stored_arcs=old["stored"], v2_stored_arcs=new["stored"], v1_lower_bound=max(load_bound(base), lower_bound(base)),
                                v2_lower_bound=bound, load_bound=load_bound(data), processing_times_changed="no", machines_changed="no"))

    (args.out / "metadata" / "instances.csv").write_text(csv_text(list(instances[0]), instances), encoding="utf-8", newline="\n")
    (args.out / "metadata" / "generation_manifest.csv").write_text(csv_text(list(manifest[0]), manifest), encoding="utf-8", newline="\n")
    (args.out / "metadata" / "changes_from_v1.csv").write_text(csv_text(list(changes[0]), changes), encoding="utf-8", newline="\n")
    (args.out / "metadata" / "files.csv").write_text(csv_text(list(files[0]), files), encoding="utf-8", newline="\n")
    summary = dict(version=VERSION, base="JSPSF-001..161 of v1.0.0", instances=len(instances),
                   standard=sum(r["series"] == "S" for r in instances), complex=sum(r["series"] == "C" for r in instances),
                   data_files=len(files), formats=dict(json=len(instances), dat=len(instances), txt=len(instances)))
    (args.out / "metadata" / "dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
