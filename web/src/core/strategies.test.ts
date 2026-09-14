import { describe, expect, it } from "vitest";
import { BoundedLoad, Jump, Maglev, Rendezvous, Ring } from "./index";

const keys = Array.from({ length: 5000 }, (_, i) => `key-${i}`);

describe("ring", () => {
  it("adding a node remaps only a small fraction, all onto the new node", () => {
    const ring = new Ring(["a", "b", "c"], 200);
    const before = new Map(keys.map((k) => [k, ring.get(k)]));
    ring.add("d");
    let moved = 0;
    for (const k of keys) {
      const after = ring.get(k);
      if (after !== before.get(k)) {
        moved++;
        expect(after).toBe("d");
      }
    }
    expect(moved / keys.length).toBeLessThan(0.4);
  });

  it("returns distinct replicas", () => {
    const ring = new Ring(["a", "b", "c", "d", "e"], 100);
    const reps = ring.getReplicas("some-key", 3);
    expect(reps).toHaveLength(3);
    expect(new Set(reps).size).toBe(3);
  });
});

describe("rendezvous", () => {
  it("removal only moves that node's keys", () => {
    const hrw = new Rendezvous(["a", "b", "c", "d"]);
    const before = new Map(keys.map((k) => [k, hrw.get(k)]));
    hrw.remove("d");
    for (const k of keys) {
      if (before.get(k) !== "d") expect(hrw.get(k)).toBe(before.get(k));
    }
  });

  it("weight biases load", () => {
    const hrw = new Rendezvous();
    hrw.add("small", 1);
    hrw.add("big", 4);
    let big = 0;
    for (let i = 0; i < 8000; i++) if (hrw.get(`key-${i}`) === "big") big++;
    expect(big).toBeGreaterThan(4000);
  });
});

describe("jump", () => {
  it("growth moves a bounded fraction", () => {
    const jump = new Jump(Array.from({ length: 8 }, (_, i) => `node-${i}`));
    const before = new Map(keys.map((k) => [k, jump.get(k)]));
    jump.add("node-8");
    const moved = keys.filter((k) => jump.get(k) !== before.get(k)).length;
    expect(moved / keys.length).toBeLessThan(0.25);
  });
});

describe("maglev", () => {
  it("covers all nodes with a tight spread", () => {
    const mag = new Maglev(["a", "b", "c", "d"], 1019);
    const counts = new Map<string, number>();
    for (let i = 0; i < 8000; i++) {
      const n = mag.get(`key-${i}`)!;
      counts.set(n, (counts.get(n) ?? 0) + 1);
    }
    expect(counts.size).toBe(4);
    const vals = [...counts.values()];
    expect(Math.max(...vals) - Math.min(...vals)).toBeLessThan(400);
  });
});

describe("bounded-load", () => {
  it("caps hot nodes", () => {
    const nodes = Array.from({ length: 5 }, (_, i) => `node-${i}`);
    const bl = new BoundedLoad(nodes, 200, 0.25);
    for (let i = 0; i < 5000; i++) bl.get(`key-${i}`);
    const loadVals = [...bl.loads().values()];
    const mean = loadVals.reduce((a, b) => a + b, 0) / nodes.length;
    expect(Math.max(...loadVals)).toBeLessThanOrEqual(1.25 * mean + 1);
  });
});
