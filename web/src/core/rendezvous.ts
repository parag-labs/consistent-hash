import { fnv1a64, MASK64 } from "./hash";

// Highest-random-weight (rendezvous) placement: score every node for the key and take
// the max. No ring, weights are first-class, lookups are O(N).
export class Rendezvous {
  private weights = new Map<string, number>();

  constructor(nodes: string[] = []) {
    for (const n of nodes) this.add(n);
  }

  add(node: string, weight = 1): void {
    if (weight < 1) throw new Error("weight must be at least 1");
    this.weights.set(node, weight);
  }

  remove(node: string): void {
    this.weights.delete(node);
  }

  get(key: string): string | null {
    if (this.weights.size === 0) return null;
    const weighted = this.isWeighted();
    let best: string | null = null;
    let bestScore = -Infinity;
    for (const [node, w] of this.weights) {
      const s = this.score(node, key, w, weighted);
      if (s > bestScore || (s === bestScore && (best === null || node > best))) {
        bestScore = s;
        best = node;
      }
    }
    return best;
  }

  getReplicas(key: string, count: number): string[] {
    if (this.weights.size === 0 || count <= 0) return [];
    const weighted = this.isWeighted();
    return [...this.weights.entries()]
      .map(([node, w]) => ({ node, score: this.score(node, key, w, weighted) }))
      .sort((a, b) => (b.score - a.score) || (a.node < b.node ? 1 : -1))
      .slice(0, Math.min(count, this.weights.size))
      .map((x) => x.node);
  }

  get nodes(): string[] {
    return [...this.weights.keys()].sort();
  }

  get size(): number {
    return this.weights.size;
  }

  private isWeighted(): boolean {
    for (const w of this.weights.values()) if (w !== 1) return true;
    return false;
  }

  private score(node: string, key: string, weight: number, weighted: boolean): number {
    const h = fnv1a64(`${node}#${key}`);
    if (!weighted) return Number(h); // pure integer score - portable, what conformance pins
    const normalized = (Number(h) + 1) / (Number(MASK64) + 1);
    return -weight / Math.log(normalized);
  }
}
