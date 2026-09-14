import { fnv1a32 } from "./hash";

// Consistent hashing with bounded loads (Google, 2017): keys are placed clockwise on
// the ring, but no node may exceed ceil((1+epsilon)*keys/nodes). A full node overflows
// to the next under cap. Placement depends on load, so it is stateful and order-sensitive.
export class BoundedLoad {
  private epsilon: number;
  private nodeList: string[];
  private ring = new Map<number, string>();
  private sorted: number[] = [];
  private load = new Map<string, number>();
  private assigned = new Map<string, string>();

  constructor(nodes: string[] = [], replicas = 100, epsilon = 0.25) {
    if (epsilon < 0) throw new Error("epsilon must be non-negative");
    this.epsilon = epsilon;
    this.nodeList = [...new Set(nodes)].sort();
    this.buildRing(replicas);
  }

  get(key: string): string | null {
    if (this.sorted.length === 0) return null;
    const existing = this.assigned.get(key);
    if (existing !== undefined) return existing;
    const cap = this.capacity();
    const start = this.firstClockwise(fnv1a32(key));
    const n = this.sorted.length;
    for (let i = 0; i < n; i++) {
      const node = this.ring.get(this.sorted[(start + i) % n])!;
      if ((this.load.get(node) ?? 0) < cap) {
        this.assign(key, node);
        return node;
      }
    }
    const fallback = this.ring.get(this.sorted[start % n])!;
    this.assign(key, fallback);
    return fallback;
  }

  loads(): Map<string, number> {
    return new Map(this.load);
  }

  get nodes(): string[] {
    return [...this.nodeList];
  }

  get size(): number {
    return this.nodeList.length;
  }

  private assign(key: string, node: string): void {
    this.assigned.set(key, node);
    this.load.set(node, (this.load.get(node) ?? 0) + 1);
  }

  private capacity(): number {
    const total = this.assigned.size + 1;
    return Math.ceil(((1 + this.epsilon) * total) / this.nodeList.length);
  }

  private buildRing(replicas: number): void {
    for (const node of this.nodeList) {
      for (let r = 0; r < replicas; r++) {
        let slot = fnv1a32(`${node}#${r}`);
        while (this.ring.has(slot)) slot = (slot + 1) >>> 0;
        this.ring.set(slot, node);
      }
    }
    this.sorted = [...this.ring.keys()].sort((a, b) => a - b);
  }

  private firstClockwise(h: number): number {
    let lo = 0;
    let hi = this.sorted.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (this.sorted[mid] <= h) lo = mid + 1;
      else hi = mid;
    }
    return lo === this.sorted.length ? 0 : lo;
  }
}
