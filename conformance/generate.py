"""Generate the cross-language golden vectors from the Python reference.

The output ``vectors.json`` is the contract every port checks itself against: for a
fixed set of nodes and keys, the exact node each strategy places each key on. Because
all ports use the same FNV hashes and the same integer-only placement rules, they
must reproduce these assignments byte-for-byte.

Run from the repo root: ``python conformance/generate.py``. Only re-run when a
strategy's placement rule intentionally changes; the vectors are committed so CI can
diff every language against them without running this script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

from hashring import HashRing, fnv1a_32
from strategies import (
    BoundedLoad,
    JumpHash,
    Maglev,
    Rendezvous,
    fnv1a_64,
)

# Fixed inputs. Node and key names are deliberately plain ASCII so no port trips on
# encoding; the counts are large enough to exercise real placement, small enough to
# keep the JSON readable.
NODES = [f"node-{i}" for i in range(8)]
KEYS = [f"key-{i}" for i in range(200)]
RING_REPLICAS = 100
MAGLEV_TABLE = 4093  # prime; small enough to keep vectors compact
BL_EPSILON_NUM = 1  # epsilon = 1/4, expressed as a fraction so every port agrees
BL_EPSILON_DEN = 4

HASH_PROBES = ["", "a", "ab", "foobar", "node-0", "key-0", "node-0#key-0"]


def hex32(v: int) -> str:
    return f"0x{v:08X}"


def hex64(v: int) -> str:
    return f"0x{v:016X}"


def build() -> dict:
    ring = HashRing(NODES, replicas=RING_REPLICAS)
    hrw = Rendezvous(NODES)
    jump = JumpHash(NODES)
    maglev = Maglev(NODES, table_size=MAGLEV_TABLE)
    bounded = BoundedLoad(NODES, replicas=RING_REPLICAS, epsilon=BL_EPSILON_NUM / BL_EPSILON_DEN)

    return {
        "_comment": "Golden vectors generated from the Python reference. See conformance/README.md.",
        "hash": {
            "fnv1a_32": {p: hex32(fnv1a_32(p)) for p in HASH_PROBES},
            "fnv1a_64": {p: hex64(fnv1a_64(p)) for p in HASH_PROBES},
        },
        "ring": {
            "replicas": RING_REPLICAS,
            "nodes": NODES,
            "assignment": {k: ring.get(k) for k in KEYS},
        },
        "rendezvous": {
            "nodes": NODES,
            "assignment": {k: hrw.get(k) for k in KEYS},
        },
        "jump": {
            "nodes": NODES,
            "assignment": {k: jump.get(k) for k in KEYS},
        },
        "maglev": {
            "table_size": MAGLEV_TABLE,
            "nodes": NODES,
            "assignment": {k: maglev.get(k) for k in KEYS},
        },
        "bounded_load": {
            "replicas": RING_REPLICAS,
            "epsilon_num": BL_EPSILON_NUM,
            "epsilon_den": BL_EPSILON_DEN,
            "nodes": NODES,
            "keys_in_order": KEYS,
            "assignment": {k: bounded.get(k) for k in KEYS},
        },
    }


def main() -> None:
    out = ROOT / "conformance" / "vectors.json"
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
