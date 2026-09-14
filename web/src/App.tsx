import { useMemo, useState } from "react";
import {
  BoundedLoad,
  fnv1a32,
  Jump,
  Maglev,
  Rendezvous,
  Ring,
  STRATEGY_LABELS,
  type StrategyName,
} from "./core";

const PALETTE = [
  "#6E56CF", "#0EA5E9", "#22C55E", "#F59E0B", "#EF4444",
  "#EC4899", "#14B8A6", "#8B5CF6", "#84CC16", "#F97316",
];

const KEYS = Array.from({ length: 2000 }, (_, i) => `key-${i}`);
// The ring draws a representative sample of the keys as dots; load and disruption are
// always computed over the full key set.
const VIZ_KEYS = KEYS.filter((_, i) => i % 3 === 0);
const REPLICAS = 200;
const MAGLEV_TABLE = 4093;
const EPSILON = 0.25;

// Place every key on a node for the chosen strategy. Returns owner-per-key.
function place(strategy: StrategyName, nodes: string[]): Map<string, string> {
  const out = new Map<string, string>();
  if (nodes.length === 0) return out;
  switch (strategy) {
    case "ring": {
      const r = new Ring(nodes, REPLICAS);
      for (const k of KEYS) out.set(k, r.get(k)!);
      break;
    }
    case "rendezvous": {
      const h = new Rendezvous(nodes);
      for (const k of KEYS) out.set(k, h.get(k)!);
      break;
    }
    case "jump": {
      const j = new Jump(nodes);
      for (const k of KEYS) out.set(k, j.get(k)!);
      break;
    }
    case "maglev": {
      const m = new Maglev(nodes, MAGLEV_TABLE);
      for (const k of KEYS) out.set(k, m.get(k)!);
      break;
    }
    case "bounded": {
      const b = new BoundedLoad(nodes, REPLICAS, EPSILON);
      for (const k of KEYS) out.set(k, b.get(k)!);
      break;
    }
  }
  return out;
}

function angleOf(s: string): number {
  return (fnv1a32(s) / 0x100000000) * Math.PI * 2 - Math.PI / 2;
}

type Change = { label: string; movedPct: number; idealPct: number } | null;

const STRATEGIES: StrategyName[] = ["ring", "rendezvous", "jump", "maglev", "bounded"];
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

export function App() {
  const [strategy, setStrategy] = useState<StrategyName>("ring");
  const [nodes, setNodes] = useState<string[]>(["node-A", "node-B", "node-C", "node-D"]);
  const [change, setChange] = useState<Change>(null);

  const placement = useMemo(() => place(strategy, nodes), [strategy, nodes]);

  const colorOf = useMemo(() => {
    const m = new Map<string, string>();
    [...nodes].sort().forEach((n, i) => m.set(n, PALETTE[i % PALETTE.length]));
    return m;
  }, [nodes]);

  const loads = useMemo(() => {
    const m = new Map<string, number>();
    for (const n of nodes) m.set(n, 0);
    for (const owner of placement.values()) m.set(owner, (m.get(owner) ?? 0) + 1);
    return m;
  }, [nodes, placement]);

  function applyChange(next: string[], label: string) {
    const before = placement;
    const after = place(strategy, next);
    let moved = 0;
    for (const k of KEYS) if (before.get(k) !== after.get(k)) moved++;
    const movedPct = (moved / KEYS.length) * 100;
    // Ideal for an add is 1/(N+1); for a remove it's the leaving node's share (~1/N).
    const idealPct = (1 / Math.max(next.length, nodes.length)) * 100;
    setChange({ label, movedPct, idealPct });
    setNodes(next);
  }

  function addNode() {
    const used = new Set(nodes.map((n) => n.replace("node-", "")));
    const letter = ALPHABET.find((l) => !used.has(l)) ?? `${nodes.length}`;
    const name = `node-${letter}`;
    applyChange([...nodes, name], `Added ${name}`);
  }

  function removeNode(name: string) {
    if (nodes.length <= 1) return;
    applyChange(nodes.filter((n) => n !== name), `Removed ${name}`);
  }

  const R = 210;
  const cx = 260;
  const cy = 260;

  return (
    <div className="app">
      <header>
        <div className="brand"><span className="pulse" /> consistent-hash</div>
        <h1>Five ways to place a key — watch only ~1/N move</h1>
        <p className="lede">
          Every strategy spreads the same {KEYS.length} keys across the nodes. Add or
          remove a node and the meter shows what fraction of keys actually moved — the
          whole promise of consistent hashing, made visible.
        </p>
      </header>

      <div className="tabs">
        {STRATEGIES.map((s) => (
          <button
            key={s}
            className={s === strategy ? "tab active" : "tab"}
            onClick={() => {
              setStrategy(s);
              setChange(null);
            }}
          >
            {STRATEGY_LABELS[s]}
          </button>
        ))}
      </div>

      <div className="stage">
        <svg viewBox="0 0 520 520" className="ring" role="img" aria-label="hash ring">
          <circle cx={cx} cy={cy} r={R} className="ring-track" />
          {VIZ_KEYS.map((k) => {
            const a = angleOf(k);
            const owner = placement.get(k);
            return (
              <circle
                key={k}
                cx={cx + Math.cos(a) * R}
                cy={cy + Math.sin(a) * R}
                r={2.4}
                fill={owner ? colorOf.get(owner) : "#334155"}
                opacity={0.85}
              />
            );
          })}
          {[...nodes].sort().map((n, i, arr) => {
            // Node markers sit evenly around an inner ring as a colour legend; the
            // real placement lives in the key dots on the outer ring.
            const a = (i / arr.length) * Math.PI * 2 - Math.PI / 2;
            const nr = R - 34;
            return (
              <circle
                key={n}
                cx={cx + Math.cos(a) * nr}
                cy={cy + Math.sin(a) * nr}
                r={9}
                fill={colorOf.get(n)}
              />
            );
          })}
          <text x={cx} y={cy - 6} className="ring-center">{nodes.length}</text>
          <text x={cx} y={cy + 16} className="ring-center-sub">nodes</text>
        </svg>

        <div className="panel">
          <div className="controls">
            <button className="primary" onClick={addNode}>+ Add node</button>
            <span className="hint">click a node below to remove it</span>
          </div>

          <div className="nodes">
            {[...nodes].sort().map((n) => (
              <button
                key={n}
                className="node-chip"
                style={{ borderColor: colorOf.get(n) }}
                onClick={() => removeNode(n)}
                title="remove"
              >
                <span className="dot" style={{ background: colorOf.get(n) }} />
                {n}
                <span className="x">×</span>
              </button>
            ))}
          </div>

          {change && (
            <div className="meter">
              <div className="meter-head">
                <span>{change.label}</span>
                <span className="moved">{change.movedPct.toFixed(1)}% of keys moved</span>
              </div>
              <div className="bar">
                <div className="bar-ideal" style={{ width: `${Math.min(change.idealPct, 100)}%` }} />
                <div className="bar-actual" style={{ width: `${Math.min(change.movedPct, 100)}%` }} />
              </div>
              <div className="meter-foot">
                ideal ≈ {change.idealPct.toFixed(1)}% ({strategy === "jump" ? "tail bucket" : "1/N"}).
                Plain <code>hash % N</code> would move most of them.
              </div>
            </div>
          )}

          <div className="loads">
            <div className="loads-title">Load per node · {KEYS.length} keys</div>
            {(() => {
              const maxLoad = Math.max(1, ...[...loads.values()]);
              return [...nodes].sort().map((n) => {
                const count = loads.get(n) ?? 0;
                return (
                  <div className="load-row" key={n}>
                    <span className="load-name">{n}</span>
                    <div className="load-track">
                      <div
                        className="load-fill"
                        style={{ width: `${(count / maxLoad) * 100}%`, background: colorOf.get(n) }}
                      />
                    </div>
                    <span className="load-val">{count}</span>
                  </div>
                );
              });
            })()}
            <div className="loads-note">
              {REPLICAS} virtual nodes per host smooth the load; more keys and replicas
              tighten it further. The spread you see is FNV's honest variance, not a bug.
            </div>
          </div>
        </div>
      </div>

      <footer>
        <span>
          Same core as the Python, Go, Rust, C#, Java and TypeScript ports — placement
          here is byte-for-byte identical to all of them.
        </span>
        <a href="https://github.com/parag-labs/consistent-hash">Source on GitHub →</a>
      </footer>
    </div>
  );
}
