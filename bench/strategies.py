"""Benchmark the five strategies against each other on the three things that matter:
disruption on a membership change, load balance, and lookup throughput.

Everything here is measured on this machine and reproducible. Run from the repo root:
``python bench/strategies.py``.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from hashring import HashRing
from strategies import BoundedLoad, JumpHash, Maglev, Rendezvous

RESULTS = ROOT / "bench" / "results"
RESULTS.mkdir(exist_ok=True)

STRATEGIES = ["ring", "rendezvous", "jump", "maglev", "bounded"]
LABELS = {
    "ring": "Ring",
    "rendezvous": "Rendezvous",
    "jump": "Jump",
    "maglev": "Maglev",
    "bounded": "Bounded-load",
}


def build(name: str, nodes: list[str]):
    if name == "ring":
        return HashRing(nodes, replicas=200)
    if name == "rendezvous":
        return Rendezvous(nodes)
    if name == "jump":
        return JumpHash(nodes)
    if name == "maglev":
        return Maglev(nodes, table_size=65537)
    if name == "bounded":
        return BoundedLoad(nodes, replicas=200, epsilon=0.25)
    raise ValueError(name)


def disruption(name: str) -> float:
    """Percent of keys that move when growing an 8-node cluster to 9. Ideal ~= 1/9."""
    keys = [f"key-{i}" for i in range(20000)]
    nodes = [f"node-{i}" for i in range(8)]
    before_obj = build(name, nodes)
    before = {k: before_obj.get(k) for k in keys}
    after_obj = build(name, nodes + ["node-8"])
    after = {k: after_obj.get(k) for k in keys}
    moved = sum(1 for k in keys if before[k] != after[k])
    return moved / len(keys) * 100


def balance(name: str) -> float:
    """Coefficient of variation of load across 8 nodes over 50k keys (lower is more even)."""
    keys = [f"key-{i}" for i in range(50000)]
    nodes = [f"node-{i}" for i in range(8)]
    obj = build(name, nodes)
    counts: dict[str, int] = {n: 0 for n in nodes}
    for k in keys:
        counts[obj.get(k)] += 1
    values = list(counts.values())
    return statistics.pstdev(values) / statistics.mean(values) * 100


def throughput(name: str) -> int:
    """Lookups per second over 100k keys on a 50-node cluster."""
    nodes = [f"node-{i}" for i in range(50)]
    obj = build(name, nodes)
    keys = [f"key-{i}" for i in range(100000)]
    start = time.perf_counter()
    for k in keys:
        obj.get(k)
    elapsed = time.perf_counter() - start
    return int(len(keys) / elapsed)


def main() -> None:
    summary = {}
    for name in STRATEGIES:
        summary[name] = {
            "disruption_pct": round(disruption(name), 2),
            "balance_cov_pct": round(balance(name), 2),
            "lookups_per_sec": throughput(name),
        }

    ideal = 1 / 9 * 100
    labels = [LABELS[s] for s in STRATEGIES]
    disruptions = [summary[s]["disruption_pct"] for s in STRATEGIES]
    balances = [summary[s]["balance_cov_pct"] for s in STRATEGIES]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.bar(labels, disruptions, color="tab:blue")
    ax1.axhline(ideal, ls=":", color="tab:green", label=f"ideal 1/9 = {ideal:.1f}%")
    ax1.set_ylabel("% keys moved adding 1 of 8 nodes")
    ax1.set_title("Disruption on a membership change")
    ax1.legend()
    ax1.tick_params(axis="x", rotation=20)

    ax2.bar(labels, balances, color="tab:purple")
    ax2.set_ylabel("load spread, coeff. of variation (%)")
    ax2.set_title("Load balance (8 nodes, 50k keys)")
    ax2.tick_params(axis="x", rotation=20)

    fig.tight_layout()
    fig.savefig(RESULTS / "strategies.png", dpi=110)
    plt.close(fig)

    (RESULTS / "strategies.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
