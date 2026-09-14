import { fnv1a64, isPrime } from "./hash";

// Maglev lookup-table hashing (Google, 2016): a fixed prime-sized permutation table,
// built once; each node claims slots in a deterministic interleaving. Lookups are a
// single array index.
export class Maglev {
  private m: number;
  private nodeList: string[];
  private table: number[] = [];

  constructor(nodes: string[] = [], tableSize = 65537) {
    if (!isPrime(tableSize)) throw new Error("tableSize must be prime");
    this.m = tableSize;
    this.nodeList = [...new Set(nodes)].sort();
    this.build();
  }

  add(node: string): void {
    if (!this.nodeList.includes(node)) {
      this.nodeList.push(node);
      this.nodeList.sort();
      this.build();
    }
  }

  remove(node: string): void {
    const i = this.nodeList.indexOf(node);
    if (i >= 0) {
      this.nodeList.splice(i, 1);
      this.build();
    }
  }

  get(key: string): string | null {
    if (this.nodeList.length === 0) return null;
    const slot = Number(fnv1a64(key) % BigInt(this.m));
    return this.nodeList[this.table[slot]];
  }

  get nodes(): string[] {
    return [...this.nodeList];
  }

  get size(): number {
    return this.nodeList.length;
  }

  private build(): void {
    const n = this.nodeList.length;
    if (n === 0) {
      this.table = [];
      return;
    }
    const M = BigInt(this.m);
    const offset: number[] = [];
    const skip: number[] = [];
    for (const name of this.nodeList) {
      offset.push(Number(fnv1a64(`${name}#offset`) % M));
      skip.push(Number(fnv1a64(`${name}#skip`) % BigInt(this.m - 1)) + 1);
    }
    const table = new Array<number>(this.m).fill(-1);
    const next = new Array<number>(n).fill(0);
    let filled = 0;
    while (filled < this.m) {
      for (let i = 0; i < n; i++) {
        let c = (offset[i] + next[i] * skip[i]) % this.m;
        while (table[c] >= 0) {
          next[i] += 1;
          c = (offset[i] + next[i] * skip[i]) % this.m;
        }
        table[c] = i;
        next[i] += 1;
        filled += 1;
        if (filled === this.m) break;
      }
    }
    this.table = table;
  }
}
