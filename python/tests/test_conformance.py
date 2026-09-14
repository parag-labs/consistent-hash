"""Conformance: the Python port must reproduce the committed golden vectors exactly.

Every language ships the mirror of this test. If any of them disagrees with
``conformance/vectors.json``, the ports have drifted and CI fails.
"""

from __future__ import annotations

import json
from pathlib import Path

from hashring import HashRing, fnv1a_32
from strategies import BoundedLoad, JumpHash, Maglev, Rendezvous, fnv1a_64

VECTORS = json.loads(
    (Path(__file__).resolve().parents[2] / "conformance" / "vectors.json").read_text(
        encoding="utf-8"
    )
)


def test_hash_probes():
    for probe, expected in VECTORS["hash"]["fnv1a_32"].items():
        assert fnv1a_32(probe) == int(expected, 16)
    for probe, expected in VECTORS["hash"]["fnv1a_64"].items():
        assert fnv1a_64(probe) == int(expected, 16)


def test_ring_matches_vectors():
    spec = VECTORS["ring"]
    ring = HashRing(spec["nodes"], replicas=spec["replicas"])
    for key, node in spec["assignment"].items():
        assert ring.get(key) == node


def test_rendezvous_matches_vectors():
    spec = VECTORS["rendezvous"]
    hrw = Rendezvous(spec["nodes"])
    for key, node in spec["assignment"].items():
        assert hrw.get(key) == node


def test_jump_matches_vectors():
    spec = VECTORS["jump"]
    jump = JumpHash(spec["nodes"])
    for key, node in spec["assignment"].items():
        assert jump.get(key) == node


def test_maglev_matches_vectors():
    spec = VECTORS["maglev"]
    maglev = Maglev(spec["nodes"], table_size=spec["table_size"])
    for key, node in spec["assignment"].items():
        assert maglev.get(key) == node


def test_bounded_load_matches_vectors():
    spec = VECTORS["bounded_load"]
    epsilon = spec["epsilon_num"] / spec["epsilon_den"]
    bounded = BoundedLoad(spec["nodes"], replicas=spec["replicas"], epsilon=epsilon)
    # Bounded-load is order-sensitive: replay the keys in the pinned order.
    for key in spec["keys_in_order"]:
        assert bounded.get(key) == spec["assignment"][key]
