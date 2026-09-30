// swift-tools-version:5.10
// PathCore: the pure-Swift game core (SPEC-architecture §2.4, §4, D1). Foundation + CoreGraphics only (tools/core.sh
// enforces the import allow-list); tested on macOS with `swift test`, no simulator.
// Written by the LEAD in WP0; CORE owns this file from C1 on.
// Template phase 1 (docs/ROADMAP.md): split into the genre-agnostic GameCore and the arrow puzzle ArrowEscape
// (ArrowEscape → GameCore, never the other way); PathCore is now an umbrella that re-exports both, so the app, lvtool and
// the tests keep `import PathCore`. Helpers shared across the two targets but not with the app use `package` access.
import PackageDescription

// FIX-2 lane B (N-01, SPEC.md ruling 39 OD8 "STRIP provenance from every shipped file"): the research readers (the
// phone / video level schemas, LevelImport) and the research metric's key are compiled for macOS only — the content
// tools (pclevels, lvtool) and `swift test` — so the iOS app's binary carries none of their vocabulary. They live in
// ArrowEscape; the define is set on every core target so a reader that moves keeps it.
let research: [SwiftSetting] = [.define("PC_RESEARCH", .when(platforms: [.macOS]))]

let package = Package(
    name: "PathCore",
    platforms: [.iOS("18.0"), .macOS("15.0")],     // string form: the .v18 / .v15 members need tools 6.0
    products: [
        .library(name: "PathCore", targets: ["PathCore"]),
        .library(name: "GameCore", targets: ["GameCore"]),
        .library(name: "ArrowEscape", targets: ["ArrowEscape"]),
        // Template phase 5: the second puzzle module (docs/architecture/PUZZLE-MODULE.md §6b). Its own product, NOT in the
        // PathCore umbrella: the app links it next to PathCore and imports it only where its plugin lives.
        .library(name: "SortPuzzle", targets: ["SortPuzzle"]),
        .executable(name: "pclevels", targets: ["pclevels"]),
    ],
    targets: [
        // Genre-agnostic: random, persistence, economy, events, the offline social world, meta rules, shared motion and
        // the session contract types. Knows nothing about arrows.
        .target(name: "GameCore", swiftSettings: research),
        // The Arrow Out puzzle: grid, level model + JSON, rules, solver, content, the level session, board motion.
        .target(name: "ArrowEscape", dependencies: ["GameCore"], swiftSettings: research),
        // Umbrella: `@_exported import GameCore` + `@_exported import ArrowEscape` only.
        .target(name: "PathCore", dependencies: ["GameCore", "ArrowEscape"], swiftSettings: research),
        // The colour-sorting puzzle: level model + seeded generator, solver, the session, the module. GameCore only
        // (tools/core.sh checks its imports: Foundation + GameCore).
        .target(name: "SortPuzzle", dependencies: ["GameCore"]),
        .executableTarget(name: "pclevels", dependencies: ["GameCore", "ArrowEscape"]),
        // No resources in the package: tests read fixtures from disk relative to #filePath (Tests/Fixtures, research
        // JSON, design/social/fixtures, tools/rng_ref.py outputs). SwiftPM resources would have to live in the target.
        // One test target over both modules (`@testable import GameCore` + `@testable import ArrowEscape`; the frozen API
        // pins import the umbrella without @testable).
        .testTarget(name: "PathCoreTests", dependencies: ["PathCore", "GameCore", "ArrowEscape"]),
        // SortPuzzle's own tests (goldens from tools/sortpuzzle/ref.py in Tests/Fixtures, the bot through the contract).
        .testTarget(name: "SortPuzzleTests", dependencies: ["SortPuzzle", "GameCore"]),
    ],
    swiftLanguageVersions: [.v5]
)
