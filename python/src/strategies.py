"""Four more placement strategies beyond the ring in :mod:`hashring`.

Consistent hashing is not one algorithm - it's a family, and which member you want
depends on what you're optimizing:

* **Rendezvous (HRW)** - highest-random-weight. No ring state at all: score every
  node for the key and take the max. Naturally supports weights and gives excellent
  spread, at O(N) per lookup.
* **Jump** - Lamping & Veach's jump consistent hash. O(1) memory, no per-node state,
  extremely fast, but buckets are an ordered 0..N-1 range: you can only grow/shrink
  at the end, not remove an arbitrary node.
* **Maglev** - Google's lookup-table hashing. Builds a fixed-size permutation table
  once; lookups are a single array index, and the table gives near-perfect balance
  with minimal disruption when a node leaves.
* **Bounded-load** - consistent hashing with a hard cap on any node's share, so a
  hot node overflows to the next one instead of melting. Wraps the ring.

Every strategy here uses the same FNV hashes as the ring so the Go, Rust, C#, Java,
Python and TypeScript ports all place a given key on the same node. The
transcendental part of *weighted* rendezvous is the one thing kept out of the
cross-language golden vectors (see conformance/README.md) because ``log`` rounds
differently per language; unweighted placement is pure integer math and matches
byte-for-byte.
"""

from __future__ import annotations

import math
from bisect import bisect_right

from hashring import fnv1a_32

FNV64_OFFSET = 0xCBF29CE484222325
FNV64_PRIME = 0x100000001B3
MASK64 = 0xFFFFFFFFFFFFFFFF


def fnv1a_64(data: str) -> int:
    """FNV-1a over UTF-8 bytes, 64-bit. Portable twin of :func:`fnv1a_32`."""
    h = FNV64_OFFSET
    for byte in data.encode("utf-8"):
        h ^= byte
        h = (h * FNV64_PRIME) & MASK64
    return h


class Rendezvous:
    """Highest-random-weight placement. Optional integer weights repeat a node in the
    scoring pool; unweighted scoring is what the golden vectors pin."""

    def __init__(self, nodes: list[str] | None = None) -> None:
        self._weights: dict[str, int] = {}
        for node in nodes or []:
            self.add(node)

    def add(self, node: str, weight: int = 1) -> None:
        if weight < 1:
            raise ValueError("weight must be at least 1")
        self._weights[node] = weight

    def remove(self, node: str) -> None:
        self._weights.pop(node, None)

    def get(self, key: str) -> str | None:
        if not self._weights:
            return None
        weighted = self._is_weighted()
        best_node: str | None = None
        best_score = float("-inf")
        for node, weight in self._weights.items():
            score = self._score(node, key, weight, weighted)
            # Deterministic tie-break by node name keeps every port in agreement.
            if score > best_score or (score == best_score and node > (best_node or "")):
                best_score = score
                best_node = node
        return best_node

    def get_replicas(self, key: str, count: int) -> list[str]:
        if not self._weights or count <= 0:
            return []
        weighted = self._is_weighted()
        ranked = sorted(
            self._weights,
            key=lambda n: (self._score(n, key, self._weights[n], weighted), n),
            reverse=True,
        )
        return ranked[: min(count, len(self._weights))]

    def _is_weighted(self) -> bool:
        return any(w != 1 for w in self._weights.values())

    def _score(self, node: str, key: str, weight: int, weighted: bool) -> float:
        h = fnv1a_64(f"{node}#{key}")
        if not weighted:
            # Pure integer score - portable and what conformance checks.
            return float(h)
        # Weighted HRW: -w / ln(h_normalized), one scale for every node. Kept off the
        # cross-language golden vectors because ``log`` rounds differently per port.
        normalized = (h + 1) / (MASK64 + 1)
        return -weight / math.log(normalized)

    @property
    def nodes(self) -> list[str]:
        return sorted(self._weights)

    def __len__(self) -> int:
        return len(self._weights)


class JumpHash:
    """Jump consistent hash over an ordered bucket list (Lamping & Veach, 2014)."""

    def __init__(self, nodes: list[str] | None = None) -> None:
        self._nodes: list[str] = list(nodes or [])

    def add(self, node: str) -> None:
        if node not in self._nodes:
            self._nodes.append(node)

    def remove(self, node: str) -> None:
        # Only removing the last bucket preserves the jump-hash guarantee; removing
        # from the middle reshuffles tails, which we allow but call out in the docs.
        if node in self._nodes:
            self._nodes.remove(node)

    def get(self, key: str) -> str | None:
        if not self._nodes:
            return None
        bucket = jump_consistent_hash(fnv1a_64(key), len(self._nodes))
        return self._nodes[bucket]

    @property
    def nodes(self) -> list[str]:
        return list(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)


def jump_consistent_hash(key: int, num_buckets: int) -> int:
    """Reference jump consistent hash: O(1) space, O(ln N) time, no lookup table."""
    if num_buckets < 1:
        raise ValueError("num_buckets must be at least 1")
    b, j = -1, 0
    key &= MASK64
    while j < num_buckets:
        b = j
        key = (key * 2862933555777941757 + 1) & MASK64
        j = int((b + 1) * (float(1 << 31) / float((key >> 33) + 1)))
    return b


class Maglev:
    """Maglev lookup-table hashing (Google, 2016). One prime-sized permutation table;
    lookups are a single array index."""

    def __init__(self, nodes: list[str] | None = None, table_size: int = 65537) -> None:
        if not _is_prime(table_size):
            raise ValueError("table_size must be prime")
        self._m = table_size
        self._nodes: list[str] = sorted(set(nodes or []))
        self._table: list[int] = []
        self._build()

    def add(self, node: str) -> None:
        if node not in self._nodes:
            self._nodes.append(node)
            self._nodes.sort()
            self._build()

    def remove(self, node: str) -> None:
        if node in self._nodes:
            self._nodes.remove(node)
            self._build()

    def get(self, key: str) -> str | None:
        if not self._nodes:
            return None
        return self._nodes[self._table[fnv1a_64(key) % self._m]]

    def _build(self) -> None:
        n = len(self._nodes)
        if n == 0:
            self._table = []
            return
        permutation = []
        for name in self._nodes:
            offset = fnv1a_64(f"{name}#offset") % self._m
            skip = fnv1a_64(f"{name}#skip") % (self._m - 1) + 1
            permutation.append((offset, skip))

        table = [-1] * self._m
        next_index = [0] * n
        filled = 0
        while filled < self._m:
            for i in range(n):
                offset, skip = permutation[i]
                candidate = (offset + next_index[i] * skip) % self._m
                while table[candidate] >= 0:
                    next_index[i] += 1
                    candidate = (offset + next_index[i] * skip) % self._m
                table[candidate] = i
                next_index[i] += 1
                filled += 1
                if filled == self._m:
                    break
        self._table = table

    @property
    def nodes(self) -> list[str]:
        return list(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)


class BoundedLoad:
    """Consistent hashing with bounded loads (Google, 2017). Assigns keys clockwise
    on the ring but caps any node at ``ceil((1 + epsilon) * keys / nodes)``; a full
    node overflows to the next one, so no node exceeds its fair share by more than
    ``epsilon``. Assignment depends on the order keys arrive, so it is stateful."""

    def __init__(
        self,
        nodes: list[str] | None = None,
        replicas: int = 100,
        epsilon: float = 0.25,
    ) -> None:
        if epsilon < 0:
            raise ValueError("epsilon must be non-negative")
        self._replicas = replicas
        self._epsilon = epsilon
        self._nodes: list[str] = sorted(set(nodes or []))
        self._ring: dict[int, str] = {}
        self._sorted: list[int] = []
        self._load: dict[str, int] = {}
        self._assigned: dict[str, str] = {}
        self._build_ring()

    def _build_ring(self) -> None:
        self._ring = {}
        for node in self._nodes:
            for r in range(self._replicas):
                slot = fnv1a_32(f"{node}#{r}")
                while slot in self._ring:
                    slot = (slot + 1) & 0xFFFFFFFF
                self._ring[slot] = node
        self._sorted = sorted(self._ring)

    def _capacity(self) -> int:
        n = len(self._nodes)
        total = len(self._assigned) + 1
        return math.ceil((1 + self._epsilon) * total / n)

    def get(self, key: str) -> str | None:
        """Owner of ``key``, respecting the per-node cap. Idempotent for a key that
        is already assigned."""
        if not self._sorted:
            return None
        if key in self._assigned:
            return self._assigned[key]
        cap = self._capacity()
        h = fnv1a_32(key)
        start = bisect_right(self._sorted, h)
        n = len(self._sorted)
        for i in range(n):
            node = self._ring[self._sorted[(start + i) % n]]
            if self._load.get(node, 0) < cap:
                self._assigned[key] = node
                self._load[node] = self._load.get(node, 0) + 1
                return node
        # Every node at cap (only when epsilon is tiny): fall back to first clockwise.
        node = self._ring[self._sorted[start % n]]
        self._assigned[key] = node
        self._load[node] = self._load.get(node, 0) + 1
        return node

    @property
    def loads(self) -> dict[str, int]:
        return dict(self._load)

    @property
    def nodes(self) -> list[str]:
        return list(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True
