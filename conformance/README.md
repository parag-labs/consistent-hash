# Cross-language conformance

Consistent hashing is only useful across services if every implementation places a
given key on the *same* node. This directory is the contract that guarantees it.

## What's here

- **`vectors.json`** - golden placements generated from the Python reference: for a
  fixed set of 8 nodes and 200 keys, the exact node each of the five strategies
  assigns each key to, plus known FNV-1a 32- and 64-bit hash probes.
- **`generate.py`** - regenerates `vectors.json`. Run it only when a strategy's
  placement rule intentionally changes; the vectors are committed so CI never has to.

## The contract

Each language port ships a conformance test that loads `vectors.json`, rebuilds every
strategy from the same parameters, and asserts it reproduces every assignment. If any
port disagrees, CI fails - that's the whole point. The languages:

| Port | Conformance check |
|------|-------------------|
| Python | `python/tests/test_conformance.py` |
| Go | `go/conformance_test.go` |
| Rust | `rust/tests/conformance.rs` |
| C# | `csharp/ConformanceTests.cs` |
| Java | `java/.../ConformanceTest.java` |
| TypeScript | `web/src/core/conformance.test.ts` |

## Why placement is portable

Everything that decides placement is integer-only and uses the shared FNV hashes:

- **Ring / bounded-load** hash `node#replica` with FNV-1a 32-bit onto a sorted ring.
- **Jump** seeds Lamping & Veach's LCG with FNV-1a 64-bit of the key.
- **Maglev** derives each node's `(offset, skip)` from FNV-1a 64-bit onto a fixed
  prime-sized table.
- **Rendezvous** scores `node#key` with FNV-1a 64-bit and takes the max.

The one thing deliberately **not** in the vectors is *weighted* rendezvous: weighting
uses a logarithm, and floating-point `log` rounds differently across languages, so
pinning it byte-for-byte would be a lie. Weighting is tested inside each port instead;
the cross-language vectors cover unweighted placement, which is pure integer math.
