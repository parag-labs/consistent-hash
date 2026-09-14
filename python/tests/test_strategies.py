"""Property tests for the four extra strategies: each must place keys deterministically,
spread load, and move only a bounded fraction of keys when membership changes."""

from __future__ import annotations

from collections import Counter

from strategies import (
    BoundedLoad,
    JumpHash,
    Maglev,
    Rendezvous,
    fnv1a_64,
    jump_consistent_hash,
)


def test_fnv64_matches_known_vectors():
    # Reference FNV-1a 64-bit values every port must reproduce.
    assert fnv1a_64("") == 0xCBF29CE484222325
    assert fnv1a_64("a") == 0xAF63DC4C8601EC8C
    assert fnv1a_64("foobar") == 0x85944171F73967E8


def test_jump_is_stable_and_in_range():
    for key in range(1000):
        b = jump_consistent_hash(key, 17)
        assert 0 <= b < 17
        assert b == jump_consistent_hash(key, 17)


def test_jump_growth_moves_bounded_fraction():
    keys = [f"key-{i}" for i in range(20000)]
    ring = JumpHash([f"node-{i}" for i in range(8)])
    before = {k: ring.get(k) for k in keys}
    ring.add("node-8")
    after = {k: ring.get(k) for k in keys}
    moved = sum(1 for k in keys if before[k] != after[k])
    # 8 -> 9 buckets should move about 1/9 of keys.
    assert moved / len(keys) < 0.20


def test_rendezvous_distribution_is_even():
    hrw = Rendezvous(["a", "b", "c", "d"])
    counts = Counter(hrw.get(f"key-{i}") for i in range(8000))
    for node in ["a", "b", "c", "d"]:
        assert 1300 < counts[node] < 2700


def test_rendezvous_removal_only_moves_that_nodes_keys():
    keys = [f"key-{i}" for i in range(5000)]
    hrw = Rendezvous(["a", "b", "c", "d"])
    before = {k: hrw.get(k) for k in keys}
    hrw.remove("d")
    after = {k: hrw.get(k) for k in keys}
    for k in keys:
        if before[k] != "d":
            assert after[k] == before[k]
        else:
            assert after[k] in {"a", "b", "c"}


def test_rendezvous_weight_biases_load():
    hrw = Rendezvous()
    hrw.add("small", weight=1)
    hrw.add("big", weight=4)
    counts = Counter(hrw.get(f"key-{i}") for i in range(8000))
    assert counts["big"] > counts["small"]


def test_maglev_covers_and_balances():
    mag = Maglev(["a", "b", "c", "d"], table_size=1019)
    counts = Counter(mag.get(f"key-{i}") for i in range(8000))
    assert set(counts) == {"a", "b", "c", "d"}
    # Maglev's table gives a tight spread.
    assert max(counts.values()) - min(counts.values()) < 400


def test_maglev_removal_is_minimal_disruption():
    keys = [f"key-{i}" for i in range(8000)]
    mag = Maglev(["a", "b", "c", "d"], table_size=1019)
    before = {k: mag.get(k) for k in keys}
    mag.remove("d")
    after = {k: mag.get(k) for k in keys}
    moved = sum(1 for k in keys if before[k] != after[k])
    # Removing one of four nodes should move roughly its own share, not much more.
    assert moved / len(keys) < 0.35


def test_bounded_load_caps_hot_nodes():
    nodes = [f"node-{i}" for i in range(5)]
    bl = BoundedLoad(nodes, replicas=200, epsilon=0.25)
    keys = [f"key-{i}" for i in range(5000)]
    for k in keys:
        bl.get(k)
    cap = max(bl.loads.values())
    mean = sum(bl.loads.values()) / len(nodes)
    # No node exceeds (1 + epsilon) * mean by more than a rounding slack.
    assert cap <= (1.25 * mean) + 1


def test_bounded_load_is_idempotent_per_key():
    bl = BoundedLoad(["a", "b", "c"], replicas=100, epsilon=0.5)
    first = bl.get("user-42")
    assert first == bl.get("user-42")


def test_empty_strategies_return_none():
    assert Rendezvous().get("k") is None
    assert JumpHash().get("k") is None
    assert Maglev().get("k") is None
    assert BoundedLoad().get("k") is None
