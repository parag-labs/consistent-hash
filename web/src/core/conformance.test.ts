import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import {
  BoundedLoad,
  fnv1a32,
  fnv1a64,
  Jump,
  Maglev,
  Rendezvous,
  Ring,
} from "./index";

// The TypeScript port must reproduce the committed golden vectors exactly.
const here = dirname(fileURLToPath(import.meta.url));
const vectors = JSON.parse(
  readFileSync(resolve(here, "../../../conformance/vectors.json"), "utf-8"),
);

const hex = (s: string) => BigInt(s);

describe("conformance", () => {
  it("fnv hash probes", () => {
    for (const [probe, expected] of Object.entries(vectors.hash.fnv1a_32)) {
      expect(BigInt(fnv1a32(probe))).toBe(hex(expected as string));
    }
    for (const [probe, expected] of Object.entries(vectors.hash.fnv1a_64)) {
      expect(fnv1a64(probe)).toBe(hex(expected as string));
    }
  });

  it("ring", () => {
    const spec = vectors.ring;
    const ring = new Ring(spec.nodes, spec.replicas);
    for (const [key, node] of Object.entries(spec.assignment)) {
      expect(ring.get(key)).toBe(node);
    }
  });

  it("rendezvous", () => {
    const spec = vectors.rendezvous;
    const hrw = new Rendezvous(spec.nodes);
    for (const [key, node] of Object.entries(spec.assignment)) {
      expect(hrw.get(key)).toBe(node);
    }
  });

  it("jump", () => {
    const spec = vectors.jump;
    const jump = new Jump(spec.nodes);
    for (const [key, node] of Object.entries(spec.assignment)) {
      expect(jump.get(key)).toBe(node);
    }
  });

  it("maglev", () => {
    const spec = vectors.maglev;
    const maglev = new Maglev(spec.nodes, spec.table_size);
    for (const [key, node] of Object.entries(spec.assignment)) {
      expect(maglev.get(key)).toBe(node);
    }
  });

  it("bounded-load", () => {
    const spec = vectors.bounded_load;
    const eps = spec.epsilon_num / spec.epsilon_den;
    const bounded = new BoundedLoad(spec.nodes, spec.replicas, eps);
    for (const key of spec.keys_in_order) {
      expect(bounded.get(key)).toBe(spec.assignment[key]);
    }
  });
});
