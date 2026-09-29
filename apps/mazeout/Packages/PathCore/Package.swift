// swift-tools-version:5.10
// PathCore: the pure-Swift game core (SPEC-architecture §2.4, §4, D1). Foundation + CoreGraphics only (tools/core.sh
// enforces the import allow-list); tested on macOS with `swift test`, no simulator.
// Written by the LEAD in WP0; CORE owns this file from C1 on.
import PackageDescription

let package = Package(
    name: "PathCore",
    platforms: [.iOS("18.0"), .macOS("15.0")],     // string form: the .v18 / .v15 members need tools 6.0
    products: [
        .library(name: "PathCore", targets: ["PathCore"]),
        .executable(name: "pclevels", targets: ["pclevels"]),
    ],
    targets: [
        // FIX-2 lane B (N-01, SPEC.md ruling 39 OD8 "STRIP provenance from every shipped file"): the research readers (the
        // phone / video level schemas, LevelImport) and the research metric's key are compiled for macOS only — the content
        // tools (pclevels, lvtool) and `swift test` — so the iOS app's binary carries none of their vocabulary.
        .target(name: "PathCore", swiftSettings: [.define("PC_RESEARCH", .when(platforms: [.macOS]))]),
        .executableTarget(name: "pclevels", dependencies: ["PathCore"]),
        // No resources in the package: tests read fixtures from disk relative to #filePath (Tests/Fixtures, research
        // JSON, design/social/fixtures, tools/rng_ref.py outputs). SwiftPM resources would have to live in the target.
        .testTarget(name: "PathCoreTests", dependencies: ["PathCore"]),
    ],
    swiftLanguageVersions: [.v5]
)
