"""Stress test: a rebalance storm.

Hammer the ring with hundreds of random add/remove operations against a large key
set and assert the two properties that must never break, no matter the churn:

- Every key always maps to a node that is currently in the ring (no dangling
  ownership after a removal).
- Each single membership change only moves a small, bounded fraction of keys - the
  whole point of consistent hashing. Plain hash % N would remap almost everything on
  every change; this asserts we don't.
"""

from __future__ import annotations

import random

from hashring import HashRing


def test_ownership_never_dangles_under_churn():
    rng = random.Random(2024)
    keys = [f"key-{i}" for i in range(3000)]
    ring = HashRing([f"node-{i}" for i in range(8)], replicas=150)

    for _ in range(300):
        live = set(ring.nodes)
        # Randomly add a fresh node or drop an existing one (keep at least 1).
        if rng.random() < 0.5 or len(live) <= 1:
            ring.add(f"node-{rng.randint(0, 40)}")
        else:
            ring.remove(rng.choice(list(live)))

        live = set(ring.nodes)
        # Spot-check a sample of keys each round; all must land on a live node.
        for k in rng.sample(keys, 200):
            assert ring.get(k) in live


def test_single_change_moves_bounded_fraction_across_many_rounds():
    rng = random.Random(99)
    keys = [f"key-{i}" for i in range(5000)]
    # Start with a healthy cluster so 1/N is already small.
    ring = HashRing([f"node-{i}" for i in range(10)], replicas=200)

    worst = 0.0
    for _ in range(60):
        before = {k: ring.get(k) for k in keys}
        if rng.random() < 0.5:
            ring.add(f"node-{rng.randint(0, 60)}")
        elif len(ring.nodes) > 1:
            ring.remove(rng.choice(ring.nodes))
        else:
            ring.add(f"node-{rng.randint(0, 60)}")

        after = {k: ring.get(k) for k in keys}
        moved = sum(1 for k in keys if before[k] != after[k])
        frac = moved / len(keys)
        worst = max(worst, frac)
        # A single membership change on a cluster this size should never move
        # anywhere near half the keys. Modulo hashing would move ~all of them.
        assert frac < 0.35, f"a single change moved {frac:.1%} of keys"

    # And typically it's much smaller than the ceiling.
    assert worst < 0.35


def test_ring_recovers_to_empty_and_back():
    ring = HashRing(replicas=50)
    assert ring.get("k") is None
    for i in range(20):
        ring.add(f"n{i}")
    assert ring.get("k") in set(ring.nodes)
    for n in list(ring.nodes):
        ring.remove(n)
    # Fully drained: no owner for any key, and no crash.
    assert ring.get("k") is None
    assert len(ring) == 0
