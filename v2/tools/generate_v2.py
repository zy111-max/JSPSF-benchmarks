#!/usr/bin/env python3
"""Sequence-flexibility designs of JSPSF v2.0; Python 3.10+, standard library only.

Processing times, machines and the reference operation order of JSPSF-001..161 stay as
they are; only FF changes. Each job is cut into consecutive stages. Every operation of a
stage precedes every operation of the next one, and inside a stage the operations are
free, split into parallel branches, or sparsely ordered. All arcs point forward, so the
reference order stays feasible and every v2 instance is a relaxation of its classic JSP.
"""
from __future__ import annotations

import hashlib
import heapq
import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Design:
    """share: target fraction of unordered operation pairs; spread: per-job variation around it;
    longest: most operations in one stage; rigid: probability of a one-operation stage."""
    share: float
    spread: float
    longest: int
    rigid: float


def seed_for(*parts) -> int:
    text = "|".join(map(str, ("JSPSF-v2", *parts)))
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def random_stages(n, longest, rigid, rng):
    stages, first = [], 0
    while first < n:
        size = 1 if rng.random() < rigid else rng.randint(2, max(2, longest))
        stages.append(list(range(first, min(n, first + size))))
        first += size
    return stages


def stage_arcs(ops, rng):
    """Arcs inside one stage, all forward in the reference order."""
    kind = rng.choice(("free", "free", "branches", "sparse"))
    if len(ops) < 3 or kind == "free":
        return []
    if kind == "branches":
        tails, arcs = {}, []
        for op in ops:
            branch = rng.randrange(rng.choice((2, 3)))
            if branch in tails:
                arcs.append((tails[branch], op))
            tails[branch] = op
        return arcs
    return [(a, b) for i, a in enumerate(ops) for b in ops[i + 1:] if rng.random() < 0.25]


def close(n, arcs):
    """Successor bitmasks of the transitive closure; arcs must point forward."""
    masks = [0] * n
    for a, b in arcs:
        masks[a] |= 1 << b
    for v in range(n - 1, -1, -1):
        for w in range(v + 1, n):
            if masks[v] >> w & 1:
                masks[v] |= masks[w]
    return masks


def unordered_share(masks):
    n = len(masks)
    pairs = n * (n - 1) // 2
    return 1 - sum(m.bit_count() for m in masks) / pairs if pairs else 0.0


def reduction(masks):
    """FF matrix holding only the direct arcs of a closure."""
    n = len(masks)
    ff = [[0] * n for _ in range(n)]
    for v in range(n):
        implied = 0
        for w in range(n):
            if masks[v] >> w & 1:
                implied |= masks[w]
        for w in range(n):
            if masks[v] >> w & 1 and not implied >> w & 1:
                ff[v][w] = 1
    return ff


def design_job(n, target, design, rng, tries=256):
    """Closure of the candidate whose unordered share is nearest to target."""
    best, gap = None, math.inf
    for _ in range(tries):
        stages = random_stages(n, design.longest, design.rigid, rng)
        arcs = [(a, b) for left, right in zip(stages, stages[1:]) for a in left for b in right]
        for stage in stages:
            arcs += stage_arcs(stage, rng)
        masks = close(n, arcs)
        off = abs(unordered_share(masks) - target)
        if off < gap:
            best, gap = masks, off
    return best


def design_instance(base, design, seed):
    """FF of every job; job targets vary within design.spread."""
    rng = random.Random(seed)
    out = []
    for n in base["NbOps"]:
        target = rng.uniform(design.share - design.spread, design.share + design.spread)
        out.append(reduction(design_job(n, min(0.95, max(0.0, target)), design, rng)))
    return out


def closure_of(matrix):
    """Successor bitmasks of any acyclic FF matrix, whatever its arc order."""
    masks = [sum(edge << i for i, edge in enumerate(row)) for row in matrix]
    for k in range(len(matrix)):
        for v in range(len(matrix)):
            if masks[v] >> k & 1:
                masks[v] |= masks[k]
    return masks


def log10_sequences(masks):
    """log10 of the number of job sequences obeying the closure (linear extensions)."""
    n = len(masks)
    preds = [sum(1 << u for u in range(n) if masks[u] >> v & 1) for v in range(n)]
    counts, full = {0: 1}, (1 << n) - 1
    for _ in range(n):
        layer = {}
        for done, ways in counts.items():
            for v in range(n):
                if not done >> v & 1 and preds[v] & ~done == 0:
                    key = done | 1 << v
                    layer[key] = layer.get(key, 0) + ways
        counts = layer
    return math.log10(counts[full])


def jackson(ops):
    """Preemptive one-machine optimum of (head, p, tail) triples, a valid makespan bound."""
    ops = sorted(ops)
    heap, t, i, bound = [], 0, 0, 0
    while i < len(ops) or heap:
        if not heap:
            t = max(t, ops[i][0])
        while i < len(ops) and ops[i][0] <= t:
            heapq.heappush(heap, (-ops[i][2], ops[i][1]))
            i += 1
        tail, left = heapq.heappop(heap)
        run = left if i == len(ops) else min(left, ops[i][0] - t)
        t += run
        if run < left:
            heapq.heappush(heap, (tail, left - run))
        else:
            bound = max(bound, t - tail)
    return bound


def lower_bound(data):
    """max(job work, Jackson bound of each machine). All F* predecessors of an operation
    belong to its job and cannot overlap, so its head is their total time; same for tails."""
    per_machine, work = {}, 0
    for times, machines, matrix in zip(data["P"], data["M"], data["FF"]):
        work = max(work, sum(times))
        masks = closure_of(matrix)
        n = len(times)
        for v in range(n):
            tail = sum(times[w] for w in range(n) if masks[v] >> w & 1)
            head = sum(times[u] for u in range(n) if masks[u] >> v & 1)
            per_machine.setdefault(machines[v], []).append((head, times[v], tail))
    return max(work, *(jackson(ops) for ops in per_machine.values()))
