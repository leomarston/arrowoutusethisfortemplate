// PathCore: the umbrella module of the reference game (template phase 1, docs/ROADMAP.md). The core was split into the
// genre-agnostic GameCore (random, persistence, economy, events, the offline social world, shared motion and session
// contract types) and the ArrowEscape puzzle (grid, levels, rules, solver, content, the level session, board motion);
// the dependency is strictly ArrowEscape → GameCore. The app and the tools keep `import PathCore` and see both public
// surfaces through these re-exports.
@_exported import GameCore
@_exported import ArrowEscape
