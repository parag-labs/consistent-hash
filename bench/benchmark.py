"""Benchmark: consistent hashing vs the naive baseline everyone starts with,
plain ``hash(key) % N``.

Three things are measured, all on this machine and reproducible:

1. Remap cost on a membership change - the headline reason consistent hashing
   exists. Adding one node to an N-node cluster should move about 1/(N+1) of keys;
   modulo moves almost all of them.
2. Distribution quality - how evenly keys spread across nodes, and how the number of
   virtual nodes (replicas) tightens that spread.
3. Lookup throughput - the cost you pay for the nicer remap behavior.

Run: python bench/benchmark.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python" / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from hashring import HashRing, fnv1a_32

RESULTS = Path(__file__).resolve().parent / "results"
RESULTS.mkdir(exist_ok=True)


def modulo_owner(key: str, nodes: list[str]) -> str:
    return nodes[fnv1a_32(key) % len(nodes)]


def bench_remap_vs_modulo() -> dict:
    keys = [f"key-{i}" for i in range(20000)]
    sizes = [4, 8, 16, 32, 64]
    ring_moved, mod_moved, ideal = [], [], []

    for n in sizes:
        nodes = [f"node-{i}" for i in range(n)]

        ring = HashRing(nodes, replicas=200)
        before = {k: ring.get(k) for k in keys}
        ring.add("node-new")
        after = {k: ring.get(k) for k in keys}
        ring_moved.append(sum(1 for k in keys if before[k] != after[k]) / len(keys) * 100)

        mod_before = {k: modulo_owner(k, nodes) for k in keys}
        mod_after = {k: modulo_owner(k, nodes + ["node-new"]) for k in keys}
        mod_moved.append(sum(1 for k in keys if mod_before[k] != mod_after[k]) / len(keys) * 100)

        ideal.append(1 / (n + 1) * 100)

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(sizes, mod_moved, "s--", color="tab:red", label="hash % N (naive)")
    ax.plot(sizes, ring_moved, "o-", color="tab:blue", label="consistent hash")
    ax.plot(sizes, ideal, ":", color="tab:green", label="ideal 1/(N+1)")
    ax.set_xlabel("nodes before the change")
    ax.set_ylabel("% of keys remapped by adding one node")
    ax.set_title("Remap cost: consistent hashing vs modulo")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "remap_vs_modulo.png", dpi=110)
    plt.close(fig)

    return {
        "sizes": sizes,
        "consistent_pct": [round(x, 2) for x in ring_moved],
        "modulo_pct": [round(x, 2) for x in mod_moved],
        "ideal_pct": [round(x, 2) for x in ideal],
    }


def bench_distribution() -> dict:
    keys = [f"key-{i}" for i in range(50000)]
    replica_counts = [1, 10, 50, 100, 200, 400]
    nodes = [f"node-{i}" for i in range(8)]
    cov = []  # coefficient of variation (stddev / mean), lower is more even

    for replicas in replica_counts:
        ring = HashRing(nodes, replicas=replicas)
        counts: dict[str, int] = {n: 0 for n in nodes}
        for k in keys:
            counts[ring.get(k)] += 1
        values = list(counts.values())
        cov.append(statistics.pstdev(values) / statistics.mean(values))

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(replica_counts, [c * 100 for c in cov], "o-", color="tab:purple")
    ax.set_xlabel("virtual nodes per physical node (replicas)")
    ax.set_ylabel("load spread, coeff. of variation (%)")
    ax.set_title("More virtual nodes -> more even load (8 nodes, 50k keys)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "distribution.png", dpi=110)
    plt.close(fig)

    return {
        "replicas": replica_counts,
        "coeff_of_variation_pct": [round(c * 100, 2) for c in cov],
    }


def bench_lookup_throughput() -> dict:
    ring = HashRing([f"node-{i}" for i in range(50)], replicas=200)
    keys = [f"key-{i}" for i in range(100000)]

    start = time.perf_counter()
    for k in keys:
        ring.get(k)
    elapsed = time.perf_counter() - start
    lookups_per_sec = len(keys) / elapsed

    return {
        "lookups": len(keys),
        "seconds": round(elapsed, 4),
        "lookups_per_sec": int(lookups_per_sec),
        "us_per_lookup": round(elapsed / len(keys) * 1e6, 3),
    }


def main() -> None:
    summary = {
        "remap": bench_remap_vs_modulo(),
        "distribution": bench_distribution(),
        "throughput": bench_lookup_throughput(),
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
