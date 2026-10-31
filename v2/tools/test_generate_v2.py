"""Checks of the v2 design functions against brute force on small cases."""
import itertools
import random
import unittest

from generate_v2 import Design, close, closure_of, design_instance, design_job, jackson, log10_sequences, \
    lower_bound, reduction, unordered_share


def extensions(masks):
    n = len(masks)
    return sum(all(not masks[b] >> a & 1 for i, a in enumerate(order) for b in order[i + 1:])
               for order in itertools.permutations(range(n)))


def meets_deadlines(ops, c):
    """Unit-step EDD decides whether preemptive operations can all finish by c - tail."""
    left = [p for _, p, _ in ops]
    for t in range(c):
        ready = [i for i, (r, _, _) in enumerate(ops) if r <= t and left[i]]
        if ready:
            i = min(ready, key=lambda i: -ops[i][2])
            left[i] -= 1
            if not left[i] and t + 1 > c - ops[i][2]:
                return False
    return not any(left)


def preemptive_optimum(ops):
    return next(c for c in itertools.count() if meets_deadlines(ops, c))


class Design_(unittest.TestCase):
    def test_reduction_keeps_closure_and_drops_implied_arcs(self):
        rng = random.Random(1)
        for _ in range(300):
            n = rng.randint(2, 14)
            arcs = [(a, b) for a in range(n) for b in range(a + 1, n) if rng.random() < 0.3]
            masks = close(n, arcs)
            ff = reduction(masks)
            self.assertEqual(closure_of(ff), masks)
            for a in range(n):
                for b in range(n):
                    if ff[a][b]:
                        removed = [row[:] for row in ff]
                        removed[a][b] = 0
                        self.assertNotEqual(closure_of(removed), masks)

    def test_design_points_forward_and_near_target(self):
        rng = random.Random(2)
        design = Design(0.3, 0.0, 6, 0.2)
        shares = []
        for _ in range(100):
            masks = design_job(15, 0.3, design, rng)
            self.assertTrue(all(masks[v] >> w & 1 == 0 for v in range(15) for w in range(v + 1)))
            shares.append(unordered_share(masks))
        self.assertLess(abs(sum(shares) / len(shares) - 0.3), 0.02)

    def test_sequences_match_enumeration(self):
        rng = random.Random(3)
        for _ in range(80):
            n = rng.randint(1, 6)
            masks = close(n, [(a, b) for a in range(n) for b in range(a + 1, n) if rng.random() < 0.4])
            self.assertAlmostEqual(10 ** log10_sequences(masks), extensions(masks), places=6)

    def test_jackson_matches_exhaustive_preemption(self):
        rng = random.Random(4)
        for _ in range(300):
            ops = [(rng.randint(0, 6), rng.randint(1, 5), rng.randint(0, 6)) for _ in range(rng.randint(1, 5))]
            self.assertEqual(jackson(ops), preemptive_optimum(ops), ops)

    def test_chain_gives_a_stronger_bound_than_load(self):
        data = dict(P=[[3, 4], [5, 2]], M=[[1, 2], [2, 1]], FF=[[[0, 1], [0, 0]], [[0, 1], [0, 0]]])
        self.assertEqual(lower_bound(data), 9)

    def test_same_seed_same_design(self):
        base = dict(NbOps=[10] * 5)
        design = Design(0.3, 0.05, 5, 0.2)
        self.assertEqual(design_instance(base, design, 7), design_instance(base, design, 7))
        self.assertNotEqual(design_instance(base, design, 7), design_instance(base, design, 8))


if __name__ == "__main__":
    unittest.main()
