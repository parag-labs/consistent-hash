"""A consistent-hash ring with virtual nodes.

Consistent hashing maps both keys and nodes onto the same circular hash space, so
adding or removing a node only remaps the keys immediately adjacent to it - not the
whole keyspace, the way plain ``hash(key) % N`` would. Each physical node is placed
at many points on the ring ("virtual nodes" / replicas) so load spreads evenly and
one node leaving doesn't dump all its keys onto a single neighbor.

The hash is a stable, language-neutral one (FNV-1a, 32-bit) so the Python, C#, and
Java ports all place the same node at the same ring position for the same input.
"""

from __future__ import annotations

from bisect import bisect_right


def fnv1a_32(data: str) -> int:
    """FNV-1a over the UTF-8 bytes. Deterministic and portable across languages."""
    h = 0x811C9DC5
    for byte in data.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class HashRing:
    def __init__(self, nodes: list[str] | None = None, replicas: int = 100) -> None:
        if replicas < 1:
            raise ValueError("replicas must be at least 1")
        self.replicas = replicas
        self._ring: dict[int, str] = {}  # ring position -> node
        self._sorted: list[int] = []  # sorted ring positions
        self._nodes: set[str] = set()
        for node in nodes or []:
            self.add(node)

    def _slot(self, node: str, replica: int) -> int:
        return fnv1a_32(f"{node}#{replica}")

    def add(self, node: str) -> None:
        if node in self._nodes:
            return
        self._nodes.add(node)
        for r in range(self.replicas):
            slot = self._slot(node, r)
            # On the rare collision, nudge deterministically to keep every replica.
            while slot in self._ring:
                slot = (slot + 1) & 0xFFFFFFFF
            self._ring[slot] = node
        self._sorted = sorted(self._ring)

    def remove(self, node: str) -> None:
        if node not in self._nodes:
            return
        self._nodes.discard(node)
        self._ring = {slot: n for slot, n in self._ring.items() if n != node}
        self._sorted = sorted(self._ring)

    def get(self, key: str) -> str | None:
        """The node that owns ``key``: the first ring position clockwise from the
        key's hash, wrapping around the end of the ring."""
        if not self._sorted:
            return None
        h = fnv1a_32(key)
        idx = bisect_right(self._sorted, h)
        if idx == len(self._sorted):
            idx = 0  # wrap around
        return self._ring[self._sorted[idx]]

    def get_replicas(self, key: str, count: int) -> list[str]:
        """The first ``count`` distinct physical nodes clockwise from the key - the
        standard way to pick replica holders for redundancy."""
        if not self._sorted or count <= 0:
            return []
        h = fnv1a_32(key)
        start = bisect_right(self._sorted, h)
        result: list[str] = []
        n = len(self._sorted)
        for i in range(n):
            node = self._ring[self._sorted[(start + i) % n]]
            if node not in result:
                result.append(node)
                if len(result) == min(count, len(self._nodes)):
                    break
        return result

    @property
    def nodes(self) -> list[str]:
        return sorted(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)
