import { fnv1a64, MASK64 } from "./hash";

// Jump consistent hash (Lamping & Veach, 2014) over an ordered bucket list. No
// per-node state, O(ln N) lookups; buckets are an ordered range.
export class Jump {
  private nodeList: string[];

  constructor(nodes: string[] = []) {
    this.nodeList = [...nodes];
  }

  add(node: string): void {
    if (!this.nodeList.includes(node)) this.nodeList.push(node);
  }

  remove(node: string): void {
    const i = this.nodeList.indexOf(node);
    if (i >= 0) this.nodeList.splice(i, 1);
  }

  get(key: string): string | null {
    if (this.nodeList.length === 0) return null;
    return this.nodeList[jumpConsistentHash(fnv1a64(key), this.nodeList.length)];
  }

  get nodes(): string[] {
    return [...this.nodeList];
  }

  get size(): number {
    return this.nodeList.length;
  }
}

// Maps key to a bucket in [0, numBuckets) with O(1) memory.
export function jumpConsistentHash(key: bigint, numBuckets: number): number {
  if (numBuckets < 1) throw new Error("numBuckets must be at least 1");
  let k = key & MASK64;
  let b = -1;
  let j = 0;
  const LCG = 2862933555777941757n;
  while (j < numBuckets) {
    b = j;
    k = (k * LCG + 1n) & MASK64;
    j = Math.floor((b + 1) * (2 ** 31 / (Number(k >> 33n) + 1)));
  }
  return b;
}
