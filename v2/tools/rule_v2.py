"""Size rule of JSPSF v2.0: which designs each base instance gets.

ratio = jobs / machines. The levels come from 30 s runs of N8, N8+NSF1 and JMX on 10 shapes:
square shapes stay hard at every level and sequence flexibility matters most near 0.4 to 0.5;
from ratio 1.5 on, machine load decides and more flexibility quickly reaches the load bound;
small rectangular shapes reach it at any level, so there the level only enlarges the search space.
10x10 starts to reach the bound at 0.5, so the complex series raises the share only above 100
operations. Other structures at equal share (long stages, gates on bottleneck machines) were
not harder, so the design stays simple.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from generate_v2 import Design

NO_COMPLEX = {"ft6", "ft20", *(f"la{i}" for i in range(1, 16)), *(f"la{i}" for i in range(26, 36)),
              *(f"swv{i}" for i in range(16, 21))}


@dataclass(frozen=True)
class Variant:
    series: str
    suffix: str
    design: Design
    size_class: str
    rule: str


def size_class(ops):
    return "XS" if ops <= 100 else "S" if ops <= 225 else "M" if ops <= 400 else "L" if ops <= 1000 else "XL"


def standard_share(jobs, machines, ops):
    ratio = jobs / machines
    if ratio <= 1:
        return 0.40 if ops <= 100 else 0.45 if ops <= 225 else 0.50
    if ratio <= 1.4:
        return 0.35
    if ratio < 2:
        return 0.20 if ops <= 225 else 0.30
    return 0.40 if ops <= 300 else 0.20


def complex_share(jobs, machines, ops):
    share = standard_share(jobs, machines, ops)
    return round(share + 0.10, 2) if jobs / machines <= 1.4 and ops > 100 else share


def plan(name, jobs, machines, ops, job_length):
    """Designs of one base instance, name without the _SF suffix."""
    share = standard_share(jobs, machines, ops)
    label = size_class(ops)
    out = [Variant("S", "", Design(share, 0.05, max(3, math.ceil(2.5 * share * job_length)), 0.15), label,
                   f"ratio {jobs / machines:.2f}, {ops} operations: standard share")]
    if name not in NO_COMPLEX:
        share = complex_share(jobs, machines, ops)
        out.append(Variant("C", "C", Design(share, 0.20, max(3, math.ceil(2.5 * (share + 0.2) * job_length)), 0.15), label,
                           f"ratio {jobs / machines:.2f}, {ops} operations: complex share, job shares spread by 0.20"))
    return out
