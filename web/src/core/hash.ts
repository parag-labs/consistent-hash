// FNV-1a hashes, the shared primitive that makes placement identical across every
// port. 32-bit uses Math.imul for a real 32-bit multiply; 64-bit uses BigInt.

export function fnv1a32(s: string): number {
  let h = 0x811c9dc5;
  const bytes = new TextEncoder().encode(s);
  for (const b of bytes) {
    h ^= b;
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

const FNV64_OFFSET = 0xcbf29ce484222325n;
const FNV64_PRIME = 0x100000001b3n;
export const MASK64 = 0xffffffffffffffffn;

export function fnv1a64(s: string): bigint {
  let h = FNV64_OFFSET;
  const bytes = new TextEncoder().encode(s);
  for (const b of bytes) {
    h ^= BigInt(b);
    h = (h * FNV64_PRIME) & MASK64;
  }
  return h;
}

export function isPrime(n: number): boolean {
  if (n < 2) return false;
  if (n % 2 === 0) return n === 2;
  for (let i = 3; i * i <= n; i += 2) {
    if (n % i === 0) return false;
  }
  return true;
}
