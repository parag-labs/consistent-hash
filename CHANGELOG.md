# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Changed

- Toolchains: Python 3.15, Go 1.27 (toolchain go1.27.3), Rust edition 2024 with
  rust-version 1.99, Java 25 (LTS), Node 26 (LTS); .NET stays on 10 with the SDK pinned
  via `csharp/global.json`. CI actions moved to their current majors.
- Libraries: React 19, Vite 8, `@vitejs/plugin-react` 6, TypeScript 7, Vitest 5 (lockfile
  resolves from the public npm registry); xunit v3 on Microsoft.Testing.Platform (opted in
  through `csharp/global.json`, so `dotnet test` is unchanged); JUnit 6, org.json 20260814
  and Surefire 3.6; matplotlib 3.11+ for the benchmarks.

## [0.2.0] - 2026-09-14

Grew from one strategy in three languages to five strategies in six. Added rendezvous
(HRW), jump, Maglev and bounded-load next to the ring; ported everything to Go, Rust
and TypeScript alongside the existing Python, C# and Java; pinned cross-language golden
vectors so every port is checked byte-for-byte in CI; and added an interactive web
visualizer plus a head-to-head strategy benchmark.

## [0.1.0] - 2026-09-07

First public release. consistent-hash ring with virtual nodes and minimal remap on membership change, in Python, C#, and Java.

[0.2.0]: https://github.com/parag-labs/consistent-hash/releases/tag/v0.2.0
[0.1.0]: https://github.com/parag-labs/consistent-hash/releases/tag/v0.1.0
