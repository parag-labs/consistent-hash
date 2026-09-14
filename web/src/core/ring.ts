import { fnv1a32 } from "./hash";

// Consistent-hash ring with virtual nodes: a key is owned by the first node clockwise
// from it, and each node occupies `replicas` points so load spreads evenly.
export class Ring {
  private replicas: number;
  private ring = new Map<number, string>();
  private sorted: number[] = [];
  private nodeSet = new Set<string>();

  constructor(nodes: string[] = [], replicas = 100) {
    if (replicas < 1) throw new Error("replicas must be at least 1");
    this.replicas = replicas;
    for (const n of nodes) this.add(n);
  }

  add(node: string): void {
    if (this.nodeSet.has(node)) return;
    this.nodeSet.add(node);
    for (let r = 0; r < this.replicas; r++) {
      let slot = fnv1a32(`${node}#${r}`);
      while (this.ring.has(slot)) slot = (slot + 1) >>> 0;
      this.ring.set(slot, node);
    }
    this.reindex();
  }

  remove(node: string): void {
    if (!this.nodeSet.has(node)) return;
    this.nodeSet.delete(node);
    for (const [slot, n] of this.ring) {
      if (n === node) this.ring.delete(slot);
    }
    this.reindex();
  }

  get(key: string): string | null {
    if (this.sorted.length === 0) return null;
    return this.ring.get(this.sorted[this.firstClockwise(fnv1a32(key))])!;
  }

  getReplicas(key: string, count: number): string[] {
    const result: string[] = [];
    if (this.sorted.length === 0 || count <= 0) return result;
    const start = this.firstClockwise(fnv1a32(key));
    const cap = Math.min(count, this.nodeSet.size);
    for (let i = 0; i < this.sorted.length; i++) {
      const node = this.ring.get(this.sorted[(start + i) % this.sorted.length])!;
      if (!result.includes(node)) {
        result.push(node);
        if (result.length === cap) break;
      }
    }
    return result;
  }

  get nodes(): string[] {
    return [...this.nodeSet].sort();
  }

  get size(): number {
    return this.nodeSet.size;
  }

  // Ring slots, exposed so the visualizer can draw the circle.
  slots(): { pos: number; node: string }[] {
    return this.sorted.map((pos) => ({ pos, node: this.ring.get(pos)! }));
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

  private reindex(): void {
    this.sorted = [...this.ring.keys()].sort((a, b) => a - b);
  }
}
