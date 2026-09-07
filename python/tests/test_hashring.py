"""Ring behavior: even-ish distribution, minimal remap on change, replica selection,
and cross-language hash stability."""

from __future__ import annotations

from collections import Counter

from hashring import HashRing, fnv1a_32


def test_empty_ring_returns_none():
    assert HashRing().get("anything") is None


def test_lookup_is_stable():
    ring = HashRing(["a", "b", "c"])
    assert ring.get("user-42") == ring.get("user-42")


def test_every_key_maps_to_a_real_node():
    ring = HashRing(["a", "b", "c"])
    for i in range(500):
        assert ring.get(f"k{i}") in {"a", "b", "c"}


def test_fnv1a_matches_known_vectors():
    # Reference FNV-1a 32-bit values - the same constants every port must produce.
    assert fnv1a_32("") == 0x811C9DC5
    assert fnv1a_32("a") == 0xE40C292C
    assert fnv1a_32("foobar") == 0xBF9CF968


def test_distribution_is_reasonably_even():
    ring = HashRing(["a", "b", "c", "d"], replicas=400)
    counts = Counter(ring.get(f"key-{i}") for i in range(8000))
    # With 4 nodes and 2000 expected each, no node should be wildly off. More
    # virtual nodes tightens the spread; this band leaves room for hash variance.
    for node in ["a", "b", "c", "d"]:
        assert 1300 < counts[node] < 2700


def test_adding_a_node_remaps_only_a_small_fraction():
    keys = [f"key-{i}" for i in range(5000)]
    ring = HashRing(["a", "b", "c"], replicas=200)
    before = {k: ring.get(k) for k in keys}

    ring.add("d")
    after = {k: ring.get(k) for k in keys}
    moved = sum(1 for k in keys if before[k] != after[k])

    # Going 3 -> 4 nodes should move roughly 1/4 of keys; plain modulo would move
    # almost all of them. Allow generous slack but assert it's well under half.
    assert moved / len(keys) < 0.40
    # And every moved key must now live on the new node.
    for k in keys:
        if before[k] != after[k]:
            assert after[k] == "d"


def test_removing_a_node_only_moves_its_keys():
    keys = [f"key-{i}" for i in range(5000)]
    ring = HashRing(["a", "b", "c", "d"], replicas=200)
    before = {k: ring.get(k) for k in keys}

    ring.remove("d")
    after = {k: ring.get(k) for k in keys}
    for k in keys:
        # Only keys that were on "d" may have moved.
        if before[k] != "d":
            assert after[k] == before[k]
        else:
            assert after[k] in {"a", "b", "c"}


def test_get_replicas_returns_distinct_nodes():
    ring = HashRing(["a", "b", "c", "d", "e"], replicas=100)
    reps = ring.get_replicas("some-key", 3)
    assert len(reps) == 3
    assert len(set(reps)) == 3


def test_get_replicas_caps_at_node_count():
    ring = HashRing(["a", "b"], replicas=50)
    assert len(ring.get_replicas("k", 5)) == 2


def test_idempotent_add_and_remove():
    ring = HashRing(replicas=10)
    ring.add("a")
    ring.add("a")  # no-op
    assert ring.nodes == ["a"]
    ring.remove("ghost")  # no-op
    assert ring.nodes == ["a"]
