export { fnv1a32, fnv1a64, isPrime, MASK64 } from "./hash";
export { Ring } from "./ring";
export { Rendezvous } from "./rendezvous";
export { Jump, jumpConsistentHash } from "./jump";
export { Maglev } from "./maglev";
export { BoundedLoad } from "./bounded";

export type StrategyName = "ring" | "rendezvous" | "jump" | "maglev" | "bounded";

export const STRATEGY_LABELS: Record<StrategyName, string> = {
  ring: "Ring + virtual nodes",
  rendezvous: "Rendezvous (HRW)",
  jump: "Jump",
  maglev: "Maglev",
  bounded: "Bounded-load",
};
